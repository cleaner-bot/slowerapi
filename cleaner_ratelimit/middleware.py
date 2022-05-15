from datetime import datetime

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Match

from .limiter import Limiter
from .strategy import MovingWindowStrategy, Ratelimited


class RatelimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, dispatch=None) -> None:
        super().__init__(app, dispatch)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        app: Starlette = request.app
        limiter: Limiter | None = getattr(app.state, "limiter", None)
        if limiter is None or not limiter.enabled:
            return await call_next(request)

        if limiter.jail is not None and limiter.jail.is_jailed(request):
            return self._make_jailed_response()

        ratelimited = None
        key = limiter.key_func(request)

        if limiter.global_limits:
            ratelimited = limiter.check_bucket("global", key, limiter.global_limits, MovingWindowStrategy)
            if ratelimited is not None and ratelimited.limited:
                if limiter.jail is not None:
                    jailed = limiter.check_bucket("jailed", key, [limiter.jail.limit], MovingWindowStrategy)
                    if jailed is not None and jailed.limited:
                        coro = limiter.jail.jail(request)
                        if coro is not None:
                            await coro
                        return self._make_jailed_response()
                return self._make_ratelimited_response(ratelimited)

        handler = None
        for route in app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL and hasattr(route, "endpoint"):
                handler = route.endpoint  # type: ignore

        if handler is not None:
            route_name = f"{handler.__module__}.{handler.__name__}"
            route_limits = limiter.route_limits.get(route_name, None)
            if route_limits:
                ratelimited = limiter.check_bucket(route_name, key, route_limits, MovingWindowStrategy)
                if ratelimited is not None and ratelimited.limited:
                    if limiter.jail is not None:
                        jailed = limiter.check_bucket("jailed", key, [limiter.jail.limit], MovingWindowStrategy)
                        if jailed is not None and jailed.limited:
                            coro = limiter.jail.jail(request)
                            if coro is not None:
                                await coro
                            return self._make_jailed_response()
                    return self._make_ratelimited_response(ratelimited)

        response = await call_next(request)
        if ratelimited:
            self._add_headers(response, ratelimited)
        return response

    def _make_jailed_response(self) -> Response:
        return JSONResponse(
            {
                "detail": (
                    "Banned from the API for exceeding allowed limits. "
                    "Contact system administrators."
                ),
            },
            status_code=429,
        )

    def _make_ratelimited_response(self, ratelimit: Ratelimited) -> Response:
        response = JSONResponse(
            {
                "detail": (
                    f"Rate limit exceeded: {ratelimit.limit.requests} "
                    f"per {ratelimit.limit.window} seconds"
                ),
                "retry_after": int(ratelimit.reset_after * 1000),
            },
            status_code=429,
        )
        self._add_headers(response, ratelimit)
        return response

    def _add_headers(self, response: Response, ratelimit: Ratelimited):
        response.headers["X-Ratelimit-Limit"] = str(ratelimit.limit.requests)
        response.headers["X-Ratelimit-Remaining"] = str(ratelimit.remaining)

        now_ms = int(datetime.utcnow().timestamp() * 1000)
        reset_after_ms = int(ratelimit.reset_after * 1000)
        response.headers["X-Ratelimit-Reset"] = str(now_ms + reset_after_ms)

        response.headers["Retry-After"] = str(reset_after_ms)

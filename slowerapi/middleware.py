from datetime import datetime

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Match

from .limiter import Limit, Limiter
from .strategy import Ratelimited


class RatelimitMiddleware(BaseHTTPMiddleware):
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
            response, ratelimited = await self._is_ratelimited(
                limiter, request, "global", key, limiter.global_limits
            )
            if response:
                return response

        handler = None
        for route in app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL and hasattr(route, "endpoint"):
                handler = route.endpoint  # type: ignore

        if handler is not None:
            route_name = f"{handler.__module__}.{handler.__name__}"
            route_limits = limiter.route_limits.get(route_name, None)
            if route_limits:
                response, ratelimited = await self._is_ratelimited(
                    limiter, request, route_name, key, route_limits
                )
                if response:
                    return response

        response = await call_next(request)
        if ratelimited:
            self._add_headers(response, ratelimited)
        return response

    async def _is_ratelimited(
        self,
        limiter: Limiter,
        request: Request,
        bucket: str,
        key: str,
        limits: list[Limit],
    ) -> tuple[Response | None, Ratelimited | None]:
        ratelimited = limiter.check_bucket(bucket, key, limits)
        if ratelimited is None or not ratelimited.limited:
            return None, ratelimited

        if limiter.jail is not None and limiter.jail.should_jail(request, key, limiter):
            await limiter.jail.jail(request)
            return self._make_jailed_response(), ratelimited
        return self._make_ratelimited_response(ratelimited), ratelimited

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

        now_ms = int(datetime.now().timestamp() * 1000)
        reset_after_ms = int(ratelimit.reset_after * 1000)
        response.headers["X-Ratelimit-Reset"] = str(now_ms + reset_after_ms)

        response.headers["Retry-After"] = str(reset_after_ms)

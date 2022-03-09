from datetime import datetime
import typing

from starlette.applications import Starlette
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.responses import Response, JSONResponse
from starlette.requests import Request
from starlette.routing import Match

from .limit import Limit
from .limiter import Limiter
from .strategy import Ratelimited, Strategy, MovingWindowStrategy


class RatelimitMiddleware(BaseHTTPMiddleware):
    buckets: typing.Dict[str, Strategy]

    def __init__(self, app, dispatch=None) -> None:
        super().__init__(app, dispatch)
        self.buckets = {}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        app: Starlette = request.app
        limiter: typing.Optional[Limiter] = getattr(app.state, "limiter", None)
        if limiter is None or not limiter.enabled:
            return await call_next(request)

        ratelimited = None
        key = limiter.key_func(request)

        if limiter.global_limits:
            ratelimited = self._check_bucket("global", key, limiter.global_limits)
            if ratelimited is not None and ratelimited.limited:
                return self._make_response(ratelimited)

        handler = None
        for route in app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL and hasattr(route, "endpoint"):
                handler = route.endpoint  # type: ignore

        if handler is not None:
            route_name = f"{handler.__module__}.{handler.__name__}"
            route_limits = limiter.route_limits.get(route_name, None)
            if route_limits:
                ratelimited = self._check_bucket(route_name, key, route_limits)
                if ratelimited is not None and ratelimited.limited:
                    return self._make_response(ratelimited)

        response = await call_next(request)
        if ratelimited:
            self._add_headers(response, ratelimited)
        return response

    def _check_bucket(
        self, bucket: str, key: str, limits: typing.List[Limit]
    ) -> typing.Optional[Ratelimited]:
        ratelimit = None
        for limit in limits:
            limit_bucket = f"{bucket}:{limit.requests}/{limit.window}"
            b = self.buckets.get(limit_bucket, None)
            if b is None:
                self.buckets[limit_bucket] = b = MovingWindowStrategy(limit)

            ratelimited = b.limit(key)
            if ratelimited.limited or ratelimit is None:
                ratelimit = ratelimited
        return ratelimit

    def _make_response(self, ratelimit: Ratelimited) -> Response:
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

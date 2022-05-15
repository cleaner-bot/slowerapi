import typing

from fastapi import Request

from .jail import Jail
from .limit import Limit, LimitType, parse_limits
from .strategy import MovingWindowStrategy, Ratelimited, Strategy

KeyFunc = typing.Callable[[Request], str]


class Limiter:
    route_limits: dict[str, list[Limit]]
    global_limits: list[Limit]
    jail: Jail | None
    buckets: dict[str, Strategy]

    def __init__(
        self,
        key_func: KeyFunc,
        global_limits: typing.Sequence[LimitType] | None = None,
        jail: Jail | None = None,
        strategy: typing.Type[Strategy] = MovingWindowStrategy,
        enabled: bool = True,
    ) -> None:
        self.key_func = key_func
        self.route_limits = {}
        self.global_limits = parse_limits(global_limits) if global_limits else []
        self.jail = jail
        self.strategy = strategy
        self.enabled = enabled
        self.buckets = {}

    def check_bucket(
        self, bucket: str, key: str, limits: list[Limit]
    ) -> Ratelimited | None:
        ratelimit = None
        for limit in limits:
            limit_bucket = f"{bucket}:{limit.requests}/{limit.window}"
            b = self.buckets.get(limit_bucket, None)
            if b is None:
                self.buckets[limit_bucket] = b = self.strategy(limit)

            ratelimited = b.limit(key)
            # 1. first cycle, ratelimit is None
            # 2. this is limited and the current one isnt
            # 3. this one resets later
            # 4. this one has less calls remaining
            if (
                ratelimit is None
                or (not ratelimit.limited and ratelimited.limited)
                or (
                    ratelimit.limited
                    and ratelimited.limited
                    and ratelimit.reset_after < ratelimited.reset_after
                )
                or (
                    not ratelimit.limited
                    and ratelimit.remaining > ratelimited.remaining
                )
            ):
                ratelimit = ratelimited
        return ratelimit

    def add_global_limit(self, limit: LimitType, *limits: LimitType):
        parsed_limits = parse_limits((limit, *limits))
        self.global_limits.extend(parsed_limits)

    def limit(self, limit: LimitType, *limits: LimitType):
        parsed_limits = parse_limits((limit, *limits))

        def wrapper(func):
            name = f"{func.__module__}.{func.__name__}"

            current_limits = self.route_limits.get(name, None)
            if current_limits is None:
                self.route_limits[name] = parsed_limits
            else:
                current_limits.extend(parsed_limits)

            return func

        return wrapper

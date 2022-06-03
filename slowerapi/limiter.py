import typing

from fastapi import Request

from .jail import Jail
from .limit import Limit, LimitType, parse_limits
from .strategy import MovingWindowStrategy, Ratelimited, Strategy

KeyFunc = typing.Callable[[Request], str]
P = typing.ParamSpec("P")
R = typing.TypeVar("R")
# I can't do this for some reason because mypy is stupid
# DecoratedFunc = typing.Callable[P, R]


class Limiter:
    route_only_count_failed: set[str]
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
        only_count_failed: bool = False,
    ) -> None:
        self.key_func = key_func
        self.route_limits = {}
        self.route_only_count_failed = set()
        self.global_only_count_failed = only_count_failed
        self.global_limits = parse_limits(global_limits) if global_limits else []
        self.jail = jail
        self.strategy = strategy
        self.enabled = enabled
        self.buckets = {}

    def check_bucket(
        self, bucket: str, key: str, limits: list[Limit], increase: bool
    ) -> Ratelimited | None:
        ratelimit = None
        for limit in limits:
            limit_bucket = f"{bucket}:{limit.requests}/{limit.window}"
            b = self.buckets.get(limit_bucket, None)
            if b is None:
                self.buckets[limit_bucket] = b = self.strategy(limit)

            ratelimited = b.limit(key, increase)
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

    def add_global_limit(self, limit: LimitType, *limits: LimitType) -> None:
        parsed_limits = parse_limits((limit, *limits))
        self.global_limits.extend(parsed_limits)

    def limit(
        self, limit: LimitType, *limits: LimitType
    ) -> typing.Callable[[typing.Callable[P, R]], typing.Callable[P, R]]:
        parsed_limits = parse_limits((limit, *limits))

        def wrapper(func: typing.Callable[P, R]) -> typing.Callable[P, R]:
            name = f"{func.__module__}.{func.__name__}"

            current_limits = self.route_limits.get(name, None)
            if current_limits is None:
                self.route_limits[name] = parsed_limits
            else:
                current_limits.extend(parsed_limits)

            return func

        return wrapper

    def only_count_failed(self, func: typing.Callable[P, R]) -> typing.Callable[P, R]:
        name = f"{func.__module__}.{func.__name__}"
        self.route_only_count_failed.add(name)
        return func

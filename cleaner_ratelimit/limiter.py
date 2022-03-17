import typing

from fastapi import Request

from .jail import Jail
from .limit import LimitType, Limit, parse_limits, parse_limit

KeyFunc = typing.Callable[[Request], str]


class Limiter:
    global_limits: list[Limit]
    route_limits: dict[str, list[Limit]]
    jail: Jail | None = None

    def __init__(
        self,
        key_func: KeyFunc,
        global_limits: list[LimitType],
        enabled: bool = True,
    ) -> None:
        self.key_func = key_func
        self.global_limits = parse_limits(global_limits)
        self.route_limits = {}
        self.enabled = enabled

    def add_global_limit(self, limit: LimitType):
        self.global_limits.append(parse_limit(limit))

    def limit(self, *limits: LimitType):
        def wrapper(func):
            name = f"{func.__module__}.{func.__name__}"
            self.route_limits[name] = parse_limits(limits)
            return func

        return wrapper

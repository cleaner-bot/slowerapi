import typing

from fastapi import Request

from .jail import Jail
from .limit import Limit, LimitType, parse_limit, parse_limits

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

    def add_global_limit(self, limit: LimitType, *limits: LimitType):
        limits = parse_limits((limit, *limits))
        self.global_limits.extend(limits)

    def limit(self, limit: LimitType, *limits: LimitType):
        limits = parse_limits((limit, *limits))

        def wrapper(func):
            name = f"{func.__module__}.{func.__name__}"
            
            current_limits = self.route_limits.get(name, None)
            if current_limits is None:
                self.route_limits[name] = limits
            else:
                current_limits.extend(limits)
            
            return func

        return wrapper

import typing

from fastapi import Request

from .limit import LimitType, Limit, parse_limits, parse_limit

KeyFunc = typing.Callable[[Request], str]

# mypy#708
T = typing.TypeVar("T")


class FunctionProperty(typing.Generic[T]):
    def __get__(self, oself: typing.Any, owner: typing.Any) -> T:
        ...

    def __set__(self, oself: typing.Any, value: T) -> None:
        ...


class Limiter:
    global_limits: typing.List[Limit]
    route_limits: typing.Dict[str, typing.List[Limit]]
    key_func: FunctionProperty[KeyFunc]  # mypy#708

    def __init__(
        self,
        key_func: KeyFunc,
        global_limits: typing.List[LimitType],
        enabled: bool = True,
    ) -> None:
        self.key_func = key_func
        self.global_limits = parse_limits(global_limits)
        self.route_limits = {}
        self.enabled = enabled

    def add_global_limit(self, limit: LimitType):
        self.global_limits.append(parse_limit(limit))

    def limit(self, *limits: typing.List[LimitType]):
        def wrapper(func):
            name = f"{func.__module__}.{func.__name__}"
            self.route_limits[name] = parse_limits(limits)
            return func

        return wrapper

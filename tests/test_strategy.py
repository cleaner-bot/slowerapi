import typing

from slowerapi.limit import Limit
from slowerapi.strategy import MovingWindowStrategy


def test_moving_window() -> None:
    limit_5_10 = Limit(5, 10)
    with TimeHelper() as th:
        window = MovingWindowStrategy(limit_5_10)
        # hijack timing function
        window._requests.time_func = th.time_func
        window._requests.time_scale = th.scale

        rt = window.limit("user_1", True)
        assert rt.limited is False
        assert rt.limit == limit_5_10
        assert rt.remaining == 4
        assert rt.reset_after == 10

        window.limit("user_1", True)
        window.limit("user_1", True)
        window.limit("user_1", True)

        rt = window.limit("user_1", True)
        assert rt.limited is False
        assert rt.remaining == 0

        rt = window.limit("user_1", False)
        assert rt.limited is False
        assert rt.remaining == 0

        rt = window.limit("user_1", True)
        assert rt.limited is True
        assert rt.remaining == 0

        rt = window.limit("user_2", True)
        assert rt.limited is False
        assert rt.remaining == 4
        assert rt.reset_after == 10

        th.advance(10)

        rt = window.limit("user_1", True)
        assert rt.limited is False
        assert rt.limit == limit_5_10
        assert rt.remaining == 4
        assert rt.reset_after == 10


# taken from expirepy
T = typing.TypeVar("T", bound="TimeHelper")


class TimeHelper:
    def __init__(self, scale: int = 1) -> None:
        self.value = 0.0
        self.scale = scale

    def time_func(self) -> float:
        return self.value * self.scale

    def advance(self, unit: float) -> None:
        self.value += unit

    def args(self) -> dict[str, typing.Any]:
        return {"time_func": self.time_func, "time_scale": self.scale}

    def __enter__(self: T) -> T:
        self.value = 0
        return self

    def __exit__(
        self, exc_type: typing.Any, exc_value: typing.Any, exc_traceback: typing.Any
    ) -> None:
        pass

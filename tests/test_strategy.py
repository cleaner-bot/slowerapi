from cleaner_ratelimit.limit import Limit
from cleaner_ratelimit.strategy import MovingWindowStrategy


def test_moving_window():
    limit_5_10 = Limit(5, 10)
    with TimeHelper() as th:
        window = MovingWindowStrategy(limit_5_10)
        # hijack timing function
        window._requests.time_func = th.time_func
        window._requests.time_scale = th.scale

        rt = window.limit("user_1")
        assert rt.limited is False
        assert rt.limit == limit_5_10
        assert rt.remaining == 4
        assert rt.reset_after == 10

        window.limit("user_1")
        window.limit("user_1")
        window.limit("user_1")

        rt = window.limit("user_1")
        assert rt.limited is False
        assert rt.remaining == 0

        rt = window.limit("user_1")
        assert rt.limited is True
        assert rt.remaining == 0

        rt = window.limit("user_2")
        assert rt.limited is False
        assert rt.remaining == 4
        assert rt.reset_after == 10

        th.advance(10)

        rt = window.limit("user_1")
        assert rt.limited is False
        assert rt.limit == limit_5_10
        assert rt.remaining == 4
        assert rt.reset_after == 10


# taken from expirepy


class TimeHelper:
    def __init__(self, scale: int = 1) -> None:
        self.value = 0
        self.scale = scale

    def time_func(self):
        return self.value * self.scale

    def advance(self, unit):
        self.value += unit

    def __enter__(self):
        self.value = 0
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

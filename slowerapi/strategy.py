import typing

from expirepy import ExpiringDict

from .limit import Limit


class Ratelimited(typing.NamedTuple):
    limited: bool
    limit: Limit
    remaining: int
    reset_after: float


class Strategy:
    def __init__(self, limit: Limit) -> None:
        self._limit = limit

    def limit(self, key: str, increase: bool) -> Ratelimited:
        raise NotImplementedError  # pragma: no cover


class MovingWindowStrategy(Strategy):
    _requests: ExpiringDict[str, int]

    def __init__(self, limit: Limit) -> None:
        super().__init__(limit)
        self._requests = ExpiringDict(expires=limit.window)

    def limit(self, key: str, increase: bool) -> Ratelimited:
        if increase:
            current = self._requests.get(key, 0) + 1
            self._requests[key] = current
            ttl = self._requests.ttl(key)
        else:
            current = self._requests.get(key, 0)
            try:
                ttl = self._requests.ttl(key)
            except KeyError:
                ttl = self._limit.window

        remaining = self._limit.requests - current
        return Ratelimited(
            limited=remaining < 0,
            limit=self._limit,
            remaining=max(0, remaining),
            reset_after=ttl,
        )

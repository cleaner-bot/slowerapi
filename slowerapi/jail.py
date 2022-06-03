from __future__ import annotations

import ipaddress
import typing
from abc import ABC

from fastapi import Request

from .limit import LimitType, parse_limits

if typing.TYPE_CHECKING:  # pragma: no cover
    from .limiter import Limiter


IpFunc = typing.Callable[[Request], str]
ReportFunc = typing.Callable[[Request, str], typing.Any]


def reduce_ip_range(ip: str) -> str:
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv4Address):
        a, b, c, _ = addr.packed
        return f"{a}.{b}.{c}.0/24"
    else:
        return f"{addr.packed[:8].hex(':', 2)}::/64"


class Jail(ABC):
    def is_jailed(self, request: Request) -> bool:  # pragma: no cover
        ...

    def should_jail(
        self, request: Request, key: str, limiter: Limiter
    ) -> bool:  # pragma: no cover
        ...

    async def jail(self, request: Request) -> None:  # pragma: no cover
        ...


class IPJail(Jail):
    _jailed: set[str]

    def __init__(
        self,
        ip_func: IpFunc,
        limits: typing.Sequence[LimitType],
        reporters: list[ReportFunc] | None = None,
    ):
        self.ip_func = ip_func
        self.limits = parse_limits(limits)
        self.reporters = reporters if reporters else []
        self._jailed = set()

    def is_jailed(self, request: Request) -> bool:
        ip_range = reduce_ip_range(self.ip_func(request))
        return ip_range in self._jailed

    def should_jail(self, request: Request, key: str, limiter: Limiter) -> bool:
        ratelimited = limiter.check_bucket("jailed", key, self.limits, True)
        return ratelimited is not None and ratelimited.limited

    async def jail(self, request: Request) -> None:
        ip_range = reduce_ip_range(self.ip_func(request))
        if ip_range in self._jailed:
            return
        self._jailed.add(ip_range)
        for reporter in self.reporters:
            await reporter(request, ip_range)

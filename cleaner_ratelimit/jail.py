from __future__ import annotations

import ipaddress
import typing
from abc import ABC

from fastapi import Request

from .limit import LimitType, parse_limits

if typing.TYPE_CHECKING:
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
    def is_jailed(self, request: Request) -> bool:
        ...

    def should_jail(self, request: Request, key: str, limiter: Limiter) -> bool:
        ...

    async def jail(self, request: Request):
        ...


class IPJail(Jail):
    _jailed: set[str]

    def __init__(
        self,
        ip_func: IpFunc,
        limits: list[LimitType],
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
        ratelimited = limiter.check_bucket("jailed", key, self.limits)
        return ratelimited is not None and ratelimited.limited

    async def jail(self, request: Request):
        ip_range = reduce_ip_range(self.ip_func(request))
        if ip_range in self._jailed:
            return
        self._jailed.add(ip_range)
        for reporter in self.reporters:
            await reporter(request, ip_range)

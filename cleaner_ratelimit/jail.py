import typing
import ipaddress

from fastapi import Request
import httpx

from .limit import parse_limit, LimitType


IpFunc = typing.Callable[[Request], str]
ReportFunc = typing.Callable[[Request, str], typing.Any]


def reduce_ip_range(ip: str) -> str:
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv4Address):
        a, b, c, _ = addr.packed
        return f"{a}.{b}.{c}.0/24"
    else:
        return f"{addr.packed[:8].hex(':', 2)}::/64"


class Jail:
    _jailed: set[str]

    def __init__(
        self,
        ip_func: IpFunc,
        limit: LimitType,
        reporter: typing.Optional[ReportFunc] = None,
    ):
        self.ip_func = ip_func
        self.limit = parse_limit(limit)
        self.reporter = reporter
        self._jailed = set()

    def is_jailed(self, request: Request) -> bool:
        ip_range = reduce_ip_range(self.ip_func(request))
        return ip_range in self._jailed

    def jail(self, request: Request):
        ip_range = reduce_ip_range(self.ip_func(request))
        if ip_range in self._jailed:
            return
        self._jailed.add(ip_range)
        if self.reporter is not None:
            return self.reporter(request, ip_range)


class CloudflareIPAccessRuleReporter:
    def __init__(
        self,
        x_auth_email: str,
        x_auth_token: str,
        zone_id: typing.Optional[str] = None,
        note: str = None,
    ) -> None:
        self.zone_id = zone_id
        self.note = note
        self.aclient = httpx.AsyncClient(
            base_url="https://api.cloudflare.com/client/v4/",
            headers={"x-auth-email": x_auth_email, "x-auth-token": x_auth_token},
        )

    async def __call__(self, request: Request, ip_range: str):
        endpoint = "user/firewall/access_rules/rules"
        if self.zone_id is not None:
            endpoint = f"zones/{self.zone_id}/firewall/access_rules/rules"
        note = self.note
        if note is None:
            note = "Automatic jail."
        await self.aclient.post(
            endpoint,
            json={
                "mode": "block",
                "configuration": {
                    "target": "ip_range",
                    "value": ip_range,
                    "note": note,
                },
            },
        )

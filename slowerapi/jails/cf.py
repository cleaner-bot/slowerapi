import httpx
from fastapi import Request


class CloudflareIPAccessRuleReporter:
    def __init__(
        self,
        x_auth_email: str,
        x_auth_key: str,
        zone_id: str | None = None,
        note: str = None,
    ) -> None:
        self.zone_id = zone_id
        self.note = note
        self.aclient = httpx.AsyncClient(
            base_url="https://api.cloudflare.com/client/v4/",
            headers={"x-auth-email": x_auth_email, "x-auth-key": x_auth_key},
        )

    async def __call__(self, request: Request, ip_range: str):
        endpoint = "user/firewall/access_rules/rules"
        if self.zone_id is not None:
            endpoint = f"zones/{self.zone_id}/firewall/access_rules/rules"
        note = self.note
        if note is None:
            note = "Automatic jail."
        req = await self.aclient.post(
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
        req.raise_for_status()

import httpx
from fastapi import Request


class CloudflareIPAccessRuleReporter:
    def __init__(
        self,
        email_or_token: str,
        key: str | None = None,
        zone_id: str | None = None,
        note: str | None = None,
    ) -> None:
        self.zone_id = zone_id
        self.note = note
        self.aclient = httpx.AsyncClient(
            base_url="https://api.cloudflare.com/client/v4/",
            headers=(
                {"x-auth-email": email_or_token, "x-auth-key": key}
                if key is not None
                else {"Authorization": f"Bearer {email_or_token}"}
            ),
        )

    async def __call__(self, request: Request, ip_range: str) -> None:
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

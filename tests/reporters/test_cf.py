from unittest import mock

import pytest

from slowerapi.reporters.cf import CloudflareIPAccessRuleReporter


@pytest.mark.asyncio
async def test_email() -> None:
    cfiparr = CloudflareIPAccessRuleReporter("test@test.cf", "0123456789")

    assert cfiparr.aclient.headers["x-auth-email"] == "test@test.cf"
    assert cfiparr.aclient.headers["x-auth-key"] == "0123456789"

    cfiparr.aclient.post = post = mock.AsyncMock(return_value=mock.Mock())  # type: ignore

    await cfiparr(None, "1.2.3.0/24")  # type: ignore

    endpoint = "user/firewall/access_rules/rules"
    json = {
        "mode": "block",
        "configuration": {
            "target": "ip_range",
            "value": "1.2.3.0/24",
            "note": "Automatic jail.",
        },
    }
    post.assert_awaited_once_with(endpoint, json=json)


@pytest.mark.asyncio
async def test_cloudflare_ip_access_rule_reporter() -> None:
    cfiparr = CloudflareIPAccessRuleReporter("test1234")

    assert cfiparr.aclient.headers["authorization"] == "Bearer test1234"


@pytest.mark.asyncio
async def test_with_note() -> None:
    cfiparr = CloudflareIPAccessRuleReporter(
        "test@test.cf", "1234567890", "1234", "note"
    )
    cfiparr.aclient.post = post = mock.AsyncMock(return_value=mock.Mock())  # type: ignore

    await cfiparr(None, "1.2.3.0/24")  # type: ignore

    endpoint = "zones/1234/firewall/access_rules/rules"
    json = {
        "mode": "block",
        "configuration": {"target": "ip_range", "value": "1.2.3.0/24", "note": "note"},
    }
    post.assert_awaited_once_with(endpoint, json=json)

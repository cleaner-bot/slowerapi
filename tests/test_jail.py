from unittest import mock

import pytest

from cleaner_ratelimit import Jail
from cleaner_ratelimit.jail import reduce_ip_range, CloudflareIPAccessRuleReporter


def test_reduce_ip_range():
    assert reduce_ip_range("1.2.3.4") == "1.2.3.0/24"
    inp = "0011:2233:4455:6677:0011:2233:4455:6677"
    assert reduce_ip_range(inp) == "0011:2233:4455:6677::/64"


def test_jail_limit():
    jail = Jail(str, "50/1m")
    assert jail.limit.requests == 50
    assert jail.limit.window == 60


def test_is_jailed():
    jail = Jail(str, "")
    assert not jail.is_jailed("1.2.3.0")
    assert not jail.is_jailed("1.2.3.4")
    jail.jail("1.2.3.4")
    assert jail.is_jailed("1.2.3.4")
    assert jail.is_jailed("1.2.3.0")


def test_reporter():
    reporter = mock.Mock()
    args = ("1.2.3.4", "1.2.3.0/24")
    jail = Jail(str, "", reporter)

    jail.jail("1.2.3.4")
    reporter.assert_called_once_with(*args)
    jail.jail("1.2.3.4")
    reporter.assert_called_once_with(*args)  # not called again


@pytest.mark.asyncio
async def test_cloudflare_ip_access_rule_reporter():
    cfiparr = CloudflareIPAccessRuleReporter("test@test.cf", "0123456789")

    assert cfiparr.aclient.headers["x-auth-email"] == "test@test.cf"
    assert cfiparr.aclient.headers["x-auth-token"] == "0123456789"

    cfiparr.aclient.post = post = mock.AsyncMock()

    await cfiparr(None, "1.2.3.0/24")

    endpoint = "user/firewall/access_rules/rules"
    json = {
        "mode": "block",
        "configuration": {
            "target": "ip_range",
            "value": "1.2.3.0/24",
            "note": "Automatic jail.",
        },
    }
    post.assert_called_once_with(endpoint, json=json)


@pytest.mark.asyncio
async def test_cloudflare_ip_access_rule_reporter_zone_note():
    cfiparr = CloudflareIPAccessRuleReporter(
        "test@test.cf", "1234567890", "1234", "note"
    )
    cfiparr.aclient.post = post = mock.AsyncMock()

    await cfiparr(None, "1.2.3.0/24")

    endpoint = "zones/1234/firewall/access_rules/rules"
    json = {
        "mode": "block",
        "configuration": {"target": "ip_range", "value": "1.2.3.0/24", "note": "note"},
    }
    post.assert_called_once_with(endpoint, json=json)

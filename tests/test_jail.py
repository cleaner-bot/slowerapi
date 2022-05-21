from unittest import mock

import pytest

from slowerapi import IPJail
from slowerapi.jail import reduce_ip_range


def test_reduce_ip_range():
    assert reduce_ip_range("1.2.3.4") == "1.2.3.0/24"
    inp = "0011:2233:4455:6677:0011:2233:4455:6677"
    assert reduce_ip_range(inp) == "0011:2233:4455:6677::/64"


def test_jail_limit():
    jail = IPJail(str, ["50/1m"])
    assert jail.limits[0].requests == 50
    assert jail.limits[0].window == 60


@pytest.mark.asyncio
async def test_is_jailed():
    jail = IPJail(str, [])
    assert not jail.is_jailed("1.2.3.0")
    assert not jail.is_jailed("1.2.3.4")
    await jail.jail("1.2.3.4")
    assert jail.is_jailed("1.2.3.4")
    assert jail.is_jailed("1.2.3.0")


@pytest.mark.asyncio
async def test_reporter():
    reporter = mock.AsyncMock()
    args = ("1.2.3.4", "1.2.3.0/24")
    jail = IPJail(str, "", [reporter])

    await jail.jail("1.2.3.4")
    reporter.assert_awaited_once_with(*args)
    await jail.jail("1.2.3.4")
    reporter.assert_awaited_once_with(*args)  # not called again

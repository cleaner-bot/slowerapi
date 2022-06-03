import pytest

from slowerapi.limit import Limit, parse_limit, parse_limits


def test_parse_limit() -> None:
    limit_1_1 = Limit(1, 1)
    assert parse_limit("") == limit_1_1
    assert parse_limit("1") == limit_1_1
    assert parse_limit("1/1") == limit_1_1
    assert parse_limit("1/second") == limit_1_1
    assert parse_limit("1/1second") == limit_1_1
    assert parse_limit("1/s") == limit_1_1
    assert parse_limit("1/seconds") == limit_1_1
    assert parse_limit("/1") == limit_1_1
    assert parse_limit("/") == limit_1_1
    assert parse_limit("1/") == limit_1_1
    assert parse_limit(limit_1_1) == limit_1_1

    with pytest.raises(ValueError):
        parse_limit("1/something")


def test_parse_limits() -> None:
    limit_1_1 = Limit(1, 1)
    limits = ["", "1", "1/1"]
    assert parse_limits(limits) == [limit_1_1] * 3

from slowerapi import Limiter
from slowerapi.limit import Limit


def test_limiter() -> None:
    limit_1_1 = Limit(1, 1)
    limiter = Limiter(lambda req: "", ["1/1"])

    assert limiter.global_limits == [limit_1_1]
    limiter.add_global_limit("1/1")
    assert limiter.global_limits == [limit_1_1] * 2

    @limiter.limit("1/1")
    def test() -> None:
        pass  # pragma: no cover

    name = f"{test.__module__}.{test.__name__}"
    assert limiter.route_limits[name] == [limit_1_1]


def test_multiple_limiter() -> None:
    limit_1_1 = Limit(1, 1)
    limiter = Limiter(lambda req: "", ["1/1"])

    assert limiter.global_limits == [limit_1_1]
    limiter.add_global_limit("1/1")
    assert limiter.global_limits == [limit_1_1] * 2

    @limiter.limit("1/1")
    def test() -> None:
        pass  # pragma: no cover

    @limiter.limit("1/1")  # type: ignore
    def test() -> None:  # noqa: F811
        pass  # pragma: no cover

    name = f"{test.__module__}.{test.__name__}"
    assert limiter.route_limits[name] == [limit_1_1, limit_1_1]


def test_only_count_failed() -> None:
    limit_1_1 = Limit(1, 1)
    limiter = Limiter(lambda req: "", ["1/1"])

    assert limiter.global_limits == [limit_1_1]
    limiter.add_global_limit("1/1")
    assert limiter.global_limits == [limit_1_1] * 2

    @limiter.only_count_failed
    def test() -> None:
        pass  # pragma: no cover

    name = f"{test.__module__}.{test.__name__}"
    assert name in limiter.route_only_count_failed

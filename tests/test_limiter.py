from cleaner_ratelimit import Limiter
from cleaner_ratelimit.limit import Limit


def test_limiter():
    limit_1_1 = Limit(1, 1)
    limiter = Limiter(lambda req: "", ["1/1"])

    assert limiter.global_limits == [limit_1_1]
    limiter.add_global_limit("1/1")
    assert limiter.global_limits == [limit_1_1] * 2

    @limiter.limit("1/1")
    def test():
        pass  # pragma: no cover

    name = f"{test.__module__}.{test.__name__}"
    assert limiter.route_limits[name] == [limit_1_1]

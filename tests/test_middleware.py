from unittest import mock

import pytest
from starlette.routing import Match

from cleaner_ratelimit import IPJail, Limiter, RatelimitMiddleware
from cleaner_ratelimit.limit import parse_limit


@pytest.fixture()
def middleware():
    app = mock.Mock()
    return RatelimitMiddleware(app)


@pytest.mark.asyncio
async def test_no_limiter(middleware: RatelimitMiddleware):
    request = mock.Mock()
    request.app = middleware.app
    call_next = mock.AsyncMock()
    middleware.app.state.limiter = None  # type: ignore

    await middleware.dispatch(request, call_next)

    call_next.assert_awaited_once_with(request)


@pytest.mark.asyncio
async def test_disabled_limiter(middleware: RatelimitMiddleware):
    request = mock.Mock()
    request.app = middleware.app
    key_func = mock.Mock()
    request.app.state.limiter = Limiter(key_func, (), enabled=False)  # type: ignore
    call_next = mock.AsyncMock()

    await middleware.dispatch(request, call_next)

    call_next.assert_awaited_once_with(request)
    key_func.assert_not_called()


@pytest.mark.asyncio
async def test_is_jailed(middleware: RatelimitMiddleware):
    request = mock.Mock()
    request.app = middleware.app
    key_func = mock.Mock()
    request.app.state.limiter = limiter = Limiter(key_func, ())  # type: ignore
    limiter.jail = mock.Mock()
    limiter.jail.is_jailed.return_value = True
    call_next = mock.AsyncMock()

    await middleware.dispatch(request, call_next)

    call_next.assert_not_called()
    key_func.assert_not_called()
    limiter.jail.is_jailed.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_key_func(middleware: RatelimitMiddleware):
    request = mock.Mock()
    request.app = middleware.app
    key_func = mock.Mock()
    request.app.state.limiter = Limiter(key_func, ())  # type: ignore
    request.app.routes = []  # type: ignore
    call_next = mock.AsyncMock()

    await middleware.dispatch(request, call_next)

    call_next.assert_awaited_once_with(request)
    key_func.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_global_limit(middleware: RatelimitMiddleware):
    request = mock.Mock()
    request.app = middleware.app
    key_func = mock.Mock(return_value="key")
    request.app.state.limiter = limiter = Limiter(key_func, ("1/1d",))  # type: ignore
    request.app.routes = []  # type: ignore
    call_next = mock.AsyncMock()
    limiter.check_bucket = mock.Mock(wraps=limiter.check_bucket)  # type: ignore
    middleware._make_ratelimited_response = mock.Mock(  # type: ignore
        wraps=middleware._make_ratelimited_response
    )

    await middleware.dispatch(request, call_next)
    call_next.assert_awaited_once_with(request)
    key_func.assert_called_once_with(request)

    limiter.check_bucket.assert_called_once()
    middleware._make_ratelimited_response.assert_not_called()

    response = await middleware.dispatch(request, call_next)
    call_next.assert_awaited_once_with(request)  # not called again, got caught

    middleware._make_ratelimited_response.assert_called_once()

    assert response.status_code == 429


@pytest.mark.asyncio
@pytest.mark.parametrize("with_reporter", (False, True))
async def test_global_limit_jailed(
    middleware: RatelimitMiddleware, with_reporter: bool
):
    request = mock.Mock()
    request.app = middleware.app
    key_func = mock.Mock(return_value="key")
    request.app.state.limiter = limiter = Limiter(key_func, ("1/1d",))  # type: ignore
    request.app.routes = []  # type: ignore
    reporters = [mock.AsyncMock()] if with_reporter else None
    limiter.jail = IPJail(lambda _: "1.2.3.4", ["0/1s"], reporters)  # type: ignore
    call_next = mock.AsyncMock()
    limiter.check_bucket = mock.Mock(wraps=limiter.check_bucket)  # type: ignore
    middleware._make_ratelimited_response = mock.Mock(  # type: ignore
        wraps=middleware._make_ratelimited_response
    )
    middleware._make_jailed_response = mock.Mock(  # type: ignore
        wraps=middleware._make_jailed_response
    )

    await middleware.dispatch(request, call_next)
    call_next.assert_awaited_once_with(request)
    key_func.assert_called_once_with(request)

    limiter.check_bucket.assert_called_once()
    middleware._make_ratelimited_response.assert_not_called()
    middleware._make_jailed_response.assert_not_called()

    response = await middleware.dispatch(request, call_next)
    call_next.assert_awaited_once_with(request)  # not called again, got caught

    middleware._make_ratelimited_response.assert_not_called()
    middleware._make_jailed_response.assert_called_once()

    if reporters is not None:
        reporters[0].assert_awaited_once_with(request, "1.2.3.0/24")

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_route_limit(middleware: RatelimitMiddleware):
    request = mock.Mock()
    request.app = middleware.app
    key_func = mock.Mock(return_value="key")
    request.app.state.limiter = limiter = Limiter(key_func, ())  # type: ignore
    route = mock.Mock()
    route.matches = mock.Mock(return_value=(Match.FULL, 0))  # type: ignore
    name = "cleaner_ratelimit_test.test.test_route"
    route.endpoint.__module__ = "cleaner_ratelimit_test.test"  # type: ignore
    route.endpoint.__name__ = "test_route"  # type: ignore
    request.app.state.limiter.route_limits[name] = [parse_limit("1/1d")]  # type: ignore
    request.app.routes = [route]  # type: ignore
    call_next = mock.AsyncMock()
    limiter.check_bucket = mock.Mock(wraps=limiter.check_bucket)  # type: ignore
    middleware._make_ratelimited_response = mock.Mock(  # type: ignore
        wraps=middleware._make_ratelimited_response
    )

    await middleware.dispatch(request, call_next)
    call_next.assert_awaited_once_with(request)
    key_func.assert_called_once_with(request)

    limiter.check_bucket.assert_called_once()
    middleware._make_ratelimited_response.assert_not_called()

    response = await middleware.dispatch(request, call_next)
    call_next.assert_awaited_once_with(request)  # not called again, got caught

    middleware._make_ratelimited_response.assert_called_once()

    assert response.status_code == 429


@pytest.mark.asyncio
@pytest.mark.parametrize("with_reporter", (False, True))
async def test_route_limit_jailed(middleware: RatelimitMiddleware, with_reporter: bool):
    request = mock.Mock()
    request.app = middleware.app
    key_func = mock.Mock(return_value="key")
    request.app.state.limiter = limiter = Limiter(key_func, ())  # type: ignore
    reporter = [mock.AsyncMock()] if with_reporter else None
    limiter.jail = IPJail(lambda _: "1.2.3.4", ["0/1s"], reporter)
    route = mock.Mock()
    route.matches = mock.Mock(return_value=(Match.FULL, 0))  # type: ignore
    name = "cleaner_ratelimit_test.test.test_route"
    route.endpoint.__module__ = "cleaner_ratelimit_test.test"  # type: ignore
    route.endpoint.__name__ = "test_route"  # type: ignore
    request.app.state.limiter.route_limits[name] = [parse_limit("1/1d")]  # type: ignore
    request.app.routes = [route]  # type: ignore
    call_next = mock.AsyncMock()
    limiter.check_bucket = mock.Mock(wraps=limiter.check_bucket)  # type: ignore
    middleware._make_ratelimited_response = mock.Mock(  # type: ignore
        wraps=middleware._make_ratelimited_response
    )
    middleware._make_jailed_response = mock.Mock(  # type: ignore
        wraps=middleware._make_jailed_response
    )

    await middleware.dispatch(request, call_next)
    call_next.assert_awaited_once_with(request)
    key_func.assert_called_once_with(request)

    limiter.check_bucket.assert_called_once()
    middleware._make_ratelimited_response.assert_not_called()

    response = await middleware.dispatch(request, call_next)
    call_next.assert_awaited_once_with(request)  # not called again, got caught

    middleware._make_ratelimited_response.assert_not_called()
    middleware._make_jailed_response.assert_called_once()

    if reporter is not None:
        reporter[0].assert_awaited_once_with(request, "1.2.3.0/24")

    assert response.status_code == 429

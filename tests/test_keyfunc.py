from unittest import mock

from slowerapi import get_visitor_ip


def test_get_visitor_ip() -> None:
    request = mock.MagicMock()
    request.headers.__contains__.return_value = False
    request.client.host = "1.2.3.4"
    assert get_visitor_ip(request) == "1.2.3.4"


def test_get_visitor_ip_cf() -> None:
    request = mock.MagicMock()
    request.headers.__contains__.return_value = True
    request.headers.__getitem__.return_value = "4.3.2.1"
    request.client.host = "1.2.3.4"
    assert get_visitor_ip(request) == "4.3.2.1"
    request.headers.__getitem__.assert_called_once_with("cf-connecting-ip")

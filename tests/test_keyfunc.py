from unittest import mock

from slowerapi import get_visitor_ip


def test_get_visitor_ip():
    request = mock.Mock()
    request.headers.get.return_value = None
    request.client.host = "1.2.3.4"
    assert get_visitor_ip(request) == "1.2.3.4"


def test_get_visitor_ip_cf():
    request = mock.Mock()
    request.headers.get.return_value = "4.3.2.1"
    request.client.host = "1.2.3.4"
    assert get_visitor_ip(request) == "4.3.2.1"
    request.headers.get.assert_called_once_with("cf-connecting-ip", None)

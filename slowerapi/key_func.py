import typing

from fastapi import Request

HEADERS = ("cf-connecting-ip",)


def get_visitor_ip(request: Request) -> str:
    for header in HEADERS:
        if header in request.headers:
            return request.headers[header]

    if request.client is None:
        raise RuntimeError("missing request.client")
    return request.client.host

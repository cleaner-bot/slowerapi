from fastapi import Request

HEADERS = (
    "cf-connecting-ip",
)


def get_visitor_ip(request: Request) -> str:
    for header in HEADERS:
        if header in request.headers:
            return request.headers[header]

    # this is a string
    return request.client.host  # type: ignore

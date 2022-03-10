from fastapi import Request


def get_visitor_ip(request: Request) -> str:
    # cloudflare header
    if ip := request.headers.get("cf-connecting-ip", None):
        return ip
    return request.client.host

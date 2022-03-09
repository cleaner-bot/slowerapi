import typing


time_units = {
    "s": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hour": 3600,
    "hours": 3600,
    "d": 86400,
    "day": 86400,
    "days": 86400,
}


class Limit(typing.NamedTuple):
    requests: int
    window: int  # in seconds


LimitType = typing.Union[str, Limit]


def parse_limits(limits: typing.List[LimitType]) -> typing.List[Limit]:
    return [parse_limit(x) for x in limits]


def parse_limit(limit: LimitType) -> Limit:
    if isinstance(limit, Limit):
        return limit
    requests, window = limit.split("/") if "/" in limit else (limit, "")
    unit_start = 0
    while unit_start < len(window) and window[unit_start].isdigit():
        unit_start += 1
    window, scale_unit = window[:unit_start], window[unit_start:]

    scale = 1
    if scale_unit in time_units:
        scale = time_units[scale_unit]
    elif scale_unit:
        raise ValueError(f"unknown time scale unit: {scale_unit}")

    return Limit(int(requests or 1), int(window or 1) * scale)

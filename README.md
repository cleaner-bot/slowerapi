
# slowerapi

A ratelimiting library for FastAPI because the others just didn't fit my use case.

## Installation

Install from github: `pip install git+https://github.com/cleaner-bot/slowerapi.git`

Add `@version` at the end to pin a version, eg `@0.1.0`.


## Quick start

```py
from slowerapi import Limiter, get_visitor_ip, RatelimitMiddleware

limiter = Limiter(key_func=get_visitor_ip)

limiter.add_global_limit("100/1s")  # global limit of 100 req/s

# ...
# add the middleware and state
app.state.limiter = limiter  # must be app.state.limiter
app.add_middleware(RatelimitMiddleware)

# ...

@app.get("/route")
@limiter.limit("5/5")  # limit to 5 requests per 5 seconds
async def get_route():
    pass
```

## Jail

We use a "jail" for punishing requests that do not follow ratelimits.

We provide a simple jail implementation: `IPJail`. It jails the entire
ip range of the offender after a special ratelimit is exceeded.

The following example will jail the ip range after the same ip exceeds
ratelimits 100 times in one minute.

```py
from slowerapi import IPJail

limiter = Limiter(
    key_func=get_visitor_ip,
    jail=IPJail(get_visitor_ip, "100/m")
)
```

### Jail reporter

Jail reporters allow for reporting jailed ip (-ranges) to other tools, to
log jails or block requests at another layer in the stack. (eg a firewall)

We provide a simple reporter implementation for blocking requests using
[Cloudflare](https://cloudflare.com)'s [IP Access Rules](https://support.cloudflare.com/hc/en-us/articles/217074967-Configuring-IP-Access-Rules).

```py
from slowerapi.repoters.cf import CloudflareIPAccessRuleReporter

cfreporter = CloudflareIPAccessRuleReporter(
    x_auth_email="your@email.com",
    x_auth_key="jjDWMDiegFDWOdmwrgnagangcvmNWfpemfeO",
    zone_id="aaaaaaaaaaaaaaaaaaaaa",  # dont set for ban across all zones
    note="Exceeded ratelimits on (service)",  # note that's added to the ban
)
limiter = Limiter(
    key_func=get_visitor_ip,
    jail=IPJail(get_visitor_ip, "100/m", [cfreporter])
)
```

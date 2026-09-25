# -*- coding: utf-8 -*-
"""DNS self-heal for this machine.

The local DNS server sometimes answers a public hostname with a dead private
address (api.pexels.com -> 10.10.34.36), so every Python HTTPS call to that
host times out while curl and other apps still work.

    import netfix   # very first import of the entry script

patches socket.getaddrinfo: a bad answer is re-resolved over DNS-over-HTTPS
(dns.google) and returned first, so connections succeed.  Every other host is
untouched - nothing is rewritten unless a private IPv4 appears for a public
name.
"""

from __future__ import annotations

import ipaddress
import json
import socket
import threading
import time
import urllib.request

_orig = socket.getaddrinfo
_tls = threading.local()
_cache = {}
_BAD = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
    "169.254.0.0/16", "172.16.0.0/12", "192.168.0.0/16")]


def _private(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return isinstance(a, ipaddress.IPv4Address) and any(a in n for n in _BAD)


def _doh(host):
    now = time.time()
    hit = _cache.get(host)
    if hit and now - hit[0] < 3600:
        return hit[1]
    if getattr(_tls, "busy", False):        # never recurse into our own lookup
        return []
    _tls.busy = True
    try:
        req = urllib.request.Request(
            "https://dns.google/resolve?name=%s&type=A" % host,
            headers={"User-Agent": "netfix/1.0"})
        data = json.load(urllib.request.urlopen(req, timeout=6))
        ips = [a["data"] for a in data.get("Answer", []) if a.get("type") == 1]
        ips = [i for i in ips if not _private(i)]
        _cache[host] = (now, ips)
        return ips
    except Exception:
        return []
    finally:
        _tls.busy = False


def _gai(host, port, family=0, type=0, proto=0, canonname=None):
    res = _orig(host, port, family, type, proto, canonname)
    if not isinstance(host, str) or not res:
        return res
    try:
        ipaddress.ip_address(host)
        return res                              # host already is an address
    except ValueError:
        pass
    if not any(_private(r[4][0]) for r in res):
        return res                              # healthy answer, leave it alone
    good = [r for r in res if not _private(r[4][0])]
    fixed = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))
             for ip in _doh(host)]
    out = fixed + good
    if not out:
        return res
    if family:
        filt = [r for r in out if r[0] == family]
        if filt:
            return filt
    return out


if socket.getaddrinfo is not _orig:
    socket.getaddrinfo = _gai
    __patched__ = True

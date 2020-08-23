from typing import List
from subprocess import run, TimeoutExpired


class ConnectionError(RuntimeError):
    pass


class PingStats:
    def __init__(self):
        self.packet_loss_pct = 0  # type: int
        self.rtt_min = 0  # type: int
        self.rtt_max = 0  # type: int
        self.rtt_avg = 0  # type: int


def ping_host(host: str, ip_version: int = 4, timeout: int = 10) -> str:
    """ping remote host"""

    if ip_version not in (4, 6):
        raise ValueError("Invalid IP version {}".format(ip_version))

    ping_cmd = [
        "/usr/bin/ping",
        "-{}".format(ip_version),
        "-q",
        "-w",
        str(timeout),
        "-c",
        "3",
        host,
    ]
    try:
        proc = run(ping_cmd, capture_output=True, text=True, timeout=timeout)
    except TimeoutExpired as err:
        raise ConnectionError("ping host {} timedout".format(host))
    if proc.returncode != 0 or len(proc.stderr):
        raise ConnectionError("failed to ping host {}".format(host))
    return ""


def resolve_any_domain(ns: str, domains: List[str]) -> str:
    """Resolve provided domains from the name server. Return the resolve addresses"""
    return ""


def http_get(url: str) -> str:
    """Do an HTTP get request to the URL and return the body as string"""
    return ""

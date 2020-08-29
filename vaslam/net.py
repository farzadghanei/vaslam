from os import path
import re
from socket import gethostbyname
from urllib.request import urlopen
from urllib.error import URLError
from typing import List, Tuple
from subprocess import run, TimeoutExpired


class ConnectionError(RuntimeError):
    pass


class HttpConError(ConnectionError):
    pass


class PingStats:
    def __init__(self):
        self.packet_loss_pct = 0  # type: int
        self.rtt_min = 0  # type: float
        self.rtt_max = 0  # type: float
        self.rtt_avg = 0  # type: float

    def connected(self) -> bool:
        """Returns True if the ping stats show connection"""
        return self.packet_loss_pct < 100 and self.rtt_max > 0


def ping_host(host: str, timeout: int = 10) -> PingStats:
    """ping remote host

    :raises: ConnectionError on ping timeout or errors
    """
    # @TODO: maybe support ICMP packets instead of running an external process
    return _parse_ping_output(_ping_cmd(host, timeout))


def resolve_any_domain(domains: List[str]) -> Tuple[str, str]:
    """Resolve IPv4 of the provided domains.
    Return the first resolved domain and its address
    """
    # @TODO: support resovling using specified name servers

    for domain in domains:
        try:
            return domain, gethostbyname(domain)
        except OSError as err:
            continue
    return "", ""


def http_get(url: str, timeout: int = 10) -> Tuple[int, str]:
    """Do an HTTP get request to the URL.
    Return a tuple of the HTTP status (int) and body (string)
    """
    code, body = 0, ""
    try:
        with urlopen(url, timeout=timeout) as resp:
            code = int(resp.getcode())
            body = resp.read()
    except (RuntimeError, URLError) as err:
        raise HttpConError("failed to http get {}: {}".format(url, err))

    return code, body


def _parse_ping_output(out: str) -> PingStats:
    """Parse output from ping command"""

    stats = PingStats()
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    for line in lines:
        # rtt min/avg/max/mdev = 9.956/10.264/10.738/0.340 ms
        match = re.match(r".*rtt.+min/avg/max.+=\s*(\S+)\s+.*", line)
        if match:
            rtts = [t.strip() for t in match.group(1).strip().split("/")]
            if len(rtts) > 2:
                stats.rtt_min = float(rtts[0])
                stats.rtt_avg = float(rtts[1])
                stats.rtt_max = float(rtts[2])
            continue
        # 3 packets transmitted, 3 received, 0% packet loss, time 2003ms
        match = re.match(r".*(\d+)%\s+packet\s*loss.*", line)
        if match:
            stats.packet_loss_pct = int(match.group(1))

    return stats


def _ping_cmd(host: str, timeout: int = 10) -> str:
    """ping host using ping command"""

    if not path.exists("/usr/bin/ping"):
        raise NotImplementedError()

    ping_cmd = [
        "/usr/bin/ping",
        "-4",
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
    return proc.stdout

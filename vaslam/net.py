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
        self.packets_sent = 0  # type: int
        self.packets_recv = 0  # type: int
        self.packet_loss_pct = 0  # type: int
        self.rtt_min = 0  # type: float
        self.rtt_max = 0  # type: float
        self.rtt_avg = 0  # type: float


def ping_host(host: str, timeout: int = 15, packets: int = 5) -> PingStats:
    """ping remote host

    :raises: ConnectionError on ping timeout or errors
    """
    # @TODO: maybe support ICMP packets instead of running an external process
    return _parse_ping_output(_ping_cmd(host, timeout, packets))


def resolve_any_hostname(hostnames: List[str]) -> Tuple[str, str]:
    """Resolve IPv4 of the provided hostnames.
    Return the first resolved hostname and its address.
    Returns empty strings if none could be resolved.
    """
    # @TODO: support resovling using specified name servers

    for hostname in hostnames:
        try:
            return hostname, gethostbyname(hostname)
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
            body = resp.read().decode("utf-8")
    except (RuntimeError, URLError) as err:
        raise HttpConError("failed to http get {}: {}".format(url, err))

    return code, body


def _parse_ping_output(out: str) -> PingStats:
    """Parse output from ping command"""

    stats = PingStats()
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    for line in lines:
        # rtt min/avg/max/mdev = 9.956/10.264/10.738/0.340 ms
        match = re.search(r".*rtt.+min/avg/max.+=\s*(\S+)", line)
        if match:
            rtts = [t.strip() for t in match.group(1).strip().split("/")]
            if len(rtts) > 2:
                stats.rtt_min = float(rtts[0])
                stats.rtt_avg = float(rtts[1])
                stats.rtt_max = float(rtts[2])
            continue
        # 3 packets transmitted, 3 received, 0% packet loss, time 2003ms
        match = re.search(r"(\d+)%\s+packet\s*loss", line)
        if match:
            stats.packet_loss_pct = int(match.group(1))

        match = re.search(r"(\d+)\s+packets\s*transmit.*(\d+)\s+receiv", line)
        if match:
            stats.packets_sent = int(match.group(1))
            stats.packets_recv = int(match.group(2))

    return stats


def _ping_cmd(host: str, timeout: int = 15, packets: int = 5) -> str:
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
        str(packets),
        host,
    ]
    try:
        proc = run(ping_cmd, capture_output=True, text=True, timeout=timeout)
    except TimeoutExpired as err:
        raise ConnectionError("ping host {} timedout".format(host))
    if proc.returncode != 0 or len(proc.stderr):
        raise ConnectionError("failed to ping host {}".format(host))
    return proc.stdout

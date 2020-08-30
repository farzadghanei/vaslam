from logging import getLogger
from queue import Queue
from threading import Thread
from typing import List, Tuple
from vaslam.conf import Conf
from vaslam.net import ping_host, resolve_any_hostname, http_get, PingStats


LOCALNET_UNKNOWN = 101
LOCALNET_GATEWAY_UNREACHABLE = 102
LOCALNET_PACKET_LOSS_HIGH = 103
LOCALNET_LATENCY_HIGH = 104
LOCALNET_PACKET_LOSS = 105
LOCALNET_LATENCY = 106
INTERNET_UNKNOWN = 201
INTERNET_UNREACHABLE = 202
INTERNET_PACKET_LOSS_HIGH = 203
INTERNET_LATENCY_HIGH = 204
INTERNET_PACKET_LOSS = 205
INTERNET_LATENCY = 206
DNS_FAIL = 300
HTTP_FAIL = 400


logger = getLogger(__name__)


class Result:
    """Represents the results of diagnosis"""

    default_packet_loss_high_threshold = 15
    default_packet_loss_threshold = 5
    default_latency_high_threshold = 700
    default_latency_threshold = 300

    def __init__(self):
        self.internet = False  # type: bool
        self.localnet = False  # type: bool
        self.dns = False  # type: bool
        self.local_dns = False  # type: bool
        self.http = False  # type: bool
        self.ipv4 = ""  # type: str
        self.gateway_ping_stats = PingStats()  # type: PingStats
        self.internet_ping_stats = PingStats()  # type: PingStats

    @staticmethod
    def new_all_ok():
        rsl = Result()
        rsl.internet = True
        rsl.localnet = True
        rsl.dns = True
        rsl.local_dns = True
        rsl.http = True
        return rsl

    def get_issues(self) -> List[int]:
        """Returns a list of issues codes for the current Result.
        Empty list means there is no issue.
        """
        issues = []
        if self.localnet:
            gw_loss, gw_rtt = (
                self.gateway_ping_stats.packet_loss_pct,
                self.gateway_ping_stats.rtt_avg,
            )
            if gw_loss > self.default_packet_loss_high_threshold:
                issues.append(LOCALNET_PACKET_LOSS_HIGH)
            elif gw_loss > self.default_packet_loss_threshold:
                issues.append(LOCALNET_PACKET_LOSS)

            if gw_rtt > self.default_latency_high_threshold:
                issues.append(LOCALNET_LATENCY_HIGH)
            elif gw_rtt > self.default_latency_threshold:
                issues.append(LOCALNET_LATENCY)
        elif self.gateway_ping_stats.packets_sent < 1:
            issues.append(LOCALNET_UNKNOWN)
        else:
            issues.append(LOCALNET_GATEWAY_UNREACHABLE)

        if self.internet:
            in_loss, in_rtt = (
                self.internet_ping_stats.packet_loss_pct,
                self.internet_ping_stats.rtt_avg,
            )
            if in_loss > self.default_packet_loss_high_threshold:
                issues.append(INTERNET_PACKET_LOSS_HIGH)
            elif in_loss > self.default_packet_loss_threshold:
                issues.append(INTERNET_PACKET_LOSS)

            if in_rtt > self.default_latency_high_threshold:
                issues.append(INTERNET_LATENCY_HIGH)
            elif in_rtt > self.default_latency_threshold:
                issues.append(INTERNET_LATENCY)
        elif self.internet_ping_stats.packets_sent < 1:
            issues.append(INTERNET_UNKNOWN)
        else:
            issues.append(INTERNET_UNREACHABLE)

        if not self.dns:
            issues.append(DNS_FAIL)

        if not self.http:
            issues.append(HTTP_FAIL)

        return issues


def check_dns(hostnames: List[str]) -> Tuple[str, str]:
    """Check DNS by resolving the hostnames.
    Return the resolved hostname and the IPv4 address.
    Returns empty strings if none could be resolved.
    """
    logger.debug("resovling hostnames: {}".format(', '.join(hostnames)))
    return resolve_any_hostname(hostnames)


def check_ping_ipv4(hosts: List[str]) -> Tuple[str, PingStats]:
    """Ping spcified hosts, returns a tuple, of
    the first host address that could be pinged, and the ping stats.
    Address would be an empty string if none of the hosts could be pinged.
    """
    ping_stats = PingStats()
    for host in hosts:
        logger.debug("pinging host {}".format(host))
        ping_stats = ping_host(host)  # @TODO: increase packets to get more accurate results
        if ping_stats.packets_recv > 0:
            return (host, ping_stats)
    return "", ping_stats


def get_visible_ipv4(urls: List[str]) -> str:
    """Return visible IPv4 address of current host.
    Return empty string if could not detect the visible IPv4 address.
    """
    for url in urls:
        try:
            logger.debug("getting visible ipv4 from {}".format(url))
            _, ip = http_get(url)
            if ip:
                return ip.strip()
        except RuntimeError as err:
            logger.exception(
                "error when getting visible ipv4 from {}: {}".format(url, err)
            )
            pass
    return ""


def diagnose_network(conf: Conf) -> Result:
    def _ns_ipv4(names, urls, que):
        name, _ = check_dns(names)
        que.put(('dns', True if name else False))
        ipv4 = get_visible_ipv4(urls) if name else ""
        que.put(('ipv4', ipv4))
        que.put(('http', True if ipv4 else False))

    def _ping_gw(gw, que):
        host, ping_stats = check_ping_ipv4([gw])
        que.put(('gw', (host, ping_stats)))

    def _ping_in(hosts, que):
        host, ping_stats = check_ping_ipv4(hosts)
        que.put(('internet', (host, ping_stats)))

    resq = Queue()  # type: Queue
    check_threads = []  # type: List[Thread]
    check_threads.append(Thread(target=_ping_gw, args=(conf.ipv4_gateway, resq)))
    check_threads.append(Thread(target=_ping_in, args=(conf.ipv4_ping_hosts, resq)))
    check_threads.append(Thread(target=_ns_ipv4, args=(conf.hostnames, conf.ipv4_echo_urls, resq)))
    for th in check_threads:
        th.start()

    for th in check_threads:
        th.join()

    result = Result()  # type: Result
    while resq.qsize():
        type_, val = resq.get()
        if type_ == 'dns':
            result.dns = bool(val)
        elif type_ == 'ipv4':
            result.ipv4 = str(val)
        elif type_ == 'http':
            result.http = bool(val)
        elif type_ == 'gw':
            gateway, result.gateway_ping_stats = val
            result.localnet = gateway != ""
        elif type_ == 'internet':
            remote_host, result.internet_ping_stats = val
            result.internet = remote_host != ""

    # even if ping didn't work, since DNS worked it's safe to say
    # Internet connection works
    if result.dns:
        result.internet = True
        result.localnet = True

    return result

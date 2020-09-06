from logging import getLogger
from queue import Queue
from threading import Thread
from typing import List, Mapping
from vaslam.conf import Conf
from vaslam.check import check_dns, check_ping_ipv4, get_visible_ipv4
from vaslam.net import PingStats


LOCALNET_UNKNOWN = 101  # type :int
LOCALNET_GATEWAY_UNREACHABLE = 102  # type :int
LOCALNET_PACKET_LOSS_HIGH = 103  # type :int
LOCALNET_LATENCY_HIGH = 104  # type :int
LOCALNET_PACKET_LOSS = 105  # type :int
LOCALNET_LATENCY = 106  # type :int
INTERNET_UNKNOWN = 201  # type :int
INTERNET_UNREACHABLE = 202  # type :int
INTERNET_PACKET_LOSS_HIGH = 203  # type :int
INTERNET_LATENCY_HIGH = 204  # type :int
INTERNET_PACKET_LOSS = 205  # type :int
INTERNET_LATENCY = 206  # type :int
DNS_FAIL = 300  # type :int
HTTP_FAIL = 400  # type :int


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


def issue_message(code: int) -> str:
    """Return human readable message regarding the issue code.
    Return emptyr string for unknown codes.
    """
    messages = {
        LOCALNET_UNKNOWN: "Local network connection quality is unknown",
        LOCALNET_GATEWAY_UNREACHABLE: "Local network gateway is unreachable",
        LOCALNET_PACKET_LOSS_HIGH: "Local network has high packet loss",
        LOCALNET_LATENCY_HIGH: "Local network has high latency",
        LOCALNET_PACKET_LOSS: "Local network has packet loss",
        LOCALNET_LATENCY: "Local network has latency",
        INTERNET_UNKNOWN: "Quality of connection to the Internet is unknown",
        INTERNET_UNREACHABLE: "Internet is unreachable",
        INTERNET_PACKET_LOSS_HIGH: "Connection to the Internet has high packet loss",
        INTERNET_LATENCY_HIGH: "Connection to the Internet has high latency",
        INTERNET_PACKET_LOSS: "Connection to the Internet has packet loss",
        INTERNET_LATENCY: "Connection to the Internet has latency",
        DNS_FAIL: "Name resolution failed, DNS issue",
        HTTP_FAIL: "Web access failed",
    }  # type: Mapping[int, str]
    return messages.get(code, '')


def diagnose_network(conf: Conf) -> Result:
    """Diagnose network and Internet connection using the provided configuration.
    Runs checks concurrently. Returns the results as a Result instance.
    """

    def _ns_ipv4(names, urls, que):
        name, _, _, _ = check_dns(names)
        que.put(("dns", True if name else False))
        ipv4, _ = get_visible_ipv4(urls) if name else "", 0
        que.put(("ipv4", ipv4))
        que.put(("http", True if ipv4 else False))

    def _ping_gw(gw, que):
        host, ping_stats = check_ping_ipv4([gw])
        que.put(("gw", (host, ping_stats)))

    def _ping_in(hosts, que):
        host, ping_stats = check_ping_ipv4(hosts)
        que.put(("internet", (host, ping_stats)))

    resq = Queue()  # type: Queue
    check_threads = []  # type: List[Thread]
    check_threads.append(Thread(target=_ping_gw, args=(conf.ipv4_gateway, resq)))
    check_threads.append(Thread(target=_ping_in, args=(conf.ipv4_ping_hosts, resq)))
    check_threads.append(
        Thread(target=_ns_ipv4, args=(conf.hostnames, conf.ipv4_echo_urls, resq))
    )
    for th in check_threads:
        th.start()

    for th in check_threads:
        th.join()

    result = Result()  # type: Result
    while resq.qsize():
        type_, val = resq.get()
        if type_ == "dns":
            result.dns = bool(val)
        elif type_ == "ipv4":
            result.ipv4 = str(val)
        elif type_ == "http":
            result.http = bool(val)
        elif type_ == "gw":
            gateway, result.gateway_ping_stats = val
            result.localnet = gateway != ""
        elif type_ == "internet":
            remote_host, result.internet_ping_stats = val
            result.internet = remote_host != ""

    # even if ping didn't work, since DNS worked it's safe to say
    # Internet connection works
    if result.dns:
        result.internet = True
        result.localnet = True

    return result

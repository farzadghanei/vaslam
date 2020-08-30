from logging import getLogger
from typing import List, Tuple
from vaslam.conf import Conf
from vaslam.net import ping_host, resolve_any_hostname, http_get, PingStats


logger = getLogger(__name__)


class Result:
    """Represents the results of diagnosis"""

    def __init__(self):
        self.internet = False  # type: bool
        self.localnet = False  # type: bool
        self.dns = False  # type: bool
        self.local_dns = False  # type: bool
        self.ipv4 = ""  # type: str
        self.gateway_ping_stats = PingStats()  # type: PingStats
        self.internet_ping_stats = PingStats()  # type: PingStats

    @staticmethod
    def all_ok():
        rsl = Result()
        rsl.internet = True
        rsl.localnet = True
        rsl.dns = True
        rsl.local_dns = True
        return rsl


def check_dns(name_servers: List[str], hostnames: List[str]) -> str:
    """Check DNS by resolving the hostnames from the specified name servers.
    Return the first name server address that could resolve any of the hostnames.
    Return emptry string if none of the name servers could resolve any of the hostnames.
    """
    logger.warning("checking individual name server is not supported yet!")
    hostname, ip = resolve_any_hostname(hostnames)
    return ip
    for ns in name_servers:
        logger.wa("checking name server {}".format(ns))
        hostname, ip = resolve_any_hostname(hostnames)
        if ip:
            return ns
    return ""


def check_ping_ipv4(hosts: List[str]) -> Tuple[str, PingStats]:
    """Ping spcified hosts, returns the first host address that could be pinged.
    Return empty string if none of the hosts could be pinged.
    """
    ping_stats = PingStats()
    for host in hosts:
        logger.debug("pinging host {}".format(host))
        ping_stats = ping_host(host)
        if ping_stats.connected():
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
                return ip
        except RuntimeError as err:
            logger.exception(
                "error when getting visible ipv4 from {}: {}".format(url, err)
            )
            pass
    return ""


def diagnose_network(conf: Conf) -> Result:
    dns_ok = check_dns(conf.ipv4_default_name_servers, conf.hostnames)
    ipv4 = dns_ok and get_visible_ipv4(conf.ipv4_echo_urls)

    if ipv4:
        result = Result.all_ok()
        result.ipv4 = ipv4
    else:
        result = Result()
        result.dns = dns_ok

    gateway, result.gateway_ping_stats = check_ping_ipv4([conf.ipv4_gateway])
    remote_host, result.internet_ping_stats = check_ping_ipv4(conf.ipv4_ping_hosts)

    if dns_ok:
        result.internet = True
        result.localnet = True
    else:
        result.internet = remote_host != ""
        result.localnet = gateway != ""

    return result

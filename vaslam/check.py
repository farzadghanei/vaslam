from logging import getLogger
from typing import List
from vaslam.conf import Conf
from vaslam.net import ping_host, resolve_any_domain, http_get


logger = getLogger(__name__)


class Result:
    """Represents the results of diagnosis"""

    def __init__(self):
        self.internet = False  # type: bool
        self.localnet = False  # type: bool
        self.dns = False  # type: bool
        self.local_dns = False  # type: bool
        self.ipv4 = ""  # type: str

    @staticmethod
    def all_ok():
        rsl = Result()
        rsl.internet = True
        rsl.localnet = True
        rsl.dns = True
        rsl.local_dns = True
        return rsl


def check_dns(name_servers: List[str], domains: List[str]) -> str:
    """Check DNS by resolving the domains from the specified name servers.
    Return the first name server address that could resolve any of the domains.
    Return emptry string if none of the name servers could resolve any of the domains.
    """
    for ns in name_servers:
        logger.debug("checking name server {}".format(ns))
        if resolve_any_domain(ns, domains):
            return ns
    return ""


def check_ping_ipv4(hosts: List[str]) -> str:
    """Ping spcified hosts, returns the first host address that could be pinged.
    Return emptyr string if none of the hosts could be pinged.
    """
    for host in hosts:
        logger.debug("pinging host {}".format(host))
        if ping_host(host):
            return host
    return ""


def get_visible_ipv4(urls: List[str]) -> str:
    """Return visible IPv4 address of current host.
    Return empty string if could not detect the visible IPv4 address.
    """
    for url in urls:
        try:
            logger.debug("getting visible ipv4 from {}".format(url))
            ip = http_get(url)
            if ip:
                return ip
        except RuntimeError as err:
            logger.exception(
                "error when getting visible ipv4 from {}: {}".format(url, err)
            )
            pass
    return ""


def diagnose_network(conf: Conf) -> Result:
    local_dns = check_dns(conf.name_servers, conf.domains)
    dns_ok = local_dns or check_dns(conf.default_name_servers, conf.domains)
    ipv4 = dns_ok and get_visible_ipv4(conf.ipv4_echo_urls)

    if ipv4:
        result = Result.all_ok()
        result.ipv4 = ipv4
        return result

    result = Result()
    result.dns = dns_ok
    result.local_dns = local_dns

    if dns_ok:
        result.internet = True
        result.localnet = True
        return result

    result.localnet = check_ping_ipv4(conf.gateways)
    result.internet = check_ping_ipv4(conf.ping_hosts)
    return result

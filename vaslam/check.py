from logging import getLogger
from typing import List, Tuple
from vaslam.net import ping_host, resolve_any_hostname, http_get, PingStats


logger = getLogger(__name__)


def check_dns(hostnames: List[str]) -> Tuple[str, str, float, str]:
    """Check DNS by resolving the hostnames.
    Return a tuple of info of:
        - the first resolved hostname
        - the resolved address
        - miliseconds that took to resolve
        - IP address of the resolver (currently empty until implemented)
    Returns empty strings and zero numerics if none could be resolved.
    """
    logger.debug("resovling hostnames: {}".format(", ".join(hostnames)))
    return resolve_any_hostname(hostnames)


def check_ping_ipv4(hosts: List[str]) -> Tuple[str, PingStats]:
    """Ping spcified hosts, returns a tuple, of
    the first host address that could be pinged, and the ping stats.
    Address would be an empty string if none of the hosts could be pinged.
    """
    ping_stats = PingStats()
    for host in hosts:
        logger.debug("pinging host {}".format(host))
        ping_stats = ping_host(
            host
        )  # @TODO: increase packets to get more accurate results
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

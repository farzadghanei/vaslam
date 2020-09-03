from time import time
from logging import getLogger
from typing import List, Tuple
from vaslam.net import (
    ping_host,
    resolve_any_hostname,
    http_get,
    PingStats,
    ConnectionError,
    HttpConError,
)


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
        try:
            ping_stats = ping_host(
                host, 15, 5
            )  # @TODO: increase packets to get more accurate results
        except ConnectionError as err:
            logger.warning("failed to ping '{}'. {}".format(host, err))
            # @TODO: maybe find a more accurate way to signal ping failure
            ping_stats = PingStats()
            ping_stats.packets_sent = 5
            ping_stats.packet_loss_pct = 100
        if ping_stats.packets_recv > 0:
            logger.info("did ping host {}".format(host))
            return (host, ping_stats)
    return "", ping_stats


def get_visible_ipv4(urls: List[str]) -> Tuple[str, float]:
    """Return visible IPv4 address of current host, and the time it took
    to call the URL and get results.
    Return empty string and zero time if could not detect the visible IPv4 address.
    """
    for url in urls:
        try:
            logger.debug("getting visible ipv4 from {}".format(url))
            start = float(time() * 1000)
            _, ip = http_get(url)
            if ip:
                return ip.strip(), (float(time() * 1000) - start)
        except HttpConError as err:
            logger.warning("failed to get visible ipv4 from {}: {}".format(url, err))
    return "", 0

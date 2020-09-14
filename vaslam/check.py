from time import time
from logging import getLogger
from threading import Event
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


def check_dns(hostnames: List[str], stop: Event = None) -> Tuple[str, str, float, str]:
    """Check DNS by resolving the IPv4 of the hostnames.
    Return a tuple of info of:
        - the first resolved hostname
        - the resolved address
        - miliseconds that took to resolve
        - IP address of the resolver (currently empty until implemented)
    Returns empty strings and zero numerics if none could be resolved.
    """
    for hostname in hostnames:
        if stop and stop.is_set():
            logger.debug("stopping resovling hostnames due to stop event")
            break
        logger.debug("resovling hostname: {}".format(hostname))
        host, addr, dur, res = resolve_any_hostname([hostname])
        if host and addr:
            logger.info(
                "hostname {} resolved to address {} after {:.2f} milliseconds".format(
                    host, addr, dur
                )
            )
            return host, addr, dur, res
    logger.warning("couldn't resolve any hostname of: {}".format(", ".join(hostnames)))
    return "", "", 0, ""


def check_ping_ipv4(hosts: List[str], stop: Event = None) -> Tuple[str, PingStats]:
    """Ping spcified hosts, returns a tuple, of
    the first host address that could be pinged, and the ping stats.
    Address would be an empty string if none of the hosts could be pinged.
    """
    ping_stats = PingStats()
    # @TODO: maybe find a more accurate way to signal ping failure
    ping_stats = PingStats()
    ping_stats.packets_sent = 5
    ping_stats.packet_loss_pct = 100
    for host in hosts:
        if stop and stop.is_set():
            logger.debug("stopping pinging hosts due to stop event")
            break
        logger.debug("pinging host {}".format(host))
        try:
            ping_stats = ping_host(
                host, 15, 5
            )  # @TODO: increase packets to get more accurate results
        except ConnectionError as err:
            logger.warning("failed to ping '{}'. {}".format(host, err))
        if ping_stats.packets_recv > 0:
            logger.info("did ping host {}".format(host))
            return (host, ping_stats)
    logger.warning("couldn'ping any host of: {}".format(", ".join(hosts)))
    return "", ping_stats


def get_visible_ipv4(urls: List[str], stop: Event = None) -> Tuple[str, float]:
    """Return visible IPv4 address of current host, and the time it took
    to call the URL and get results.
    Return empty string and zero time if could not detect the visible IPv4 address.
    """
    for url in urls:
        if stop and stop.is_set():
            logger.debug("stopping getting visible IPv4 due to stop event")
            break
        try:
            logger.debug("getting visible ipv4 from {}".format(url))
            start = float(time() * 1000)
            _, ip = http_get(url)
            if ip:
                ip = ip.strip()
                logger.info("visible ipv4 is {}".format(ip))
                return ip, (float(time() * 1000) - start)
        except HttpConError as err:
            logger.warning("failed to get visible ipv4 from {}: {}".format(url, err))
    logger.warning("failed to get visible ipv4".format())
    return "", 0

"""
vaslam.system
=============

provide information from the host operating system
"""
from os import path
from subprocess import run
from logging import getLogger
from typing import List


logger = getLogger(__name__)


def get_name_servers() -> List[str]:
    """Return list of name servers configured to resolve names for the system"""
    name_servers = _resolvconf_name_servers()
    if not name_servers:
        name_servers = _network_manager_name_servers()
    # @TODO: support systemd-resolvd if no name servers found yet
    return name_servers


def get_gateway_ipv4() -> str:
    """Return system gateway host IPv4 address"""

    gw_addr = _get_gateway_from_procfs()
    if not len(gw_addr) == 8:
        logger.warning("found no IPv4 for default gateway from /proc")
        return ""

    logger.debug("/proc reports gateway to be: {}".format(gw_addr))
    # convert hex octets from proc to dot-decimal notation
    octets = []
    for i in range(
        8, 1, -2
    ):  # walk back from the end by 2 chars, proc reports addr backwards
        hex_oct = gw_addr[i - 2 : i]
        octets.append(str(int(hex_oct, 16)))

    return ".".join(octets)


def _get_gateway_from_procfs() -> str:
    """Return the raw value for default gateway from profs or empty string"""

    with open("/proc/net/route", "rt") as fh:
        lines = [l.strip() for l in fh.readlines() if l.strip()]

    if len(lines) < 2:
        logger.warning("can't find gateway from /proc. empty routing table")
        return ""

    lines = lines[1:]  # skip the headers

    # lines are like:
    # Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT
    for line in lines:
        words = [w.strip() for w in line.split() if w.strip()]
        if len(words) < 3:  # fail safe, shouldn't happen
            continue
        dst = words[1]
        try:
            if int(dst) == 0:
                return words[2]
        except ValueError:
            continue

    return ""


def _resolvconf_name_servers() -> List[str]:
    """Find system name servers from resolv.conf file"""

    if not path.exists("/etc/resolv.conf") or not path.isfile("/etc/resolv.conf"):
        logger.debug("no name servers from resolv.conf. not an existing file")
        return []
    with open("/etc/resolv.conf") as fh:
        lines = fh.readlines()
    lines = [l.strip() for l in lines if l.strip().startswith("nameserver")]
    logger.debug("finding name servers from {} lines of resolv.conf".format(len(lines)))
    servers = [l.split(" ")[-1].strip() for l in lines]
    return [s for s in servers if s]


def _network_manager_name_servers() -> List[str]:
    """Find system name servers as reported by NetworkManager (if available)"""

    if not path.exists("/usr/bin/nmcli"):
        logger.debug("no name servers from network manager. nmcli is not available")
        return []

    cmd = ["/usr/bin/nmcli", "--terse", "dev", "show"]

    logger.debug("finding name servers from network manager")
    proc = run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout:
        logger.warning(
            "failed to find name servers from network manager. nmcli returned {}".format(
                proc.returncode
            )
        )
        return []
    # sample line
    # IP4.DNS[1]:192.168.0.1
    lines = [l.strip() for l in proc.stdout.splitlines() if "DNS" in l.strip().upper()]
    logger.debug(
        "getting name servers from {} lines of network manager".format(len(lines))
    )
    servers = [l.partition(":")[2].strip() for l in lines]
    return [s for s in servers if s]

"""
vaslam.system
=============

provide information from the host operating system
"""
from typing import List


def get_name_servers() -> List[str]:
    """Return list of name servers configured to resolve names for the system"""

    return []


def get_gateway_addr() -> str:
    """Return system gateway host address"""

    return ""

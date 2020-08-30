from vaslam.system import get_name_servers, get_gateway_ipv4


default_hostnames = [
    "www.fedoraproject.org",
    "www.opensuse.org",
    "www.debian.org",
    "www.ubuntu.com",
]
default_ipv4_name_servers = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
default_ipv4_ping_hosts = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
default_ipv4_echo_urls = [
    "http://icanhazip.com/ip",
    "http://ifconfig.io/ip",
    "http://ifconfig.me/ip",
]


class Conf:
    def __init__(self):
        self.hostnames = []  # type: List[str]
        self.name_servers = []  # type: List[str]
        self.ipv4_gateway = ""  # type: str
        self.ipv4_default_name_servers = []  # type: List[str]
        self.ipv4_ping_hosts = []  # type: List[str]
        self.ipv4_echo_urls = []  # type: List[str]


def default_conf() -> Conf:
    conf = Conf()
    conf.hostnames = default_hostnames
    conf.name_servers = get_name_servers()
    conf.ipv4_default_name_servers = default_ipv4_name_servers
    conf.ipv4_ping_hosts = default_ipv4_ping_hosts
    conf.ipv4_gateway = get_gateway_ipv4()
    conf.ipv4_echo_urls = default_ipv4_echo_urls
    return conf

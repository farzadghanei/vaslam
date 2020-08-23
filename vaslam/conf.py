from vaslam.system import get_name_servers, get_gateway_addr


default_name_servers = ("1.1.1.1", "8.8.8.8", "9.9.9.9")
default_domains = ("fedoraproject.org", "opensuse.org", "icanhazip.com", "ifconfig.io")
default_ping_hosts = ("1.1.1.1", "8.8.8.8", "9.9.9.9")
default_ipv4_echo_urls = (
    "http://icanhazip.com/ip",
    "http://ifconfig.io/ip",
    " http://ifconfig.me/ip",
)


class Conf:
    def __init__(self):
        self.gateways = []  # type: List[str]
        self.name_servers = []  # type: List[str]
        self.default_name_servers = []  # type: List[str]
        self.ping_hosts = []  # type: List[str]
        self.ipv4_echo_urls = []  # type: List[str]


def default_conf() -> Conf:
    conf = Conf()
    conf.domains = default_domains
    conf.name_servers = get_name_servers()
    conf.default_name_servers = default_name_servers
    conf.ping_hosts = default_ping_hosts
    conf.gateways = [get_gateway_addr()]
    conf.ipv4_echo_urls = default_ipv4_echo_urls
    return conf

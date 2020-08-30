from vaslam.conf import (
    Conf,
    default_conf,
    default_hostnames,
    default_ipv4_name_servers,
    default_ipv4_ping_hosts,
    default_ipv4_echo_urls,
)
from unittest import TestCase
from unittest.mock import patch


class TestDefaultConf(TestCase):
    def setUp(self):
        patcher = patch("vaslam.conf.get_name_servers")
        self.addCleanup(patcher.stop)
        self.mock_get_ns = patcher.start()
        self.mock_get_ns.return_value = ["192.168.0.100"]

        patcher = patch("vaslam.conf.get_gateway_ipv4")
        self.addCleanup(patcher.stop)
        self.mock_get_gw = patcher.start()
        self.mock_get_gw.return_value = "192.168.0.1"

    def test_default_conf_returns_a_conf_with_defaults(self):
        ret = default_conf()
        self.assertIsInstance(ret, Conf)
        self.assertEqual(ret.hostnames, default_hostnames)
        self.assertEqual(ret.ipv4_default_name_servers, default_ipv4_name_servers)
        self.assertEqual(ret.ipv4_ping_hosts, default_ipv4_ping_hosts)
        self.assertEqual(ret.ipv4_echo_urls, default_ipv4_echo_urls)

    def test_default_conf_returns_system_name_servers_and_default_gateway(self):
        ret = default_conf()
        self.assertEqual(ret.name_servers, ["192.168.0.100"])
        self.mock_get_ns.assert_called_once_with()
        self.assertEqual(ret.ipv4_gateway, "192.168.0.1")
        self.mock_get_gw.assert_called_once_with()

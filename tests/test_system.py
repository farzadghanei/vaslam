from subprocess import CompletedProcess
from unittest import TestCase
from unittest.mock import patch, call, mock_open
from vaslam.system import get_name_servers, get_gateway_ipv4


class TestGetNameServers(TestCase):
    def setUp(self):
        patcher = patch("vaslam.system.path")
        self.addCleanup(patcher.stop)
        self.mock_path = patcher.start()
        self.mock_path.exists.return_value = True
        self.mock_path.isfile.return_value = True

        self.mock_resolvconf = """
# mocked /etc/resolv.conf
search localdomain
nameserver 127.0.0.1
# nameserver 192.168.1.100
 nameserver     192.168.0.1
        """
        self.mock_open = mock_open(read_data=self.mock_resolvconf)
        self.open_patcher = patch("vaslam.system.open", self.mock_open)
        self.addCleanup(self.open_patcher.stop)
        self.open_patcher.start()

        self.mock_nmcli_out = """
GENERAL.DEVICE:eth0
GENERAL.MTU:1500
GENERAL.STATE:100 (connected)
IP4.ADDRESS[1]:192.168.0.2/24
IP4.GATEWAY:192.168.0.1
IP4.DNS[1]:192.168.0.2
IP4.DNS[2]:127.0.0.2
IP4.DOMAIN[1]:local
"""
        self.mock_run_result = CompletedProcess(
            ("/usr/bin/nmcli", "dev", "show"), 0, self.mock_nmcli_out, ""
        )
        patcher = patch("vaslam.system.run")
        self.addCleanup(patcher.stop)
        self.mock_run = patcher.start()
        self.mock_run.return_value = self.mock_run_result

    def test_get_name_servers_returns_list_of_ns_in_resolvconf_if_exists(self):
        self.assertEqual(["127.0.0.1", "192.168.0.1"], get_name_servers())
        self.mock_path.exists.assert_called_once_with("/etc/resolv.conf")
        self.mock_path.isfile.assert_called_once_with("/etc/resolv.conf")
        self.mock_open.assert_called_once_with("/etc/resolv.conf")

    def test_get_name_servers_wont_run_nmcli_if_resolvconf_exists(self):
        get_name_servers()
        self.assertFalse(self.mock_run.called)

    def test_get_name_servers_checks_for_and_runs_nmcli_when_no_resolvconf(self):
        self.mock_path.exists.side_effect = [False, True]
        self.assertEqual(["192.168.0.2", "127.0.0.2"], get_name_servers())
        self.mock_path.exists.assert_has_calls(
            [call("/etc/resolv.conf"), call("/usr/bin/nmcli")]
        )
        self.assertTrue(self.mock_run.called)

    def test_get_name_servers_runs_nmcli_when_resolvconf_is_not_a_file(self):
        self.mock_path.isfile.return_value = False
        self.assertEqual(["192.168.0.2", "127.0.0.2"], get_name_servers())
        self.assertTrue(self.mock_run.called)

    def test_get_name_servers_runs_nmcli_when_resolvconf_has_no_nameservers(self):
        mocked_open = mock_open(read_data="# no name servers in resolv.conf")
        patcher = patch("vaslam.system.open", mocked_open)
        self.addCleanup(patcher.stop)
        patcher.start()

        self.assertEqual(["192.168.0.2", "127.0.0.2"], get_name_servers())

        self.assertTrue(self.mock_run.called)

    def test_get_name_servers_returns_empty_when_nmcli_fails(self):
        self.mock_path.isfile.return_value = False
        mock_run_result = CompletedProcess(("/usr/bin/nmcli", "dev", "show"), 1, "", "")
        self.mock_run.return_value = mock_run_result
        self.assertEqual([], get_name_servers())

    def test_get_name_servers_returns_empty_when_resolvconf_nor_nmcli_exist(self):
        self.mock_path.exists.return_value = False
        self.assertEqual([], get_name_servers())
        self.assertFalse(self.mock_run.called)


class TestGetGatewayIpv4(TestCase):
    def _mock_open(self, data):
        self.mock_open = mock_open(read_data=data)
        patcher = patch("vaslam.system.open", self.mock_open)
        self.addCleanup(patcher.stop)
        patcher.start()

    def setUp(self):
        self.mock_route = r"""
Iface	Destination	Gateway 	Flags	RefCnt	Use	Metric	Mask		MTU	Window	IRTT
eth0	00000000	0101A8C0	0003	0	0	600	00000000	0	0	0
eth1	000011AC	00000000	0001	0	0	0	0000FFFF	0	0	0
        """
        self._mock_open(self.mock_route)

    def test_get_gateway_ipv4_returns_default_gateway(self):
        self.assertEqual("192.168.1.1", get_gateway_ipv4())

    def test_get_gateway_ipv4_returns_empty_str_if_no_route_rules(self):
        route = r"""
Iface	Destination	Gateway 	Flags	RefCnt	Use	Metric	Mask		MTU	Window	IRTT
        """
        self._mock_open(route)
        self.assertEqual("", get_gateway_ipv4())

    def test_get_gateway_ipv4_returns_empty_str_if_no_route_table(self):
        self._mock_open("")
        self.assertEqual("", get_gateway_ipv4())

    def test_get_gateway_ipv4_returns_empty_str_on_incorrect_route_rules(self):
        route = r"""
Iface	Destination	Gateway 	Flags	RefCnt	Use	Metric	Mask		MTU	Window	IRTT
eth0	00000000
        """
        self._mock_open(route)
        self.assertEqual("", get_gateway_ipv4())

        route = r"""
Iface	Destination	Gateway
eth0	00000000
        """
        self._mock_open(route)
        self.assertEqual("", get_gateway_ipv4())

        route = r"""
Iface	Destination	Gateway 	Flags	RefCnt	Use	Metric	Mask		MTU	Window	IRTT
eth0	invalid         0101A8C0	0003	0	0	600	00000000	0	0	0
        """
        self._mock_open(route)
        self.assertEqual("", get_gateway_ipv4())

        route = r"""
Iface	Destination	Gateway 	Flags	RefCnt	Use	Metric	Mask		MTU	Window	IRTT
eth0	00000000        0101A8          0003	0	0	600	00000000	0	0	0
        """
        self._mock_open(route)
        self.assertEqual("", get_gateway_ipv4())

    def test_get_gateway_ipv4_returns_empty_if_no_default_gateway_in_table(self):
        route = r"""
Iface	Destination	Gateway 	Flags	RefCnt	Use	Metric	Mask		MTU	Window	IRTT
eth0	000011AC	0101A8C0	0003	0	0	600	00000000	0	0	0
eth1	000011AC	00000000	0001	0	0	0	0000FFFF	0	0	0
        """
        self._mock_open(route)
        self.assertEqual("", get_gateway_ipv4())

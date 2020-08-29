from urllib.error import URLError
from subprocess import CompletedProcess, TimeoutExpired
from unittest import TestCase
from unittest.mock import Mock, patch, call
from vaslam.net import (
    _parse_ping_output,
    ping_host,
    http_get,
    resolve_any_domain,
    PingStats,
    ConnectionError,
    HttpConError,
)


class TestPingStats(TestCase):
    def test_ping_stats_default_is_all_zero(self):
        ps = PingStats()
        self.assertEqual(0, ps.packet_loss_pct)
        self.assertEqual(0, ps.rtt_min)
        self.assertEqual(0, ps.rtt_max)
        self.assertEqual(0, ps.rtt_avg)

    def test_ping_stats_all_zero_is_not_connected(self):
        ps = PingStats()
        self.assertFalse(ps.connected())

    def test_ping_stats_less_than_100_pct_loss_and_some_max_is_connected(self):
        ps = PingStats()
        ps.packet_loss_pct = 99
        ps.rtt_max = 0.001
        self.assertTrue(ps.connected())

    def test_ping_stats_less_than_100_pct_loss_and_no_max_is_not_connected(self):
        ps = PingStats()
        ps.packet_loss_pct = 90
        self.assertFalse(ps.connected())

    def test_ping_stats_100_loss_and_some_max_is_not_connected(self):
        ps = PingStats()
        ps.packet_loss_pct = 100
        ps.rtt_max = 0.001
        self.assertFalse(ps.connected())


class TestPing(TestCase):
    def setUp(self):
        self.mock_ping_output = """
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.

--- 127.0.0.1 ping statistics ---
3 packets transmitted, 3 received, 1% packet loss, time 2063ms
rtt min/avg/max/mdev = 0.079/0.083/0.087/0.003 ms
            """
        self.mock_run_result = CompletedProcess(
            ("/usr/bin/ping",), 0, self.mock_ping_output, ""
        )

        patch_path = patch("vaslam.net.path")
        self.addCleanup(patch_path.stop)
        self.mock_path = patch_path.start()
        self.mock_path.exists.return_value = True

        patch_run = patch("vaslam.net.run")
        self.addCleanup(patch_run.stop)
        self.mock_run = patch_run.start()
        self.mock_run.return_value = self.mock_run_result

    def test_ping_host_checks_ping_cmd_exists_then_runs_it(self):
        ret = ping_host("127.0.10.10", 8)

        self.mock_path.exists.assert_called_once_with("/usr/bin/ping")
        self.mock_run.assert_called_once_with(
            ["/usr/bin/ping", "-4", "-q", "-w", "8", "-c", "3", "127.0.10.10"],
            capture_output=True,
            text=True,
            timeout=8,
        )

    def test_ping_host_returns_ping_stats(self):
        ret = ping_host("127.0.10.10")

        self.assertIsInstance(ret, PingStats)
        self.assertEqual(ret.packet_loss_pct, 1)
        self.assertEqual(ret.rtt_min, 0.079)
        self.assertEqual(ret.rtt_avg, 0.083)
        self.assertEqual(ret.rtt_max, 0.087)

    def test_ping_host_raises_error_if_ping_cmd_doesnot_exist(self):
        self.mock_path.exists.return_value = False

        with self.assertRaises(NotImplementedError):
            ping_host("127.0.0.1")

        self.mock_path.exists.assert_called_once_with("/usr/bin/ping")
        self.assertFalse(self.mock_run.called)

    def test_ping_host_raises_connection_error_on_cmd_timeout(self):
        self.mock_run.side_effect = TimeoutExpired("/usr/bin/ping", 5)

        with self.assertRaises(ConnectionError):
            ping_host("127.0.0.1", 5)

    def testping_host_raises_connection_error_when_cmd_returncode_nonzero(self):
        self.mock_run_result.returncode = 1

        with self.assertRaises(ConnectionError):
            ping_host("127.0.0.1")

    def test_ping_host_raises_connection_error_when_cmd_has_stderr(self):
        self.mock_run_result.stderr = "mocked stderr"

        with self.assertRaises(ConnectionError):
            ping_host("127.0.0.1")


class TestParsePingOutput(TestCase):
    def test_ping_parse_output_ping_s20190515_fedora(self):
        output = """
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.

--- 127.0.0.1 ping statistics ---
3 packets transmitted, 3 received, 1% packet loss, time 2063ms
rtt min/avg/max/mdev = 0.079/0.083/0.087/0.003 ms
"""
        res = _parse_ping_output(output)
        self.assertIsInstance(res, PingStats)
        self.assertEqual(1, res.packet_loss_pct)
        self.assertEqual(0.079, res.rtt_min)
        self.assertEqual(0.083, res.rtt_avg)
        self.assertEqual(0.087, res.rtt_max)

    def test_ping_parse_output_ping_s20190515_buster(self):
        output = """
PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.

--- 127.0.0.1 ping statistics ---
3 packets transmitted, 3 received, 2% packet loss, time 58ms
rtt min/avg/max/mdev = 0.066/0.087/0.099/0.016 ms
"""
        res = _parse_ping_output(output)
        self.assertIsInstance(res, PingStats)
        self.assertEqual(2, res.packet_loss_pct)
        self.assertEqual(0.066, res.rtt_min)
        self.assertEqual(0.087, res.rtt_avg)
        self.assertEqual(0.099, res.rtt_max)


class TestHttpGet(TestCase):
    def setUp(self):
        patcher = patch("vaslam.net.urlopen")
        self.addCleanup(patcher.stop)
        self.mock_urlopen = patcher.start()
        self.mock_resp = Mock()
        self.mock_resp.getcode.return_value = 200
        self.mock_resp.read.return_value = "<html></html>"
        self.mock_urlopen.return_value.__enter__.return_value = self.mock_resp

    def test_http_get_returns_http_code_and_body_tuple(self):
        ret = http_get("http://localhost")
        self.assertEqual((200, "<html></html>"), ret)

    def test_http_get_calls_urlopen_passing_timeout(self):
        http_get("http://localhost", 5)
        self.mock_urlopen.assert_called_once_with("http://localhost", timeout=5)

    def test_http_get_raises_http_con_error_on_url_errors(self):
        self.mock_urlopen.side_effect = URLError("invalid URL")
        with self.assertRaises(HttpConError):
            http_get("http://invalid")

    def test_http_get_raises_http_con_error_on_runtime_errors(self):
        self.mock_urlopen.side_effect = RuntimeError("mocked err in tests")
        with self.assertRaises(HttpConError):
            http_get("http://localhost")


class TestResolveAnyDomain(TestCase):
    def setUp(self):
        patcher = patch("vaslam.net.gethostbyname")
        self.addCleanup(patcher.stop)
        self.mock_gethostbyname = patcher.start()
        self.mock_gethostbyname.return_value = "127.0.0.1"

    def test_resolve_any_domain_returns_domain_and_resolved_address(self):
        ret = resolve_any_domain(["localhost"])
        self.assertEqual(("localhost", "127.0.0.1"), ret)

    def test_resolve_any_domain_calls_gethostbyname(self):
        ret = resolve_any_domain(["localhost"])
        self.mock_gethostbyname.assert_called_once_with("localhost")

    def test_resolve_any_domain_calls_gethostbyname_with_next_domain_on_errors(self):
        self.mock_gethostbyname.side_effect = OSError("mocked err in tests")
        ret = resolve_any_domain(["invalid.local", "localhost"])
        self.mock_gethostbyname.assert_has_calls(
            [call("invalid.local"), call("localhost")]
        )

    def test_resolve_any_domain_calls_gethostbyname_returns_empty_values_on_all_errors(
        self,
    ):
        self.mock_gethostbyname.side_effect = OSError("mocked err in tests")
        ret = resolve_any_domain(["invalid.local", "localhost"])
        self.assertEqual(("", ""), ret)

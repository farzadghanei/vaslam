from unittest import TestCase
from unittest.mock import patch, call
from vaslam.check import check_dns, check_ping_ipv4, get_visible_ipv4
from vaslam.net import ConnectionError, PingStats, HttpConError


class TestCheckDns(TestCase):
    def setUp(self):
        patcher = patch("vaslam.check.resolve_any_hostname")
        self.addCleanup(patcher.stop)
        self.mock_resolv = patcher.start()
        self.mock_resolv.return_value = ("debian.org", "127.0.0.1", 0.2, "")

    def test_check_dns_calls_resolve_any_hostname(self):
        self.assertEqual(
            ("debian.org", "127.0.0.1", 0.2, ""),
            check_dns(["debian.org", "ubuntu.com", "opensuse.org"]),
        )
        self.mock_resolv.assert_called_once_with(["debian.org"])

    def test_check_dns_wont_stop_on_failures(self):
        self.mock_resolv.side_effect = [
            ("", "", 2, ""),
            ("opensuse.org", "127.0.1.1", 0.3, ""),
        ]
        self.assertEqual(
            ("opensuse.org", "127.0.1.1", 0.3, ""),
            check_dns(["debian.org", "opensuse.org"]),
        )
        self.mock_resolv.assert_has_calls(
            [call(["debian.org"]), call(["opensuse.org"])]
        )


class TestCheckPingIpv4(TestCase):
    def setUp(self):
        patcher = patch("vaslam.check.ping_host")
        self.addCleanup(patcher.stop)
        self.mock_ping = patcher.start()
        self.ping_stats = PingStats()
        self.ping_stats.packets_recv = 1
        self.mock_ping.return_value = self.ping_stats
        patcher = patch("vaslam.check.logger")
        self.addCleanup(patcher.stop)
        self.mock_logger = patcher.start()

    def test_check_ping_calls_ping_host_and_returns_the_first_resolved_host_and_stats(
        self,
    ):
        self.assertEqual(
            ("debian.org", self.ping_stats),
            check_ping_ipv4(["debian.org", "ubuntu.com", "opensuse.org"]),
        )
        self.mock_ping.assert_called_once_with("debian.org", 15, 5)

    def test_check_ping_calls_returns_the_next_resolved_host_when_failed_to_resolve(
        self,
    ):
        def _mocked_ping(host, *args):
            if host == "opensuse.org":
                return self.ping_stats
            raise ConnectionError("mocked err in tests")

        self.mock_ping.side_effect = _mocked_ping
        self.assertEqual(
            ("opensuse.org", self.ping_stats),
            check_ping_ipv4(["debian.org", "opensuse.org", "ubuntu.com"]),
        )
        self.mock_ping.assert_has_calls(
            [call("debian.org", 15, 5), call("opensuse.org", 15, 5)]
        )
        self.mock_logger.warning.assert_called_once()

    def test_check_ping_calls_returns_empty_string_and_a_failed_ping_stats_if_all_failed(
        self,
    ):
        self.mock_ping.side_effect = ConnectionError("mocked err intests")
        host, stats = check_ping_ipv4(["debian.org", "opensuse.org", "ubuntu.com"])
        self.assertEqual("", host)
        self.assertIsInstance(stats, PingStats)
        self.assertEqual(0, stats.packets_recv)
        self.assertEqual(100, stats.packet_loss_pct)
        self.mock_ping.assert_has_calls(
            [
                call("debian.org", 15, 5),
                call("opensuse.org", 15, 5),
                call("ubuntu.com", 15, 5),
            ]
        )
        self.assertGreaterEqual(self.mock_logger.warning.call_count, 1)


class TestGetVisibleIpv4(TestCase):
    def setUp(self):
        patcher = patch("vaslam.check.http_get")
        self.addCleanup(patcher.stop)
        self.mock_http = patcher.start()
        self.mock_http.return_value = (200, "192.168.0.220")

        patcher = patch("vaslam.check.time")
        self.addCleanup(patcher.stop)
        self.mock_time = patcher.start()
        self.mock_time.side_effect = [
            1599381508.081003,
            1599381509.081003,
            1599381510.081003,
            1599381511.081003,
            1599381512.081003,
        ]
        self.urls = ["http://localhost", "http://127.0.0.1", "http://resolver"]

        patcher = patch("vaslam.check.logger")
        self.addCleanup(patcher.stop)
        self.mock_logger = patcher.start()

    def test_get_visible_ipv4_returns_response_body_and_duration_milliseconds(self):
        self.assertEqual(("192.168.0.220", 1000), get_visible_ipv4(self.urls))
        self.mock_http.assert_called_once_with(self.urls[0])

    def test_get_visible_ipv4_calls_http_get_until_a_url_succeeds(self):
        def _mock_http(url):
            if url == "http://127.0.0.1":
                return 200, "192.168.0.221"
            raise HttpConError("mocked err in tests")

        self.mock_http.side_effect = _mock_http
        ret = get_visible_ipv4(self.urls)
        self.assertEqual("192.168.0.221", ret[0])
        self.mock_http.assert_has_calls(
            [call("http://localhost"), call("http://127.0.0.1")]
        )
        self.mock_logger.warning.assert_called_once()

    def test_get_visible_ipv4_returns_empty_str_and_zero_time_if_all_urls_fail(self):
        self.mock_http.side_effect = HttpConError("mocked err in tests")
        self.assertEqual(("", 0), get_visible_ipv4(self.urls))
        self.mock_http.assert_has_calls([call(u) for u in self.urls])
        self.assertGreaterEqual(self.mock_logger.warning.call_count, 1)

import socket
from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from .infrastructure.adapters import HttpAllyServiceAdapter, ThirdPartyExchangeRateAdapter
from .interfaces.api.views import ConsumeExternalJsonAPIView


class ThirdPartyExchangeRateAdapterTests(TestCase):
    def test_returns_rate_from_api(self):
        response = mock.MagicMock()
        response.json.return_value = {"rates": {"COP": 4123.0}}
        client = mock.MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = response

        with mock.patch("common.infrastructure.adapters.httpx.Client", return_value=client):
            rate = ThirdPartyExchangeRateAdapter().get_usd_to_cop_rate()

        self.assertEqual(rate, 4123.0)

    def test_falls_back_to_default_on_error(self):
        with mock.patch("common.infrastructure.adapters.httpx.Client", side_effect=RuntimeError("boom")):
            rate = ThirdPartyExchangeRateAdapter().get_usd_to_cop_rate()

        self.assertEqual(rate, 4000.0)


class HttpAllyServiceAdapterTests(TestCase):
    @mock.patch.dict("os.environ", {"ALLY_SERVICE_URL": ""})
    def test_returns_mocked_fallback_without_configured_url(self):
        data = HttpAllyServiceAdapter().validate_user_trust("a@example.com")
        self.assertTrue(data["mocked"])
        self.assertEqual(data["email"], "a@example.com")

    @mock.patch.dict("os.environ", {"ALLY_SERVICE_URL": "https://ally.example.com"})
    def test_returns_real_response_when_configured(self):
        response = mock.MagicMock()
        response.json.return_value = {"status": "verified", "score": 90}
        client = mock.MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = response

        with mock.patch("common.infrastructure.adapters.httpx.Client", return_value=client):
            data = HttpAllyServiceAdapter().validate_user_trust("b@example.com")

        self.assertEqual(data["status"], "verified")

    @mock.patch.dict("os.environ", {"ALLY_SERVICE_URL": "https://ally.example.com"})
    def test_returns_unknown_on_error_when_configured(self):
        with mock.patch("common.infrastructure.adapters.httpx.Client", side_effect=RuntimeError("timeout")):
            data = HttpAllyServiceAdapter().validate_user_trust("c@example.com")

        self.assertEqual(data["status"], "unknown")
        self.assertFalse(data["mocked"])


class ExternalServicesTestAPIViewTests(TestCase):
    def setUp(self):
        cache.clear()

    @mock.patch("common.interfaces.api.views.HttpAllyServiceAdapter.validate_user_trust")
    @mock.patch("common.interfaces.api.views.ThirdPartyExchangeRateAdapter.get_usd_to_cop_rate")
    def test_success(self, get_rate, validate_trust):
        get_rate.return_value = 4100.0
        validate_trust.return_value = {"status": "verified", "score": 85, "email": "test@example.com"}

        response = self.client.get("/api/external-services")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["adapters"]["exchange_rate_api"]["usd_to_cop"], 4100.0)
        self.assertEqual(data["adapters"]["ally_service"]["status"], "verified")


class TriggerAsyncTaskAPIViewTests(TestCase):
    def setUp(self):
        cache.clear()

    @mock.patch("common.interfaces.api.views.trigger_report_generation.delay")
    def test_valid_email_triggers_task(self, delay):
        delay.return_value = mock.MagicMock(id="task-123")

        response = self.client.post(
            "/api/trigger-task", {"email": "valido@example.com"}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["task_id"], "task-123")
        delay.assert_called_once_with(requester_email="valido@example.com")

    def test_invalid_email_returns_400(self):
        response = self.client.post(
            "/api/trigger-task", {"email": "no-es-un-email"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @mock.patch("common.interfaces.api.views.trigger_report_generation.delay")
    def test_missing_email_uses_default(self, delay):
        delay.return_value = mock.MagicMock(id="task-456")

        response = self.client.post("/api/trigger-task", {}, content_type="application/json")

        self.assertEqual(response.status_code, 202)
        delay.assert_called_once_with(requester_email="test@example.com")


class ConsumeExternalJsonValidateUrlTests(TestCase):
    def test_blank_url_raises(self):
        with self.assertRaises(ValueError):
            ConsumeExternalJsonAPIView._validate_url("  ")

    def test_non_http_scheme_raises(self):
        with self.assertRaises(ValueError):
            ConsumeExternalJsonAPIView._validate_url("ftp://example.com/file")

    def test_missing_netloc_raises(self):
        with self.assertRaises(ValueError):
            ConsumeExternalJsonAPIView._validate_url("http://")

    def test_netloc_without_hostname_raises(self):
        with self.assertRaises(ValueError):
            ConsumeExternalJsonAPIView._validate_url("http://:8080/path")

    def test_dns_failure_raises(self):
        with mock.patch("socket.getaddrinfo", side_effect=socket.gaierror("no dns")):
            with self.assertRaises(ValueError):
                ConsumeExternalJsonAPIView._validate_url("http://no-existe.example.com")

    def test_blocks_private_ip(self):
        with mock.patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("10.0.0.5", 80))]):
            with self.assertRaises(ValueError):
                ConsumeExternalJsonAPIView._validate_url("http://internal.example.com")

    def test_blocks_loopback_ip(self):
        with mock.patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 80))]):
            with self.assertRaises(ValueError):
                ConsumeExternalJsonAPIView._validate_url("http://localhost.example.com")

    def test_allows_public_ip(self):
        with mock.patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 80))]):
            result = ConsumeExternalJsonAPIView._validate_url("http://public.example.com/data")
        self.assertEqual(result, "http://public.example.com/data")


class ConsumeExternalJsonAPIViewTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_invalid_url_returns_400(self):
        response = self.client.post(
            "/api/aliados/consumir", {"url": "not-a-url"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @mock.patch("common.interfaces.api.views.ConsumeExternalJsonAPIView._validate_url")
    def test_success(self, validate_url):
        validate_url.return_value = "https://ally.example.com/data"
        response_obj = mock.MagicMock()
        response_obj.read.return_value = b'{"ok": true}'
        response_obj.status = 200
        response_obj.__enter__.return_value = response_obj

        with mock.patch("common.interfaces.api.views.url_request.urlopen", return_value=response_obj):
            response = self.client.post(
                "/api/aliados/consumir", {"url": "https://ally.example.com/data"}, content_type="application/json"
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["data"], {"ok": True})

    @mock.patch("common.interfaces.api.views.ConsumeExternalJsonAPIView._validate_url")
    def test_non_json_response_returns_400(self, validate_url):
        validate_url.return_value = "https://ally.example.com/data"
        response_obj = mock.MagicMock()
        response_obj.read.return_value = b"not json"
        response_obj.__enter__.return_value = response_obj

        with mock.patch("common.interfaces.api.views.url_request.urlopen", return_value=response_obj):
            response = self.client.post(
                "/api/aliados/consumir", {"url": "https://ally.example.com/data"}, content_type="application/json"
            )

        self.assertEqual(response.status_code, 400)

    @mock.patch("common.interfaces.api.views.ConsumeExternalJsonAPIView._validate_url")
    def test_http_error_returns_502(self, validate_url):
        from urllib import error as url_error

        validate_url.return_value = "https://ally.example.com/data"
        http_error = url_error.HTTPError("https://ally.example.com/data", 503, "unavailable", {}, None)

        with mock.patch("common.interfaces.api.views.url_request.urlopen", side_effect=http_error):
            response = self.client.post(
                "/api/aliados/consumir", {"url": "https://ally.example.com/data"}, content_type="application/json"
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["ally_status"], 503)

    @mock.patch("common.interfaces.api.views.ConsumeExternalJsonAPIView._validate_url")
    def test_connection_error_returns_504(self, validate_url):
        from urllib import error as url_error

        validate_url.return_value = "https://ally.example.com/data"

        with mock.patch(
            "common.interfaces.api.views.url_request.urlopen", side_effect=url_error.URLError("unreachable")
        ):
            response = self.client.post(
                "/api/aliados/consumir", {"url": "https://ally.example.com/data"}, content_type="application/json"
            )

        self.assertEqual(response.status_code, 504)

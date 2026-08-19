import socket
import unittest
from unittest import mock
from urllib import request as url_request

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache
from django.test import TestCase, override_settings
from pywebpush import WebPushException

from accounts.infrastructure.models import User

from .domain.ports import WebPushExpiredError
from .exceptions import ServiceUnavailableError
from .infrastructure.adapters import (
    HttpAllyServiceAdapter,
    HttpSupportServiceAdapter,
    PywebpushWebPushAdapter,
    ThirdPartyExchangeRateAdapter,
)
from .interfaces.api.views import ConsumeExternalJsonAPIView

try:
    from axe_playwright_python.sync_playwright import Axe
    from playwright.sync_api import sync_playwright
except ImportError:
    Axe = None
    sync_playwright = None


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


class HttpSupportServiceAdapterTests(TestCase):
    def test_create_rating_returns_data_on_success(self):
        response = mock.MagicMock()
        response.json.return_value = {"data": {"id": 1, "puntuacion": 5}}
        client = mock.MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = response

        with mock.patch("common.infrastructure.adapters.httpx.Client", return_value=client):
            data = HttpSupportServiceAdapter().create_rating(
                usuario_id=1, autor_id=2, puntuacion=5, comentario="Muy bueno"
            )

        self.assertEqual(data["id"], 1)

    def test_create_rating_raises_service_unavailable_on_failure(self):
        with mock.patch("common.infrastructure.adapters.httpx.Client", side_effect=RuntimeError("timeout")):
            with self.assertRaises(ServiceUnavailableError):
                HttpSupportServiceAdapter().create_rating(
                    usuario_id=1, autor_id=2, puntuacion=5, comentario="Muy bueno"
                )

    def test_list_ratings_returns_empty_list_on_failure_instead_of_raising(self):
        with mock.patch("common.infrastructure.adapters.httpx.Client", side_effect=RuntimeError("timeout")):
            data = HttpSupportServiceAdapter().list_ratings(usuario_id=1)

        self.assertEqual(data, [])

    def test_list_ratings_returns_data_on_success(self):
        response = mock.MagicMock()
        response.json.return_value = {"data": [{"puntuacion": 4}, {"puntuacion": 5}]}
        client = mock.MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = response

        with mock.patch("common.infrastructure.adapters.httpx.Client", return_value=client):
            data = HttpSupportServiceAdapter().list_ratings(usuario_id=1)

        self.assertEqual(len(data), 2)


class PywebpushWebPushAdapterTests(TestCase):
    def _subscription(self):
        return mock.Mock(endpoint="https://push.example/1", p256dh="p256dh-value", auth="auth-value")

    @override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY="")
    def test_noop_when_vapid_keys_not_configured(self):
        with mock.patch("common.infrastructure.adapters.webpush") as webpush_mock:
            PywebpushWebPushAdapter().enviar(subscription=self._subscription(), titulo="T", mensaje="M")
        webpush_mock.assert_not_called()

    @override_settings(VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv", VAPID_ADMIN_EMAIL="ops@cucu.local")
    def test_calls_webpush_with_subscription_info_when_configured(self):
        with mock.patch("common.infrastructure.adapters.webpush") as webpush_mock:
            PywebpushWebPushAdapter().enviar(subscription=self._subscription(), titulo="T", mensaje="M")

        webpush_mock.assert_called_once()
        kwargs = webpush_mock.call_args.kwargs
        self.assertEqual(kwargs["subscription_info"]["endpoint"], "https://push.example/1")
        self.assertEqual(kwargs["subscription_info"]["keys"]["p256dh"], "p256dh-value")
        self.assertEqual(kwargs["vapid_claims"]["sub"], "mailto:ops@cucu.local")

    @override_settings(VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv")
    def test_raises_expired_error_on_410(self):
        response = mock.Mock(status_code=410)
        with mock.patch(
            "common.infrastructure.adapters.webpush",
            side_effect=WebPushException("gone", response=response),
        ):
            with self.assertRaises(WebPushExpiredError):
                PywebpushWebPushAdapter().enviar(subscription=self._subscription(), titulo="T", mensaje="M")

    @override_settings(VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv")
    def test_swallows_non_expiry_webpush_errors(self):
        response = mock.Mock(status_code=500)
        with mock.patch(
            "common.infrastructure.adapters.webpush",
            side_effect=WebPushException("boom", response=response),
        ):
            PywebpushWebPushAdapter().enviar(subscription=self._subscription(), titulo="T", mensaje="M")


class HealthAPIViewTests(TestCase):
    def test_healthy_reports_ok_with_no_auth_required(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["checks"], {"database": "ok", "cache": "ok"})

    @mock.patch("common.interfaces.api.views.connection")
    def test_database_failure_returns_503(self, connection):
        connection.cursor.side_effect = Exception("db down")

        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["checks"]["database"], "error")


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
            url, resolved_ip = ConsumeExternalJsonAPIView._validate_url("http://public.example.com/data")
        self.assertEqual(url, "http://public.example.com/data")
        self.assertEqual(resolved_ip, "93.184.216.34")


class ConsumeExternalJsonAPIViewTests(TestCase):
    def setUp(self):
        cache.clear()

    def _mock_opener(self, *, response=None, side_effect=None):
        opener = mock.MagicMock()
        if side_effect is not None:
            opener.open.side_effect = side_effect
        else:
            opener.open.return_value = response
        return opener

    def test_invalid_url_returns_400(self):
        response = self.client.post(
            "/api/aliados/consumir", {"url": "not-a-url"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @mock.patch("common.interfaces.api.views.build_pinned_opener")
    @mock.patch("common.interfaces.api.views.ConsumeExternalJsonAPIView._validate_url")
    def test_success(self, validate_url, build_pinned_opener):
        validate_url.return_value = ("https://ally.example.com/data", "93.184.216.34")
        response_obj = mock.MagicMock()
        response_obj.read.return_value = b'{"ok": true}'
        response_obj.status = 200
        response_obj.__enter__.return_value = response_obj
        build_pinned_opener.return_value = self._mock_opener(response=response_obj)

        response = self.client.post(
            "/api/aliados/consumir", {"url": "https://ally.example.com/data"}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["data"], {"ok": True})
        build_pinned_opener.assert_called_once_with("93.184.216.34")

    @mock.patch("common.interfaces.api.views.build_pinned_opener")
    @mock.patch("common.interfaces.api.views.ConsumeExternalJsonAPIView._validate_url")
    def test_non_json_response_returns_400(self, validate_url, build_pinned_opener):
        validate_url.return_value = ("https://ally.example.com/data", "93.184.216.34")
        response_obj = mock.MagicMock()
        response_obj.read.return_value = b"not json"
        response_obj.__enter__.return_value = response_obj
        build_pinned_opener.return_value = self._mock_opener(response=response_obj)

        response = self.client.post(
            "/api/aliados/consumir", {"url": "https://ally.example.com/data"}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    @mock.patch("common.interfaces.api.views.build_pinned_opener")
    @mock.patch("common.interfaces.api.views.ConsumeExternalJsonAPIView._validate_url")
    def test_http_error_returns_502(self, validate_url, build_pinned_opener):
        from urllib import error as url_error

        validate_url.return_value = ("https://ally.example.com/data", "93.184.216.34")
        http_error = url_error.HTTPError("https://ally.example.com/data", 503, "unavailable", {}, None)
        build_pinned_opener.return_value = self._mock_opener(side_effect=http_error)

        response = self.client.post(
            "/api/aliados/consumir", {"url": "https://ally.example.com/data"}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["ally_status"], 503)

    @mock.patch("common.interfaces.api.views.build_pinned_opener")
    @mock.patch("common.interfaces.api.views.ConsumeExternalJsonAPIView._validate_url")
    def test_connection_error_returns_504(self, validate_url, build_pinned_opener):
        from urllib import error as url_error

        validate_url.return_value = ("https://ally.example.com/data", "93.184.216.34")
        build_pinned_opener.return_value = self._mock_opener(side_effect=url_error.URLError("unreachable"))

        response = self.client.post(
            "/api/aliados/consumir", {"url": "https://ally.example.com/data"}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 504)


class SafeHttpTests(TestCase):
    def test_resolve_and_validate_host_returns_first_public_ip(self):
        from common.infrastructure.safe_http import resolve_and_validate_host

        with mock.patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 80))]):
            ip = resolve_and_validate_host("example.com")
        self.assertEqual(ip, "93.184.216.34")

    def test_resolve_and_validate_host_rejects_private_ip(self):
        from common.infrastructure.safe_http import UnsafeHostError, resolve_and_validate_host

        with mock.patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("10.0.0.5", 80))]):
            with self.assertRaises(UnsafeHostError):
                resolve_and_validate_host("internal.example.com")

    def test_resolve_and_validate_host_rejects_when_dns_fails(self):
        from common.infrastructure.safe_http import UnsafeHostError, resolve_and_validate_host

        with mock.patch("socket.getaddrinfo", side_effect=socket.gaierror("no dns")):
            with self.assertRaises(UnsafeHostError):
                resolve_and_validate_host("no-existe.example.com")

    def test_resolve_and_validate_host_rejects_empty_result(self):
        from common.infrastructure.safe_http import UnsafeHostError, resolve_and_validate_host

        with mock.patch("socket.getaddrinfo", return_value=[]):
            with self.assertRaises(UnsafeHostError):
                resolve_and_validate_host("example.com")

    def test_resolve_and_validate_host_keeps_first_ip_when_multiple_families_resolve(self):
        from common.infrastructure.safe_http import resolve_and_validate_host

        addr_infos = [
            (2, 1, 6, "", ("93.184.216.34", 80)),
            (10, 1, 6, "", ("2606:2800:220:1:248:1893:25c8:1946", 80, 0, 0)),
        ]
        with mock.patch("socket.getaddrinfo", return_value=addr_infos):
            ip = resolve_and_validate_host("example.com")
        self.assertEqual(ip, "93.184.216.34")

    def test_pinned_http_connection_connects_to_pinned_ip_not_hostname(self):
        """El punto central del fix: la conexion real debe ir a la IP ya
        validada, sin volver a resolver el hostname (que es exactamente lo
        que permite el bypass de DNS rebinding)."""
        from common.infrastructure.safe_http import _PinnedHTTPConnection

        fake_sock = mock.MagicMock()
        with mock.patch("socket.create_connection", return_value=fake_sock) as create_connection, \
                mock.patch("socket.getaddrinfo", side_effect=AssertionError("no deberia resolver DNS de nuevo")):
            conn = _PinnedHTTPConnection("ally.example.com", pinned_ip="93.184.216.34")
            conn.connect()

        create_connection.assert_called_once()
        called_address = create_connection.call_args[0][0]
        self.assertEqual(called_address[0], "93.184.216.34")
        self.assertEqual(conn.sock, fake_sock)

    def test_http_handler_dispatches_to_pinned_connection_factory(self):
        from common.infrastructure.safe_http import _PinnedHTTPConnection, _PinnedHTTPHandler

        handler = _PinnedHTTPHandler("93.184.216.34")
        request_obj = url_request.Request("http://ally.example.com/data")
        with mock.patch.object(handler, "do_open") as do_open:
            handler.http_open(request_obj)

        do_open.assert_called_once()
        connection_factory = do_open.call_args[0][0]
        conn = connection_factory("ally.example.com", timeout=5)
        self.assertIsInstance(conn, _PinnedHTTPConnection)
        self.assertEqual(conn._pinned_ip, "93.184.216.34")

    def test_https_handler_dispatches_to_pinned_connection_factory(self):
        from common.infrastructure.safe_http import _PinnedHTTPSConnection, _PinnedHTTPSHandler

        handler = _PinnedHTTPSHandler("93.184.216.34")
        request_obj = url_request.Request("https://ally.example.com/data")
        with mock.patch.object(handler, "do_open") as do_open:
            handler.https_open(request_obj)

        do_open.assert_called_once()
        connection_factory = do_open.call_args[0][0]
        conn = connection_factory("ally.example.com", timeout=5)
        self.assertIsInstance(conn, _PinnedHTTPSConnection)
        self.assertEqual(conn._pinned_ip, "93.184.216.34")

    def test_build_pinned_opener_registers_handlers_for_the_pinned_ip(self):
        from common.infrastructure.safe_http import (
            _PinnedHTTPHandler,
            _PinnedHTTPSHandler,
            build_pinned_opener,
        )

        opener = build_pinned_opener("93.184.216.34")
        handler_types = {type(h) for h in opener.handlers}
        self.assertIn(_PinnedHTTPHandler, handler_types)
        self.assertIn(_PinnedHTTPSHandler, handler_types)

    def test_pinned_https_connection_uses_hostname_for_sni(self):
        from common.infrastructure.safe_http import _PinnedHTTPSConnection

        fake_sock = mock.MagicMock()
        wrapped_sock = mock.MagicMock()
        fake_context = mock.MagicMock()
        fake_context.wrap_socket.return_value = wrapped_sock

        conn = _PinnedHTTPSConnection("ally.example.com", pinned_ip="93.184.216.34")
        conn._context = fake_context

        with mock.patch("socket.create_connection", return_value=fake_sock) as create_connection:
            conn.connect()

        called_address = create_connection.call_args[0][0]
        self.assertEqual(called_address[0], "93.184.216.34")
        fake_context.wrap_socket.assert_called_once_with(fake_sock, server_hostname="ally.example.com")
        self.assertEqual(conn.sock, wrapped_sock)


class AdminLoginRateLimitMiddlewareTests(TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _attempt(self, remote_addr="127.0.0.1"):
        return self.client.post(
            "/admin/login/",
            {"username": "admin", "password": "wrong"},
            REMOTE_ADDR=remote_addr,
        )

    def test_11th_admin_login_attempt_within_a_minute_is_throttled(self):
        for _ in range(10):
            response = self._attempt()
            self.assertNotEqual(response.status_code, 429)

        response = self._attempt()
        self.assertEqual(response.status_code, 429)

    def test_get_requests_are_not_rate_limited(self):
        for _ in range(15):
            response = self.client.get("/admin/login/", REMOTE_ADDR="127.0.0.1")
            self.assertNotEqual(response.status_code, 429)

    def test_other_admin_paths_are_not_rate_limited(self):
        for _ in range(15):
            response = self.client.post("/admin/", REMOTE_ADDR="127.0.0.1")
            self.assertNotEqual(response.status_code, 429)

    def test_rate_limit_is_scoped_per_ip(self):
        for _ in range(10):
            self._attempt(remote_addr="203.0.113.1")

        response = self._attempt(remote_addr="203.0.113.2")
        self.assertNotEqual(response.status_code, 429)


@unittest.skipUnless(sync_playwright, "playwright/axe-playwright-python not installed - run: python -m playwright install chromium")
class AccessibilityAxeTests(StaticLiveServerTestCase):
    """Escaneo automatizado de accesibilidad (axe-core via Playwright) sobre
    las pantallas reales de la app. Corre contra un servidor Django real, no
    HTML estatico - captura lo que un lector de pantalla real vería."""

    PUBLIC_PAGES = [
        "/",
        "/ui/login/",
        "/ui/registro/",
        "/ui/terminos/",
        "/ui/privacidad/",
        "/ui/soporte/",
        "/ui/publicar/",
    ]

    AUTHENTICATED_PAGES = [
        "/ui/perfil/",
        "/ui/seguimiento/",
    ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()
        cls.axe = Axe()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()

    def _assert_axe_clean(self, page, label):
        results = self.axe.run(page)
        violations = results.response["violations"]
        if violations:
            details = "\n".join(f"- {v['id']} ({v['impact']}): {v['help']}" for v in violations)
            self.fail(f"Violaciones de accesibilidad en {label}:\n{details}")

    def test_public_pages_have_no_axe_violations(self):
        for path in self.PUBLIC_PAGES:
            with self.subTest(path=path):
                page = self.browser.new_page()
                try:
                    page.goto(f"{self.live_server_url}{path}")
                    self._assert_axe_clean(page, path)
                finally:
                    page.close()

    def test_authenticated_pages_have_no_axe_violations(self):
        user = User(username="axe@example.com", email="axe@example.com", nombre="Axe Test")
        user.set_password("secret12345")
        user.save()

        page = self.browser.new_page()
        try:
            page.goto(f"{self.live_server_url}/ui/login/")
            page.fill('input[name="email"]', "axe@example.com")
            page.fill('input[name="password"]', "secret12345")
            page.click('button[type="submit"]')
            page.wait_for_timeout(1500)

            for path in self.AUTHENTICATED_PAGES:
                with self.subTest(path=path):
                    page.goto(f"{self.live_server_url}{path}")
                    page.wait_for_timeout(500)
                    self._assert_axe_clean(page, path)
        finally:
            page.close()

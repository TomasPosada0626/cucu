from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.infrastructure.models import User
from common.exceptions import ConflictError, NotFoundError, ValidationError

from .domain.services import NotificacionService
from .infrastructure.factories import NotificacionFactory
from .infrastructure.models import Notificacion
from .tasks import enqueue_payment_notification, trigger_report_generation


class NotificacionFactoryTests(TestCase):
    def setUp(self):
        self.user = User(username="factory@example.com", email="factory@example.com", nombre="Factory")
        self.user.set_password("secret12345")
        self.user.save()

    def test_crear_success(self):
        notificacion = NotificacionFactory.crear(usuario=self.user, tipo="pedido", mensaje="Hola")
        self.assertEqual(notificacion.tipo, "pedido")
        self.assertEqual(notificacion.mensaje, "Hola")
        self.assertFalse(notificacion.leida)

    def test_crear_invalid_tipo_raises(self):
        with self.assertRaises(ValidationError):
            NotificacionFactory.crear(usuario=self.user, tipo="no-existe", mensaje="Hola")


class NotificacionModelTests(TestCase):
    def test_str_includes_id_and_tipo(self):
        user = User(username="modelstr@example.com", email="modelstr@example.com", nombre="ModelStr")
        user.set_password("secret12345")
        user.save()
        notificacion = Notificacion.objects.create(usuario=user, tipo="pedido", mensaje="Hola")
        self.assertIn(str(notificacion.id), str(notificacion))
        self.assertIn("pedido", str(notificacion))


class NotificacionServiceTests(TestCase):
    def setUp(self):
        self.service = NotificacionService()
        self.user = User(username="service_user@example.com", email="service_user@example.com", nombre="ServiceUser")
        self.user.set_password("secret12345")
        self.user.save()
        self.other_user = User(username="other_service@example.com", email="other_service@example.com", nombre="Other")
        self.other_user.set_password("secret12345")
        self.other_user.save()

    def test_enviar_creates_notification(self):
        notificacion = self.service.enviar(self.user, "pedido", "Tu pedido va en camino")
        self.assertTrue(Notificacion.objects.filter(id=notificacion.id).exists())

    def test_marcar_leida_success(self):
        notificacion = Notificacion.objects.create(usuario=self.user, tipo="pedido", mensaje="X")
        updated = self.service.marcar_leida(notificacion.id)
        self.assertTrue(updated.leida)
        notificacion.refresh_from_db()
        self.assertTrue(notificacion.leida)

    def test_marcar_leida_not_found_raises(self):
        with self.assertRaises(NotFoundError):
            self.service.marcar_leida(999999)

    def test_marcar_leida_already_read_raises_conflict(self):
        notificacion = Notificacion.objects.create(usuario=self.user, tipo="pedido", mensaje="X", leida=True)
        with self.assertRaises(ConflictError):
            self.service.marcar_leida(notificacion.id)

    def test_obtener_usuario_returns_only_own_notifications(self):
        Notificacion.objects.create(usuario=self.user, tipo="pedido", mensaje="mia")
        Notificacion.objects.create(usuario=self.other_user, tipo="pedido", mensaje="ajena")

        resultado = self.service.obtener_usuario(self.user)

        self.assertEqual(resultado.count(), 1)
        self.assertEqual(resultado.first().mensaje, "mia")


class NotificationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User(username="api_notif@example.com", email="api_notif@example.com", nombre="ApiNotif")
        self.user.set_password("secret12345")
        self.user.save()
        access = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_mis_notificaciones_requires_auth(self):
        anon = APIClient()
        response = anon.get("/api/notificaciones/")
        self.assertEqual(response.status_code, 401)

    def test_mis_notificaciones_returns_only_own(self):
        other_user = User(username="other_api@example.com", email="other_api@example.com", nombre="OtherApi")
        other_user.set_password("secret12345")
        other_user.save()
        Notificacion.objects.create(usuario=self.user, tipo="pedido", mensaje="mia")
        Notificacion.objects.create(usuario=other_user, tipo="pedido", mensaje="ajena")

        response = self.client.get("/api/notificaciones/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["mensaje"], "mia")

    def test_marcar_leida_success(self):
        notificacion = Notificacion.objects.create(usuario=self.user, tipo="pedido", mensaje="X")

        response = self.client.post(f"/api/notificaciones/{notificacion.id}/leer/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["leida"])

    def test_marcar_leida_not_found_returns_404(self):
        response = self.client.post("/api/notificaciones/999999/leer/")
        self.assertEqual(response.status_code, 404)

    def test_marcar_leida_already_leida_returns_409(self):
        notificacion = Notificacion.objects.create(usuario=self.user, tipo="pedido", mensaje="X", leida=True)

        response = self.client.post(f"/api/notificaciones/{notificacion.id}/leer/")

        self.assertEqual(response.status_code, 409)


class NotificationTasksTests(TestCase):
    def setUp(self):
        self.user = User(username="task_user@example.com", email="task_user@example.com", nombre="TaskUser")
        self.user.set_password("secret12345")
        self.user.save()

    def test_enqueue_payment_notification_autorizado(self):
        result = enqueue_payment_notification(
            usuario_id=self.user.id, pago_id=1, pedido_id=2, estado="autorizado"
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["estado"], "AUTORIZADO")
        notificacion = Notificacion.objects.get(usuario=self.user)
        self.assertEqual(notificacion.tipo, "pago")
        self.assertIn("autorizado", notificacion.mensaje.lower())

    def test_enqueue_payment_notification_fallido(self):
        enqueue_payment_notification(usuario_id=self.user.id, pago_id=1, pedido_id=2, estado="fallido")
        notificacion = Notificacion.objects.get(usuario=self.user)
        self.assertIn("fallo", notificacion.mensaje.lower())

    def test_enqueue_payment_notification_otro_estado(self):
        enqueue_payment_notification(usuario_id=self.user.id, pago_id=1, pedido_id=2, estado="pendiente")
        notificacion = Notificacion.objects.get(usuario=self.user)
        self.assertIn("pendiente", notificacion.mensaje.lower())

    @mock.patch("time.sleep")
    def test_trigger_report_generation(self, sleep):
        result = trigger_report_generation(requester_email="a@example.com")
        sleep.assert_called_once_with(2)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["requested_by"], "a@example.com")

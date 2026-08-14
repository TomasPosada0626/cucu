from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.infrastructure.models import User
from common.exceptions import NotFoundError, ValidationError
from market.infrastructure.models import Pedido, Publicacion

from .domain.services import PaymentService
from .infrastructure.gateways import CardGateway, CashGateway, PaymentGatewayFactory, PseGateway
from .infrastructure.models import Pago


class PagoCreateTests(TestCase):
	def setUp(self):
		self.client = APIClient()

		self.seller = User(username="seller_pay@example.com", email="seller_pay@example.com", nombre="Seller")
		self.seller.set_password("secret12345")
		self.seller.save()

		self.buyer = User(username="buyer_pay@example.com", email="buyer_pay@example.com", nombre="Buyer")
		self.buyer.set_password("secret12345")
		self.buyer.save()

		self.other = User(username="other_pay@example.com", email="other_pay@example.com", nombre="Other")
		self.other.set_password("secret12345")
		self.other.save()

		self.publicacion = Publicacion.objects.create(
			titulo="Producto",
			descripcion="Desc",
			precio=20.0,
			usuario=self.seller,
		)

		self.pedido = Pedido.objects.create(
			telefono="123",
			total=20.0,
			publicacion=self.publicacion,
			usuario=self.buyer,
		)

		access = str(RefreshToken.for_user(self.buyer).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_create_pago_authorized_and_associated(self):
		response = self.client.post(
			"/api/pago",
			{
				"pedido_id": self.pedido.id,
				"metodo": "cash",
				"monto": 20.0,
			},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		data = response.json()
		self.assertEqual(data["pedido_id"], self.pedido.id)
		self.assertEqual(data["metodo"], "cash")
		self.assertEqual(float(data["monto"]), 20.0)
		self.assertEqual(data["estado"], "AUTORIZADO")

		pago = Pago.objects.get(id=data["id"])
		self.assertEqual(pago.pedido_id, self.pedido.id)

	def test_cannot_pay_order_not_owned(self):
		other_pedido = Pedido.objects.create(
			telefono="999",
			total=20.0,
			publicacion=self.publicacion,
			usuario=self.other,
		)

		response = self.client.post(
			"/api/pago",
			{"pedido_id": other_pedido.id, "metodo": "cash", "monto": 20.0},
			format="json",
		)
		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.json().get("detail"), "No puedes pagar un pedido que no es tuyo")

	def test_pago_for_nonexistent_pedido_returns_404(self):
		response = self.client.post(
			"/api/pago", {"pedido_id": 999999, "metodo": "cash", "monto": 20.0}, format="json"
		)
		self.assertEqual(response.status_code, 404)

	def test_card_within_limit_sets_estado_autorizado(self):
		response = self.client.post(
			"/api/pago",
			{"pedido_id": self.pedido.id, "metodo": "card", "monto": 20.0},
			format="json",
		)
		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()["estado"], "AUTORIZADO")


class PagoModelTests(TestCase):
	def test_str_includes_id_and_estado(self):
		seller = User(username="model_pay_seller@example.com", email="model_pay_seller@example.com", nombre="Seller")
		seller.set_password("secret12345")
		seller.save()
		buyer = User(username="model_pay_buyer@example.com", email="model_pay_buyer@example.com", nombre="Buyer")
		buyer.set_password("secret12345")
		buyer.save()
		publicacion = Publicacion.objects.create(titulo="X", descripcion="Y", precio=10, usuario=seller)
		pedido = Pedido.objects.create(telefono="1", total=10, publicacion=publicacion, usuario=buyer)
		pago = Pago.objects.create(pedido=pedido, metodo="cash", monto=10, estado="AUTORIZADO")
		self.assertIn(str(pago.id), str(pago))
		self.assertIn("AUTORIZADO", str(pago))


class PaymentGatewayTests(TestCase):
	def test_cash_gateway_authorizes_positive_amount(self):
		self.assertTrue(CashGateway().authorize(amount=100))
		self.assertFalse(CashGateway().authorize(amount=0))

	def test_pse_gateway_authorizes_positive_amount(self):
		self.assertTrue(PseGateway().authorize(amount=100))
		self.assertFalse(PseGateway().authorize(amount=0))

	def test_card_gateway_rejects_over_limit(self):
		self.assertTrue(CardGateway().authorize(amount=1_000_000))
		self.assertFalse(CardGateway().authorize(amount=1_000_001))
		self.assertFalse(CardGateway().authorize(amount=0))

	def test_factory_maps_known_methods(self):
		self.assertIsInstance(PaymentGatewayFactory.get_gateway(method="cash"), CashGateway)
		self.assertIsInstance(PaymentGatewayFactory.get_gateway(method="efectivo"), CashGateway)
		self.assertIsInstance(PaymentGatewayFactory.get_gateway(method="card"), CardGateway)
		self.assertIsInstance(PaymentGatewayFactory.get_gateway(method="tarjeta"), CardGateway)
		self.assertIsInstance(PaymentGatewayFactory.get_gateway(method="pse"), PseGateway)

	def test_factory_rejects_unknown_method(self):
		with self.assertRaises(ValidationError):
			PaymentGatewayFactory.get_gateway(method="bitcoin")


class PaymentServiceDirectTests(TestCase):
	def setUp(self):
		self.pedido_repo = MagicMock()
		self.pago_repo = MagicMock()
		self.ensure_transaccion = MagicMock()
		self.service = PaymentService(
			pedido_lookup_repository=self.pedido_repo,
			pago_repository=self.pago_repo,
			ensure_transaccion_func=self.ensure_transaccion,
		)
		self.user = MagicMock(id=1)

	def test_pedido_not_found_raises(self):
		self.pedido_repo.get_by_id.return_value = None
		with self.assertRaises(NotFoundError):
			self.service.register_payment(user=self.user, pedido_id=999, metodo="cash")

	def test_zero_total_raises(self):
		pedido = MagicMock(usuario_id=1, total=0)
		self.pedido_repo.get_by_id.return_value = pedido
		with self.assertRaises(ValidationError):
			self.service.register_payment(user=self.user, pedido_id=1, metodo="cash")

	def test_monto_mismatch_raises(self):
		pedido = MagicMock(usuario_id=1, total=100.0)
		self.pedido_repo.get_by_id.return_value = pedido
		with self.assertRaises(ValidationError):
			self.service.register_payment(user=self.user, pedido_id=1, metodo="cash", monto=50.0)

	def test_declined_payment_does_not_ensure_transaccion(self):
		pedido = MagicMock(usuario_id=1, total=2_000_000.0)
		self.pedido_repo.get_by_id.return_value = pedido
		self.pago_repo.create.return_value = MagicMock(id=1, estado="FALLIDO")

		with patch("notifications.tasks.enqueue_payment_notification.delay"):
			self.service.register_payment(user=self.user, pedido_id=1, metodo="card")

		self.pago_repo.create.assert_called_once()
		self.assertEqual(self.pago_repo.create.call_args.kwargs["estado"], "FALLIDO")
		self.ensure_transaccion.assert_not_called()

	def test_notification_enqueue_failure_is_swallowed(self):
		pedido = MagicMock(usuario_id=1, total=100.0)
		self.pedido_repo.get_by_id.return_value = pedido
		self.pago_repo.create.return_value = MagicMock(id=1, estado="AUTORIZADO")

		with patch("notifications.tasks.enqueue_payment_notification.delay", side_effect=RuntimeError("rabbitmq down")):
			pago = self.service.register_payment(user=self.user, pedido_id=1, metodo="cash")

		self.assertEqual(pago.estado, "AUTORIZADO")
		self.ensure_transaccion.assert_called_once_with(pedido)

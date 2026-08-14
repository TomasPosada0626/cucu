from django.test import TestCase

from accounts.infrastructure.models import User
from common.exceptions import ConflictError
from market.infrastructure.models import Pedido, Publicacion

from .domain.builders import TransaccionBuilder, ensure_transaccion_for_pedido
from .infrastructure.models import Transaccion


class TransactionsTestBase(TestCase):
    def setUp(self):
        self.seller = User(username="trx_seller@example.com", email="trx_seller@example.com", nombre="Seller")
        self.seller.set_password("secret12345")
        self.seller.save()

        self.buyer = User(username="trx_buyer@example.com", email="trx_buyer@example.com", nombre="Buyer")
        self.buyer.set_password("secret12345")
        self.buyer.save()

        self.publicacion = Publicacion.objects.create(
            titulo="Sopa", descripcion="Caliente", precio=10000, usuario=self.seller,
        )

    def create_pedido(self):
        return Pedido.objects.create(
            telefono="123456", total=10000, publicacion=self.publicacion, usuario=self.buyer,
        )


class TransaccionBuilderTests(TransactionsTestBase):
    def test_build_requires_pedido(self):
        with self.assertRaises(ValueError):
            TransaccionBuilder().build()

    def test_build_creates_transaccion_with_defaults(self):
        pedido = self.create_pedido()

        transaccion = TransaccionBuilder().for_pedido(pedido).build()

        self.assertEqual(transaccion.pedido_id, pedido.id)
        self.assertEqual(transaccion.estado, "ABIERTA")
        self.assertEqual(transaccion.distancia_validacion_metros, 0.0)

    def test_build_with_custom_estado_and_distancia(self):
        pedido = self.create_pedido()

        transaccion = (
            TransaccionBuilder()
            .for_pedido(pedido)
            .with_estado("CERRADA")
            .with_distancia_validacion_metros(45.5)
            .build()
        )

        self.assertEqual(transaccion.estado, "CERRADA")
        self.assertEqual(transaccion.distancia_validacion_metros, 45.5)

    def test_build_raises_conflict_if_already_exists(self):
        pedido = self.create_pedido()
        TransaccionBuilder().for_pedido(pedido).build()
        pedido.refresh_from_db()

        with self.assertRaises(ConflictError):
            TransaccionBuilder().for_pedido(pedido).build()


class EnsureTransaccionForPedidoTests(TransactionsTestBase):
    def test_creates_new_when_none_exists(self):
        pedido = self.create_pedido()

        transaccion = ensure_transaccion_for_pedido(pedido)

        self.assertIsInstance(transaccion, Transaccion)
        self.assertEqual(Transaccion.objects.filter(pedido=pedido).count(), 1)

    def test_returns_existing_when_already_present(self):
        pedido = self.create_pedido()
        primera = ensure_transaccion_for_pedido(pedido)
        pedido.refresh_from_db()

        segunda = ensure_transaccion_for_pedido(pedido)

        self.assertEqual(primera.id, segunda.id)
        self.assertEqual(Transaccion.objects.filter(pedido=pedido).count(), 1)


class TransaccionModelTests(TransactionsTestBase):
    def test_str_includes_id_and_estado(self):
        pedido = self.create_pedido()
        transaccion = Transaccion.objects.create(pedido=pedido, estado="ABIERTA")
        self.assertIn(str(transaccion.id), str(transaccion))
        self.assertIn("ABIERTA", str(transaccion))

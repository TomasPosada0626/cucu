import io

from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
from decimal import Decimal
from PIL import Image

from accounts.infrastructure.models import User
from common.exceptions import ValidationError
from geo.infrastructure.models import Ubicacion

from .domain.builders import PedidoBuilder
from .domain.image_validation import validate_publicacion_imagen
from .domain.order_rules import PublicacionSnapshot, validate_and_price_items
from .infrastructure.models import Pedido, PedidoItem, Publicacion


def _valid_png_bytes() -> bytes:
	buffer = io.BytesIO()
	Image.new("RGB", (2, 2), color="red").save(buffer, format="PNG")
	return buffer.getvalue()


class PedidoCreateTests(TestCase):
	def setUp(self):
		self.client = APIClient()

		self.seller = User(username="seller@example.com", email="seller@example.com", nombre="Seller")
		self.seller.set_password("secret12345")
		self.seller.save()

		self.buyer = User(username="buyer@example.com", email="buyer@example.com", nombre="Buyer")
		self.buyer.set_password("secret12345")
		self.buyer.save()

		self.publicacion = Publicacion.objects.create(
			titulo="Comida",
			descripcion="Rica",
			maximo_por_venta=5,
			precio=12.5,
			usuario=self.seller,
		)

		access = str(RefreshToken.for_user(self.buyer).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_create_pedido_associated_and_default_fields(self):
		response = self.client.post(
			"/api/pedidos",
			{
				"publicacion_id": self.publicacion.id,
				"telefono": "123456",
				"direccion_entrega": "Calle 10 # 20-30, Bogota",
				"direccion_entrega_detalles": "Apto 101",
				"direccion_entrega_latitud": "4.653332",
				"direccion_entrega_longitud": "-74.083652",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		data = response.json()
		self.assertEqual(data["publicacion_id"], self.publicacion.id)
		self.assertEqual(data["usuario_id"], self.buyer.id)
		self.assertEqual(data["estado"], "PENDIENTE")
		self.assertEqual(data["direccion_entrega"], "Calle 10 # 20-30, Bogota")
		self.assertEqual(data["direccion_entrega_detalles"], "Apto 101")
		self.assertIsNotNone(data.get("fecha_creacion"))

		pedido = Pedido.objects.get(id=data["id"])
		self.assertEqual(pedido.usuario_id, self.buyer.id)
		self.assertEqual(pedido.publicacion_id, self.publicacion.id)
		self.assertEqual(pedido.direccion_entrega, "Calle 10 # 20-30, Bogota")
		self.assertEqual(pedido.direccion_entrega_detalles, "Apto 101")
		self.assertEqual(pedido.direccion_entrega_latitud, Decimal("4.653332"))
		self.assertEqual(pedido.direccion_entrega_longitud, Decimal("-74.083652"))
		self.publicacion.refresh_from_db()
		self.assertEqual(self.publicacion.stock, 9)
		self.assertEqual(data["items"][0]["publicacion"]["maximo_por_venta"], 5)

	def test_create_pedido_rejects_second_active_order_for_same_user(self):
		Pedido.objects.create(
			telefono="123456",
			total=12.5,
			publicacion=self.publicacion,
			usuario=self.buyer,
			estado="PENDIENTE",
		)

		response = self.client.post(
			"/api/pedidos",
			{
				"publicacion_id": self.publicacion.id,
				"telefono": "123456",
				"direccion_entrega": "Calle 10 # 20-30, Bogota",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertIn("pedido activo", response.json()["detail"].lower())
		self.assertEqual(Pedido.objects.filter(usuario=self.buyer).count(), 1)

	def test_create_pedido_rejects_when_stock_is_insufficient(self):
		self.publicacion.stock = 1
		self.publicacion.save(update_fields=["stock"])

		response = self.client.post(
			"/api/pedidos",
			{
				"publicacion_ids": [self.publicacion.id, self.publicacion.id],
				"telefono": "123456",
				"direccion_entrega": "Calle 10 # 20-30, Bogota",
				"direccion_entrega_latitud": "4.653332",
				"direccion_entrega_longitud": "-74.083652",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertIn("stock insuficiente", response.json()["detail"].lower())
		self.publicacion.refresh_from_db()
		self.assertEqual(self.publicacion.stock, 1)

	def test_create_pedido_rejects_when_exceeds_maximo_por_venta(self):
		self.publicacion.maximo_por_venta = 2
		self.publicacion.stock = 10
		self.publicacion.save(update_fields=["maximo_por_venta", "stock"])

		response = self.client.post(
			"/api/pedidos",
			{
				"publicacion_ids": [self.publicacion.id, self.publicacion.id, self.publicacion.id],
				"telefono": "123456",
				"direccion_entrega": "Calle 10 # 20-30, Bogota",
				"direccion_entrega_latitud": "4.653332",
				"direccion_entrega_longitud": "-74.083652",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertIn("hasta 2", response.json()["detail"].lower())

	def test_list_my_orders_returns_only_current_user_orders(self):
		own_pedido = Pedido.objects.create(
			telefono="123456",
			total=12.5,
			publicacion=self.publicacion,
			usuario=self.buyer,
		)
		other_user = User(username="other@example.com", email="other@example.com", nombre="Other")
		other_user.set_password("secret12345")
		other_user.save()
		Pedido.objects.create(
			telefono="999999",
			total=12.5,
			publicacion=self.publicacion,
			usuario=other_user,
		)

		response = self.client.get("/api/mis-pedidos")

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(len(data), 1)
		self.assertEqual(data[0]["id"], own_pedido.id)

	def test_mark_my_order_as_delivered(self):
		pedido = Pedido.objects.create(
			telefono="123456",
			total=12.5,
			publicacion=self.publicacion,
			usuario=self.buyer,
			estado="ACEPTADO",
		)

		response = self.client.patch(f"/api/pedidos/{pedido.id}/entregar")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["estado"], "ENTREGADO")
		pedido.refresh_from_db()
		self.assertEqual(pedido.estado, "ENTREGADO")


class PublicacionGeoTests(TestCase):
	def setUp(self):
		self.client = APIClient()

		self.seller = User(username="cook@example.com", email="cook@example.com", nombre="Cook")
		self.seller.set_password("secret12345")
		self.seller.save()

		access = str(RefreshToken.for_user(self.seller).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_create_publicacion_with_address_only(self, geocode_address):
		geocode_address.return_value.latitud = "4.653332"
		geocode_address.return_value.longitud = "-74.083652"
		geocode_address.return_value.direccion_texto = "Calle 10 # 20-30, Bogota"

		response = self.client.post(
			"/api/publicaciones",
			{
				"titulo": "Bandeja paisa",
				"descripcion": "Plato casero del día",
				"categoria": "otra",
				"precio": 22000,
				"maximo_por_venta": 3,
				"direccion_texto": "Calle 10 # 20-30",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 201)
		data = response.json()
		self.assertEqual(data["titulo"], "Bandeja paisa")
		self.assertEqual(data["categoria"], "otra")
		self.assertEqual(data["maximo_por_venta"], 3)
		self.assertEqual(data["ubicacion"]["direccion_texto"], "Calle 10 # 20-30, Bogota")

		publicacion = Publicacion.objects.get(id=data["id"])
		self.assertIsNotNone(publicacion.ubicacion_id)
		self.assertEqual(publicacion.ubicacion.direccion_texto, "Calle 10 # 20-30, Bogota")
		self.assertEqual(publicacion.maximo_por_venta, 3)

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_create_publicacion_with_image(self, geocode_address):
		geocode_address.return_value.latitud = "4.653332"
		geocode_address.return_value.longitud = "-74.083652"
		geocode_address.return_value.direccion_texto = "Calle 10 # 20-30, Bogota"

		image = SimpleUploadedFile("ramen.png", _valid_png_bytes(), content_type="image/png")

		response = self.client.post(
			"/api/publicaciones",
			{
				"titulo": "Ramen de prueba",
				"descripcion": "Caldo y fideos",
				"categoria": "otra",
				"precio": 28000,
				"direccion_texto": "Calle 10 # 20-30",
				"imagen": image,
			},
		)

		self.assertEqual(response.status_code, 201)
		data = response.json()
		self.assertTrue(data["image_url"])
		self.assertIn("publicaciones/", data["image_url"])

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_create_publicacion_rejects_file_disguised_as_image(self, geocode_address):
		geocode_address.return_value.latitud = "4.653332"
		geocode_address.return_value.longitud = "-74.083652"
		geocode_address.return_value.direccion_texto = "Calle 10 # 20-30, Bogota"

		malicious = SimpleUploadedFile(
			"evil.svg", b"<svg onload='alert(1)'/>", content_type="image/png"
		)

		response = self.client.post(
			"/api/publicaciones",
			{
				"titulo": "X", "descripcion": "Y", "precio": 1000,
				"direccion_texto": "Calle 10 # 20-30", "imagen": malicious,
			},
		)

		self.assertEqual(response.status_code, 400)

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_create_publicacion_rejects_disallowed_content_type(self, geocode_address):
		geocode_address.return_value.latitud = "4.653332"
		geocode_address.return_value.longitud = "-74.083652"
		geocode_address.return_value.direccion_texto = "Calle 10 # 20-30, Bogota"

		malicious = SimpleUploadedFile("shell.php", b"<?php system($_GET['c']); ?>", content_type="application/x-php")

		response = self.client.post(
			"/api/publicaciones",
			{
				"titulo": "X", "descripcion": "Y", "precio": 1000,
				"direccion_texto": "Calle 10 # 20-30", "imagen": malicious,
			},
		)

		self.assertEqual(response.status_code, 400)

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_create_publicacion_rejects_oversized_image(self, geocode_address):
		geocode_address.return_value.latitud = "4.653332"
		geocode_address.return_value.longitud = "-74.083652"
		geocode_address.return_value.direccion_texto = "Calle 10 # 20-30, Bogota"

		oversized = SimpleUploadedFile(
			"big.png", b"0" * (5 * 1024 * 1024 + 1), content_type="image/png"
		)

		response = self.client.post(
			"/api/publicaciones",
			{
				"titulo": "X", "descripcion": "Y", "precio": 1000,
				"direccion_texto": "Calle 10 # 20-30", "imagen": oversized,
			},
		)

		self.assertEqual(response.status_code, 400)

	def test_list_only_publicaciones_within_five_km(self):
		ubicacion_cercana = Ubicacion.objects.create(
			direccion_texto="Punto cercano",
			latitud="4.653900",
			longitud="-74.083100",
		)
		ubicacion_lejana = Ubicacion.objects.create(
			direccion_texto="Punto lejano",
			latitud="4.720000",
			longitud="-74.083100",
		)

		Publicacion.objects.create(
			titulo="Ajiaco",
			descripcion="Cercano",
			precio=18000,
			usuario=self.seller,
			ubicacion=ubicacion_cercana,
		)
		Publicacion.objects.create(
			titulo="Sancocho",
			descripcion="Lejano",
			precio=19000,
			usuario=self.seller,
			ubicacion=ubicacion_lejana,
		)

		response = self.client.get(
			"/api/publicaciones/cercanas",
			{
				"latitud": "4.653332",
				"longitud": "-74.083652",
				"radio_km": 5,
			},
		)

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(len(data), 1)
		self.assertEqual(data[0]["titulo"], "Ajiaco")
		self.assertLessEqual(data[0]["distancia_km"], 5.0)

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_list_publicaciones_by_address_when_geolocation_is_not_available(self, geocode_address):
		geocode_address.return_value.latitud = "4.653332"
		geocode_address.return_value.longitud = "-74.083652"
		geocode_address.return_value.direccion_texto = "Calle 10 # 20-30, Bogota"

		ubicacion_cercana = Ubicacion.objects.create(
			direccion_texto="Punto cercano",
			latitud="4.653900",
			longitud="-74.083100",
		)
		Publicacion.objects.create(
			titulo="Arroz con pollo",
			descripcion="Cercano por direccion",
			precio=21000,
			usuario=self.seller,
			ubicacion=ubicacion_cercana,
		)

		response = self.client.get(
			"/api/publicaciones/cercanas",
			{
				"direccion_texto": "Calle 10 # 20-30, Bogota",
				"radio_km": 5,
			},
		)

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(len(data), 1)
		self.assertEqual(data[0]["titulo"], "Arroz con pollo")

	def test_delete_my_publicacion(self):
		ubicacion = Ubicacion.objects.create(
			direccion_texto="Calle 44 # 10-20, Medellin",
			latitud="6.244203",
			longitud="-75.581212",
		)
		publicacion = Publicacion.objects.create(
			titulo="Menu temporal",
			descripcion="Eliminar",
			precio=15000,
			usuario=self.seller,
			ubicacion=ubicacion,
		)

		response = self.client.delete(f"/api/publicaciones/{publicacion.id}")

		self.assertEqual(response.status_code, 204)
		self.assertFalse(Publicacion.objects.filter(id=publicacion.id).exists())
		self.assertFalse(Ubicacion.objects.filter(id=ubicacion.id).exists())


class PedidoAceptarApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()

		self.seller = User(username="seller3@example.com", email="seller3@example.com", nombre="Seller3")
		self.seller.set_password("secret12345")
		self.seller.save()

		self.buyer = User(username="buyer3@example.com", email="buyer3@example.com", nombre="Buyer3")
		self.buyer.set_password("secret12345")
		self.buyer.save()

		self.other = User(username="other3@example.com", email="other3@example.com", nombre="Other3")
		self.other.set_password("secret12345")
		self.other.save()

		self.publicacion = Publicacion.objects.create(
			titulo="Empanadas",
			descripcion="Ricas",
			precio=8000,
			usuario=self.seller,
		)

	def _pedido(self, estado="PENDIENTE"):
		return Pedido.objects.create(
			telefono="123456",
			total=8000,
			publicacion=self.publicacion,
			usuario=self.buyer,
			estado=estado,
		)

	def _auth_as(self, user):
		access = str(RefreshToken.for_user(user).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_seller_accepts_own_pedido(self):
		pedido = self._pedido(estado="PENDIENTE")
		self._auth_as(self.seller)

		response = self.client.patch(f"/api/pedidos/{pedido.id}/aceptar/")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["estado"], "ACEPTADO")
		pedido.refresh_from_db()
		self.assertEqual(pedido.estado, "ACEPTADO")

	def test_non_owner_cannot_accept_pedido(self):
		pedido = self._pedido(estado="PENDIENTE")
		self._auth_as(self.other)

		response = self.client.patch(f"/api/pedidos/{pedido.id}/aceptar/")

		self.assertEqual(response.status_code, 403)
		pedido.refresh_from_db()
		self.assertEqual(pedido.estado, "PENDIENTE")

	def test_cannot_accept_pedido_not_pending(self):
		pedido = self._pedido(estado="ACEPTADO")
		self._auth_as(self.seller)

		response = self.client.patch(f"/api/pedidos/{pedido.id}/aceptar/")

		self.assertEqual(response.status_code, 400)

	def test_accept_nonexistent_pedido_returns_404(self):
		self._auth_as(self.seller)

		response = self.client.patch("/api/pedidos/999999/aceptar/")

		self.assertEqual(response.status_code, 404)


class PublicOrderHistoryApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()

		seller = User(username="seller2@example.com", email="seller2@example.com", nombre="Seller2")
		seller.set_password("secret12345")
		seller.save()

		buyer = User(username="buyer2@example.com", email="buyer2@example.com", nombre="Buyer2")
		buyer.set_password("secret12345")
		buyer.save()

		publicacion = Publicacion.objects.create(
			titulo="Burrito",
			descripcion="Grande",
			precio=15000,
			usuario=seller,
		)

		pedido = Pedido.objects.create(
			telefono="3001234567",
			direccion_entrega="Calle 1",
			total=15000,
			publicacion=publicacion,
			usuario=buyer,
		)

		pedido.items.create(publicacion=publicacion, cantidad=2, precio_unitario=7500)

	def test_public_history_endpoint_allows_anonymous(self):
		response = self.client.get("/api/aliados/historial-pedidos")

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertIn("results", payload)
		self.assertGreaterEqual(payload["count"], 1)
		self.assertEqual(response["Access-Control-Allow-Origin"], "*")

		first = payload["results"][0]
		self.assertIn("id", first)
		self.assertIn("total", first)
		self.assertIn("items", first)
		self.assertNotIn("telefono", first)

	def test_public_history_endpoint_respects_limit_param(self):
		response = self.client.get("/api/aliados/historial-pedidos?limit=1")

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload["limit"], 1)

	def test_public_history_invalid_limit_returns_400(self):
		response = self.client.get("/api/aliados/historial-pedidos?limit=abc")
		self.assertEqual(response.status_code, 400)

	def test_public_history_options_returns_cors_headers(self):
		response = self.client.options("/api/aliados/historial-pedidos")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response["Access-Control-Allow-Origin"], "*")
		self.assertEqual(response["Access-Control-Allow-Headers"], "Content-Type")


class MarketModelsTests(TestCase):
	def setUp(self):
		self.seller = User(username="model_seller@example.com", email="model_seller@example.com", nombre="Seller")
		self.seller.set_password("secret12345")
		self.seller.save()
		self.buyer = User(username="model_buyer@example.com", email="model_buyer@example.com", nombre="Buyer")
		self.buyer.set_password("secret12345")
		self.buyer.save()
		self.publicacion = Publicacion.objects.create(
			titulo="Arepa", descripcion="Rica", precio=5000, usuario=self.seller,
		)

	def test_publicacion_str_is_titulo(self):
		self.assertEqual(str(self.publicacion), "Arepa")

	def test_pedido_str_includes_id_and_estado(self):
		pedido = Pedido.objects.create(
			telefono="123", total=5000, publicacion=self.publicacion, usuario=self.buyer,
		)
		self.assertIn(str(pedido.id), str(pedido))
		self.assertIn("PENDIENTE", str(pedido))

	def test_pedido_item_str_includes_pedido_id(self):
		pedido = Pedido.objects.create(
			telefono="123", total=5000, publicacion=self.publicacion, usuario=self.buyer,
		)
		item = PedidoItem.objects.create(pedido=pedido, publicacion=self.publicacion, cantidad=1, precio_unitario=5000)
		self.assertIn(str(pedido.id), str(item))


class OrderRulesTests(TestCase):
	def _snapshot(self, **overrides):
		defaults = dict(id=1, titulo="Sopa", estado="ACTIVA", stock=10, maximo_por_venta=5, precio=1000.0)
		defaults.update(overrides)
		return PublicacionSnapshot(**defaults)

	def test_rejects_unavailable_publicacion(self):
		snapshot = self._snapshot(estado="PAUSADA")
		with self.assertRaises(ValidationError):
			validate_and_price_items({1: 1}, {1: snapshot})

	def test_rejects_insufficient_stock(self):
		snapshot = self._snapshot(stock=1)
		with self.assertRaises(ValidationError):
			validate_and_price_items({1: 5}, {1: snapshot})

	def test_rejects_exceeding_maximo_por_venta(self):
		snapshot = self._snapshot(maximo_por_venta=2)
		with self.assertRaises(ValidationError):
			validate_and_price_items({1: 3}, {1: snapshot})

	def test_computes_total_with_delivery_fee(self):
		snapshot = self._snapshot(precio=1000.0)
		total = validate_and_price_items({1: 2}, {1: snapshot}, delivery_fee=500.0)
		self.assertEqual(total, 2500.0)

	def test_rejects_when_total_not_positive(self):
		with self.assertRaises(ValidationError):
			validate_and_price_items({}, {}, delivery_fee=0.0)


class PedidoBuilderTests(TestCase):
	def setUp(self):
		self.seller = User(username="builder_seller@example.com", email="builder_seller@example.com", nombre="Seller")
		self.seller.set_password("secret12345")
		self.seller.save()
		self.buyer = User(username="builder_buyer@example.com", email="builder_buyer@example.com", nombre="Buyer")
		self.buyer.set_password("secret12345")
		self.buyer.save()
		self.publicacion = Publicacion.objects.create(
			titulo="Torta", descripcion="Dulce", precio=8000, usuario=self.seller,
		)

	def test_default_repository_is_created_when_not_injected(self):
		builder = PedidoBuilder()
		self.assertIsNotNone(builder.pedido_repository)

	def test_build_requires_user(self):
		with self.assertRaises(ValueError):
			PedidoBuilder().build()

	def test_build_requires_non_blank_telefono(self):
		with self.assertRaises(ValidationError):
			(
				PedidoBuilder()
				.for_user(self.buyer)
				.with_telefono("   ")
				.with_delivery_address("Calle 1")
				.with_publicacion_id(self.publicacion.id)
				.build()
			)

	def test_build_requires_non_blank_direccion(self):
		with self.assertRaises(ValidationError):
			(
				PedidoBuilder()
				.for_user(self.buyer)
				.with_telefono("123")
				.with_delivery_address("   ")
				.with_publicacion_id(self.publicacion.id)
				.build()
			)

	def test_build_rejects_both_publicacion_id_and_ids(self):
		with self.assertRaises(ValidationError):
			(
				PedidoBuilder()
				.for_user(self.buyer)
				.with_telefono("123")
				.with_delivery_address("Calle 1")
				.with_publicacion_id(self.publicacion.id)
				.with_publicacion_ids([self.publicacion.id])
				.build()
			)

	def test_build_requires_at_least_one_publicacion(self):
		with self.assertRaises(ValidationError):
			(
				PedidoBuilder()
				.for_user(self.buyer)
				.with_telefono("123")
				.with_delivery_address("Calle 1")
				.build()
			)


class PublicacionListCreateApiTests(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.seller = User(username="list_seller@example.com", email="list_seller@example.com", nombre="Seller")
		self.seller.set_password("secret12345")
		self.seller.save()
		self.repartidor = User(
			username="list_repartidor@example.com", email="list_repartidor@example.com",
			nombre="Repartidor", es_repartidor=True,
		)
		self.repartidor.set_password("secret12345")
		self.repartidor.save()
		Publicacion.objects.create(titulo="Existing", descripcion="X", precio=1000, usuario=self.seller)

		access = str(RefreshToken.for_user(self.seller).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_list_publicaciones(self):
		response = self.client.get("/api/publicaciones")
		self.assertEqual(response.status_code, 200)
		self.assertGreaterEqual(len(response.json()), 1)

	def test_list_publicaciones_second_call_hits_cache(self):
		with patch(
			"market.interfaces.api.views.ListPublicacionesUseCase.execute",
			side_effect=lambda: list(Publicacion.objects.all()),
		) as execute:
			first = self.client.get("/api/publicaciones")
			second = self.client.get("/api/publicaciones")

		self.assertEqual(first.status_code, 200)
		self.assertEqual(second.status_code, 200)
		self.assertEqual(execute.call_count, 1)
		self.assertEqual(first.json(), second.json())

	def test_creating_publicacion_invalidates_list_cache(self):
		before = self.client.get("/api/publicaciones").json()

		with patch("market.domain.services.GeocodingService.geocode_address") as geocode_address:
			geocode_address.return_value.latitud = "4.65"
			geocode_address.return_value.longitud = "-74.08"
			geocode_address.return_value.direccion_texto = "Calle 1"
			self.client.post(
				"/api/publicaciones",
				{"titulo": "Nueva desde cache test", "descripcion": "Y", "precio": 1000, "direccion_texto": "Calle 1"},
				format="json",
			)

		after = self.client.get("/api/publicaciones").json()
		self.assertEqual(len(after), len(before) + 1)
		self.assertIn("Nueva desde cache test", [p["titulo"] for p in after])

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_create_publicacion_geocode_failure_returns_400(self, geocode_address):
		geocode_address.side_effect = ValidationError("No se pudo ubicar la dirección proporcionada")

		response = self.client.post(
			"/api/publicaciones",
			{"titulo": "X", "descripcion": "Y", "precio": 1000, "direccion_texto": "direccion invalida"},
			format="json",
		)
		self.assertEqual(response.status_code, 400)

	def test_repartidor_cannot_create_publicacion(self):
		access = str(RefreshToken.for_user(self.repartidor).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

		response = self.client.post(
			"/api/publicaciones",
			{"titulo": "X", "descripcion": "Y", "precio": 1000, "direccion_texto": "Calle 1"},
			format="json",
		)
		self.assertEqual(response.status_code, 403)

	def test_create_publicacion_requires_both_coords(self):
		response = self.client.post(
			"/api/publicaciones",
			{
				"titulo": "X", "descripcion": "Y", "precio": 1000,
				"direccion_texto": "Calle 1", "latitud": "4.6",
			},
			format="json",
		)
		self.assertEqual(response.status_code, 400)

	def test_create_publicacion_with_coords_skips_geocoding(self):
		with patch("market.domain.services.GeocodingService.geocode_address") as geocode_address:
			response = self.client.post(
				"/api/publicaciones",
				{
					"titulo": "Con coords", "descripcion": "Y", "precio": 1000, "direccion_texto": "Calle 1",
					"latitud": "4.65", "longitud": "-74.08",
				},
				format="json",
			)
		self.assertEqual(response.status_code, 201)
		geocode_address.assert_not_called()

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_create_publicacion_without_categoria_defaults_blank(self, geocode_address):
		geocode_address.return_value.latitud = "4.65"
		geocode_address.return_value.longitud = "-74.08"
		geocode_address.return_value.direccion_texto = "Calle 1"

		response = self.client.post(
			"/api/publicaciones",
			{"titulo": "Sin categoria", "descripcion": "Y", "precio": 1000, "direccion_texto": "Calle 1"},
			format="json",
		)
		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()["categoria"], "")

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_create_publicacion_deduplicates_ingredientes(self, geocode_address):
		geocode_address.return_value.latitud = "4.65"
		geocode_address.return_value.longitud = "-74.08"
		geocode_address.return_value.direccion_texto = "Calle 1"

		response = self.client.post(
			"/api/publicaciones",
			{
				"titulo": "Con ingredientes", "descripcion": "Y", "precio": 1000, "direccion_texto": "Calle 1",
				"ingredientes": ["Tomate", "Tomate", "Queso"],
			},
			format="json",
		)
		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()["ingredientes"], ["Tomate", "Queso"])


class CatalogServiceDirectTests(TestCase):
	"""Cubre ramas defensivas de CatalogService que el serializer de la API ya
	bloquea antes de llegar al dominio (categoria invalida, coordenadas
	ausentes, ubicacion nula) — se llaman directo para ejercitarlas."""

	def setUp(self):
		from market.domain.services import CatalogService

		self.service = CatalogService()
		self.seller = User(username="catsvc_seller@example.com", email="catsvc_seller@example.com", nombre="Seller")
		self.seller.set_password("secret12345")
		self.seller.save()

	def test_clean_categoria_rejects_unknown_value(self):
		with self.assertRaises(ValidationError):
			self.service._clean_categoria("no-existe")

	def test_clean_categoria_blank_returns_empty_string(self):
		self.assertEqual(self.service._clean_categoria(None), "")
		self.assertEqual(self.service._clean_categoria("  "), "")

	def test_resolve_coordinates_requires_location_when_called_directly(self):
		with self.assertRaises(ValidationError):
			self.service._resolve_coordinates()

	def test_clean_ingredientes_skips_blank_and_dedupes(self):
		result = self.service._clean_ingredientes(["Tomate", "  ", "Tomate", " Queso "])
		self.assertEqual(result, ["Tomate", "Queso"])

	def test_clean_ingredientes_handles_none(self):
		self.assertEqual(self.service._clean_ingredientes(None), [])

	def _publicacion(self):
		return Publicacion.objects.create(
			titulo="Directo", descripcion="X", precio=1000, usuario=self.seller,
		)

	def test_update_publicacion_blank_titulo_after_strip_raises(self):
		publicacion = self._publicacion()
		with self.assertRaises(ValidationError):
			self.service.update_publicacion(user=self.seller, publicacion_id=publicacion.id, titulo="   ")

	def test_update_publicacion_blank_descripcion_after_strip_raises(self):
		publicacion = self._publicacion()
		with self.assertRaises(ValidationError):
			self.service.update_publicacion(user=self.seller, publicacion_id=publicacion.id, descripcion="   ")

	def test_update_publicacion_non_positive_precio_raises(self):
		publicacion = self._publicacion()
		with self.assertRaises(ValidationError):
			self.service.update_publicacion(user=self.seller, publicacion_id=publicacion.id, precio=-5)

	def test_update_publicacion_no_changes_raises(self):
		publicacion = self._publicacion()
		with self.assertRaises(ValidationError):
			self.service.update_publicacion(user=self.seller, publicacion_id=publicacion.id)

	def test_list_publicaciones_cercanas_skips_entries_without_ubicacion(self):
		from unittest.mock import MagicMock

		from market.domain.services import CatalogService as CatalogServiceCls

		publicacion_sin_ubicacion = MagicMock(ubicacion=None)
		repo = MagicMock()
		repo.list_active_with_location.return_value = [publicacion_sin_ubicacion]

		service = CatalogServiceCls(publicacion_repository=repo)
		resultado = service.list_publicaciones_cercanas(latitud=4.65, longitud=-74.08)

		self.assertEqual(resultado, [])



class PublicacionNearbyApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.seller = User(username="nearby_seller@example.com", email="nearby_seller@example.com", nombre="Seller")
		self.seller.set_password("secret12345")
		self.seller.save()
		access = str(RefreshToken.for_user(self.seller).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_requires_location_or_address(self):
		response = self.client.get("/api/publicaciones/cercanas")
		self.assertEqual(response.status_code, 400)

	def test_coords_missing_pair_returns_400(self):
		response = self.client.get("/api/publicaciones/cercanas", {"latitud": "4.6"})
		self.assertEqual(response.status_code, 400)

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_nearby_geocode_failure_returns_400(self, geocode_address):
		geocode_address.side_effect = ValidationError("No se pudo ubicar la dirección proporcionada")

		response = self.client.get(
			"/api/publicaciones/cercanas", {"direccion_texto": "direccion invalida"}
		)
		self.assertEqual(response.status_code, 400)

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_lookup_by_direccion_texto(self, geocode_address):
		geocode_address.return_value.latitud = "4.653332"
		geocode_address.return_value.longitud = "-74.083652"

		ubicacion = Ubicacion.objects.create(
			direccion_texto="Cerca", latitud="4.653900", longitud="-74.083100",
		)
		Publicacion.objects.create(
			titulo="Cercano", descripcion="X", precio=1000, usuario=self.seller, ubicacion=ubicacion,
		)

		response = self.client.get(
			"/api/publicaciones/cercanas", {"direccion_texto": "Calle 10, Bogota"}
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.json()), 1)


class PedidoDetailAndDeliveryApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.seller = User(username="detail_seller@example.com", email="detail_seller@example.com", nombre="Seller")
		self.seller.set_password("secret12345")
		self.seller.save()
		self.buyer = User(username="detail_buyer@example.com", email="detail_buyer@example.com", nombre="Buyer")
		self.buyer.set_password("secret12345")
		self.buyer.save()
		self.publicacion = Publicacion.objects.create(
			titulo="Pizza", descripcion="X", precio=15000, usuario=self.seller,
		)
		access = str(RefreshToken.for_user(self.buyer).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def _pedido(self, estado="PENDIENTE"):
		return Pedido.objects.create(
			telefono="123", total=15000, publicacion=self.publicacion, usuario=self.buyer, estado=estado,
		)

	def test_get_own_pedido(self):
		pedido = self._pedido()
		response = self.client.get(f"/api/pedidos/{pedido.id}")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["id"], pedido.id)

	def test_get_pedido_not_found(self):
		response = self.client.get("/api/pedidos/999999")
		self.assertEqual(response.status_code, 404)

	def test_mark_delivered_is_idempotent(self):
		pedido = self._pedido(estado="ENTREGADO")
		response = self.client.patch(f"/api/pedidos/{pedido.id}/entregar")
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["estado"], "ENTREGADO")

	def test_mark_delivered_not_found(self):
		response = self.client.patch("/api/pedidos/999999/entregar")
		self.assertEqual(response.status_code, 404)

	@patch("market.interfaces.api.views.MarkOrderDeliveredUseCase.execute")
	def test_mark_delivered_translates_domain_validation_error(self, execute):
		execute.side_effect = ValidationError("regla de negocio violada")
		pedido = self._pedido()

		response = self.client.patch(f"/api/pedidos/{pedido.id}/entregar")

		self.assertEqual(response.status_code, 400)

	def test_set_propina_success(self):
		pedido = self._pedido()
		response = self.client.patch(
			f"/api/pedidos/{pedido.id}/propina", {"propina": 2000}, format="json"
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["propina"], 2000)
		pedido.refresh_from_db()
		self.assertEqual(pedido.propina, 2000)

	def test_set_propina_not_found(self):
		response = self.client.patch(
			"/api/pedidos/999999/propina", {"propina": 2000}, format="json"
		)
		self.assertEqual(response.status_code, 404)

	def test_set_propina_rejects_negative(self):
		pedido = self._pedido()
		response = self.client.patch(
			f"/api/pedidos/{pedido.id}/propina", {"propina": -100}, format="json"
		)
		self.assertEqual(response.status_code, 400)


class PedidoCreateEdgeCasesApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.seller = User(username="edge_seller@example.com", email="edge_seller@example.com", nombre="Seller")
		self.seller.set_password("secret12345")
		self.seller.save()
		self.buyer = User(username="edge_buyer@example.com", email="edge_buyer@example.com", nombre="Buyer")
		self.buyer.set_password("secret12345")
		self.buyer.save()
		self.repartidor = User(
			username="edge_repartidor@example.com", email="edge_repartidor@example.com",
			nombre="Repartidor", es_repartidor=True,
		)
		self.repartidor.set_password("secret12345")
		self.repartidor.save()
		self.publicacion = Publicacion.objects.create(
			titulo="Tamal", descripcion="X", precio=6000, usuario=self.seller,
		)
		access = str(RefreshToken.for_user(self.buyer).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_repartidor_cannot_create_pedido(self):
		access = str(RefreshToken.for_user(self.repartidor).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

		response = self.client.post(
			"/api/pedidos",
			{"publicacion_id": self.publicacion.id, "telefono": "123", "direccion_entrega": "Calle 1"},
			format="json",
		)
		self.assertEqual(response.status_code, 403)

	def test_create_pedido_requires_both_delivery_coords(self):
		response = self.client.post(
			"/api/pedidos",
			{
				"publicacion_id": self.publicacion.id, "telefono": "123", "direccion_entrega": "Calle 1",
				"direccion_entrega_latitud": "4.6",
			},
			format="json",
		)
		self.assertEqual(response.status_code, 400)

	def test_create_pedido_publicacion_not_found_returns_404(self):
		response = self.client.post(
			"/api/pedidos",
			{
				"publicacion_id": 999999,
				"telefono": "123",
				"direccion_entrega": "Calle 1",
				"direccion_entrega_latitud": "4.65",
				"direccion_entrega_longitud": "-74.08",
			},
			format="json",
		)
		self.assertEqual(response.status_code, 404)

	def test_create_pedido_unavailable_publicacion_returns_400(self):
		self.publicacion.estado = "PAUSADA"
		self.publicacion.save(update_fields=["estado"])

		response = self.client.post(
			"/api/pedidos",
			{
				"publicacion_id": self.publicacion.id,
				"telefono": "123",
				"direccion_entrega": "Calle 1",
				"direccion_entrega_latitud": "4.65",
				"direccion_entrega_longitud": "-74.08",
			},
			format="json",
		)
		self.assertEqual(response.status_code, 400)
		self.assertIn("no está disponible", response.json()["detail"])

	@patch("market.domain.services.GeocodingService.geocode_address")
	def test_create_pedido_geocodes_when_coords_missing(self, geocode_address):
		geocode_address.return_value.latitud = "4.65"
		geocode_address.return_value.longitud = "-74.08"

		response = self.client.post(
			"/api/pedidos",
			{"publicacion_id": self.publicacion.id, "telefono": "123", "direccion_entrega": "Calle 1 sin coords"},
			format="json",
		)
		self.assertEqual(response.status_code, 201)
		geocode_address.assert_called_once()


class MisPublicacionesApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.seller = User(username="mispub_seller@example.com", email="mispub_seller@example.com", nombre="Seller")
		self.seller.set_password("secret12345")
		self.seller.save()
		self.buyer = User(username="mispub_buyer@example.com", email="mispub_buyer@example.com", nombre="Buyer")
		self.buyer.set_password("secret12345")
		self.buyer.save()
		self.publicacion = Publicacion.objects.create(
			titulo="Jugo", descripcion="X", precio=3000, usuario=self.seller,
		)
		pedido = Pedido.objects.create(
			telefono="1", total=3000, publicacion=self.publicacion, usuario=self.buyer,
		)
		pedido.items.create(publicacion=self.publicacion, cantidad=2, precio_unitario=3000)

		access = str(RefreshToken.for_user(self.seller).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_returns_own_publicaciones_with_totals(self):
		response = self.client.get("/api/mis-publicaciones")
		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(len(data["publicaciones"]), 1)
		self.assertEqual(data["total_unidades_vendidas"], 2)
		self.assertEqual(data["saldo_disponible"], 6000.0)


class PublicacionDetailUpdateApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.seller = User(username="detailupd_seller@example.com", email="detailupd_seller@example.com", nombre="Seller")
		self.seller.set_password("secret12345")
		self.seller.save()
		self.other = User(username="detailupd_other@example.com", email="detailupd_other@example.com", nombre="Other")
		self.other.set_password("secret12345")
		self.other.save()
		self.publicacion = Publicacion.objects.create(
			titulo="Original", descripcion="X", precio=4000, usuario=self.seller,
		)
		access = str(RefreshToken.for_user(self.seller).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_patch_updates_titulo(self):
		response = self.client.patch(
			f"/api/publicaciones/{self.publicacion.id}", {"titulo": "Nuevo"}, format="json"
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["titulo"], "Nuevo")

	def test_patch_no_fields_returns_400(self):
		response = self.client.patch(f"/api/publicaciones/{self.publicacion.id}", {}, format="json")
		self.assertEqual(response.status_code, 400)

	def test_patch_blank_titulo_after_strip_returns_400(self):
		response = self.client.patch(
			f"/api/publicaciones/{self.publicacion.id}", {"titulo": "   "}, format="json"
		)
		self.assertEqual(response.status_code, 400)

	def test_patch_blank_descripcion_after_strip_returns_400(self):
		response = self.client.patch(
			f"/api/publicaciones/{self.publicacion.id}", {"descripcion": "   "}, format="json"
		)
		self.assertEqual(response.status_code, 400)

	def test_patch_updates_every_field_at_once(self):
		response = self.client.patch(
			f"/api/publicaciones/{self.publicacion.id}",
			{
				"titulo": "Actualizado",
				"descripcion": "Nueva desc",
				"categoria": "postres",
				"ingredientes": ["Azucar", "Azucar"],
				"stock": 7,
				"maximo_por_venta": 3,
				"precio": 9999,
				"estado": "PAUSADA",
			},
			format="json",
		)
		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(data["titulo"], "Actualizado")
		self.assertEqual(data["descripcion"], "Nueva desc")
		self.assertEqual(data["categoria"], "postres")
		self.assertEqual(data["ingredientes"], ["Azucar"])
		self.assertEqual(data["stock"], 7)
		self.assertEqual(data["maximo_por_venta"], 3)
		self.assertEqual(data["precio"], 9999)
		self.assertEqual(data["estado"], "PAUSADA")

	def test_patch_not_owner_returns_403(self):
		access = str(RefreshToken.for_user(self.other).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

		response = self.client.patch(
			f"/api/publicaciones/{self.publicacion.id}", {"titulo": "Hackeado"}, format="json"
		)
		self.assertEqual(response.status_code, 403)

	def test_patch_not_found_returns_404(self):
		response = self.client.patch("/api/publicaciones/999999", {"titulo": "X"}, format="json")
		self.assertEqual(response.status_code, 404)

	@patch("market.interfaces.api.views.UpdatePublicacionUseCase.execute")
	def test_patch_translates_domain_validation_error(self, execute):
		execute.side_effect = ValidationError("regla de negocio violada")

		response = self.client.patch(
			f"/api/publicaciones/{self.publicacion.id}", {"titulo": "Nuevo"}, format="json"
		)

		self.assertEqual(response.status_code, 400)

	def test_delete_success(self):
		response = self.client.delete(f"/api/publicaciones/{self.publicacion.id}")
		self.assertEqual(response.status_code, 204)
		self.assertFalse(Publicacion.objects.filter(id=self.publicacion.id).exists())

	def test_delete_not_owner_returns_403(self):
		access = str(RefreshToken.for_user(self.other).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

		response = self.client.delete(f"/api/publicaciones/{self.publicacion.id}")
		self.assertEqual(response.status_code, 403)

	def test_delete_not_found_returns_404(self):
		response = self.client.delete("/api/publicaciones/999999")
		self.assertEqual(response.status_code, 404)


class ValidatePublicacionImagenTests(TestCase):
	def test_none_passes_silently(self):
		validate_publicacion_imagen(None)

	def test_valid_image_passes(self):
		image = SimpleUploadedFile("ok.png", _valid_png_bytes(), content_type="image/png")
		validate_publicacion_imagen(image)

	def test_rejects_disallowed_content_type(self):
		image = SimpleUploadedFile("ok.png", _valid_png_bytes(), content_type="application/pdf")
		with self.assertRaises(DjangoValidationError):
			validate_publicacion_imagen(image)

	def test_rejects_content_that_is_not_really_an_image(self):
		fake = SimpleUploadedFile("evil.svg", b"<svg onload='alert(1)'/>", content_type="image/png")
		with self.assertRaises(DjangoValidationError):
			validate_publicacion_imagen(fake)

	def test_rejects_oversized_file(self):
		big = SimpleUploadedFile("big.png", b"0" * (5 * 1024 * 1024 + 1), content_type="image/png")
		with self.assertRaises(DjangoValidationError):
			validate_publicacion_imagen(big)

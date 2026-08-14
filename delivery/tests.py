from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.infrastructure.models import User
from common.exceptions import ValidationError
from geo.infrastructure.models import Ubicacion
from market.domain.order_rules import DELIVERY_FEE_COP
from market.infrastructure.models import Pedido, Publicacion

from .domain.rules import (
    current_payout_period,
    haversine_meters,
    next_state_after_location_update,
    validate_can_mark_finalizado,
    validate_can_mark_salio,
)
from .infrastructure.models import Asignacion, RepartidorPerfil

RECOGIDA_LAT = 4.653332
RECOGIDA_LNG = -74.083652
ENTREGA_LAT = 4.660000
ENTREGA_LNG = -74.090000
NEAR_OFFSET = 0.0003  # ~33m, dentro del geofence de 120m
FAR_OFFSET = 0.02  # ~2.2km, fuera del geofence


class DeliveryRulesTests(TestCase):
    def test_haversine_zero_distance(self):
        self.assertAlmostEqual(
            haversine_meters(lat1=4.6, lng1=-74.0, lat2=4.6, lng2=-74.0), 0.0
        )

    def test_haversine_known_distance_order_of_magnitude(self):
        distancia = haversine_meters(lat1=4.65, lng1=-74.08, lat2=4.66, lng2=-74.08)
        self.assertGreater(distancia, 1000)
        self.assertLess(distancia, 1200)

    def test_next_state_asignado_to_llego_recogida_within_radius(self):
        nuevo = next_state_after_location_update(
            estado_actual="ASIGNADO",
            repartidor_lat=RECOGIDA_LAT + NEAR_OFFSET,
            repartidor_lng=RECOGIDA_LNG,
            recogida_lat=RECOGIDA_LAT,
            recogida_lng=RECOGIDA_LNG,
            entrega_lat=ENTREGA_LAT,
            entrega_lng=ENTREGA_LNG,
        )
        self.assertEqual(nuevo, "LLEGO_RECOGIDA")

    def test_next_state_asignado_outside_radius_returns_none(self):
        nuevo = next_state_after_location_update(
            estado_actual="ASIGNADO",
            repartidor_lat=RECOGIDA_LAT + FAR_OFFSET,
            repartidor_lng=RECOGIDA_LNG,
            recogida_lat=RECOGIDA_LAT,
            recogida_lng=RECOGIDA_LNG,
            entrega_lat=ENTREGA_LAT,
            entrega_lng=ENTREGA_LNG,
        )
        self.assertIsNone(nuevo)

    def test_next_state_en_camino_to_llego_entrega_within_radius(self):
        nuevo = next_state_after_location_update(
            estado_actual="EN_CAMINO_ENTREGA",
            repartidor_lat=ENTREGA_LAT + NEAR_OFFSET,
            repartidor_lng=ENTREGA_LNG,
            recogida_lat=RECOGIDA_LAT,
            recogida_lng=RECOGIDA_LNG,
            entrega_lat=ENTREGA_LAT,
            entrega_lng=ENTREGA_LNG,
        )
        self.assertEqual(nuevo, "LLEGO_ENTREGA")

    def test_next_state_other_states_always_return_none(self):
        for estado in ("LLEGO_RECOGIDA", "LLEGO_ENTREGA", "FINALIZADO"):
            nuevo = next_state_after_location_update(
                estado_actual=estado,
                repartidor_lat=RECOGIDA_LAT,
                repartidor_lng=RECOGIDA_LNG,
                recogida_lat=RECOGIDA_LAT,
                recogida_lng=RECOGIDA_LNG,
                entrega_lat=ENTREGA_LAT,
                entrega_lng=ENTREGA_LNG,
            )
            self.assertIsNone(nuevo)

    def test_validate_can_mark_salio_raises_when_not_llego_recogida(self):
        with self.assertRaises(ValidationError):
            validate_can_mark_salio("ASIGNADO")

    def test_validate_can_mark_salio_allows_llego_recogida(self):
        validate_can_mark_salio("LLEGO_RECOGIDA")

    def test_validate_can_mark_finalizado_raises_when_not_llego_entrega(self):
        with self.assertRaises(ValidationError):
            validate_can_mark_finalizado("EN_CAMINO_ENTREGA")

    def test_validate_can_mark_finalizado_allows_llego_entrega(self):
        validate_can_mark_finalizado("LLEGO_ENTREGA")

    def test_current_payout_period_is_a_seven_day_window_containing_now(self):
        momento = datetime(2026, 8, 12, 15, 0, tzinfo=dt_timezone.utc)
        inicio, fin = current_payout_period(momento)
        self.assertEqual((fin - inicio).days, 7)
        self.assertLessEqual(inicio, momento.astimezone(inicio.tzinfo))
        self.assertGreater(fin, momento.astimezone(inicio.tzinfo))


class DeliveryModelsTests(TestCase):
    def test_repartidor_perfil_str(self):
        user = User(username="strtest@example.com", email="strtest@example.com", nombre="Str")
        user.set_password("secret12345")
        user.save()
        perfil = RepartidorPerfil.objects.create(usuario=user, activo=True)
        self.assertIn("activo=True", str(perfil))

    def test_asignacion_str(self):
        seller = User(username="strseller@example.com", email="strseller@example.com", nombre="Seller")
        seller.set_password("secret12345")
        seller.save()
        buyer = User(username="strbuyer@example.com", email="strbuyer@example.com", nombre="Buyer")
        buyer.set_password("secret12345")
        buyer.save()
        repartidor = User(username="strrepartidor@example.com", email="strrepartidor@example.com", nombre="R", es_repartidor=True)
        repartidor.set_password("secret12345")
        repartidor.save()
        publicacion = Publicacion.objects.create(titulo="X", descripcion="Y", precio=1000, usuario=seller)
        pedido = Pedido.objects.create(telefono="1", total=1000, publicacion=publicacion, usuario=buyer)
        asignacion = Asignacion.objects.create(pedido=pedido, repartidor=repartidor)
        self.assertIn(str(pedido.id), str(asignacion))
        self.assertIn("ASIGNADO", str(asignacion))


class DeliveryAPITestBase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.repartidor = User(
            username="repartidor@example.com", email="repartidor@example.com",
            nombre="Repartidor", es_repartidor=True,
        )
        self.repartidor.set_password("secret12345")
        self.repartidor.save()

        self.buyer = User(
            username="buyer_delivery@example.com", email="buyer_delivery@example.com", nombre="Buyer",
        )
        self.buyer.set_password("secret12345")
        self.buyer.save()

        self.seller = User(
            username="seller_delivery@example.com", email="seller_delivery@example.com", nombre="Seller",
        )
        self.seller.set_password("secret12345")
        self.seller.save()

        self.ubicacion_recogida = Ubicacion.objects.create(
            direccion_texto="Restaurante", latitud=RECOGIDA_LAT, longitud=RECOGIDA_LNG,
        )
        self.publicacion = Publicacion.objects.create(
            titulo="Bandeja paisa", descripcion="Rica", precio=20000,
            usuario=self.seller, ubicacion=self.ubicacion_recogida,
        )

    def auth_as(self, user):
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def create_pedido(self, estado="ACEPTADO", **extra):
        defaults = dict(
            telefono="3000000000",
            direccion_entrega="Calle 1",
            direccion_entrega_latitud=Decimal(str(ENTREGA_LAT)),
            direccion_entrega_longitud=Decimal(str(ENTREGA_LNG)),
            total=25000,
            publicacion=self.publicacion,
            usuario=self.buyer,
            estado=estado,
        )
        defaults.update(extra)
        return Pedido.objects.create(**defaults)

    def other_repartidor(self, suffix="2"):
        user = User(
            username=f"otro_repartidor{suffix}@example.com",
            email=f"otro_repartidor{suffix}@example.com",
            nombre="Otro Repartidor", es_repartidor=True,
        )
        user.set_password("secret12345")
        user.save()
        return user


class DisponibilidadAPITests(DeliveryAPITestBase):
    def test_non_repartidor_is_forbidden(self):
        self.auth_as(self.buyer)
        response = self.client.post("/api/repartidor/disponibilidad", {"activo": True}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_set_disponibilidad_true_then_false(self):
        self.auth_as(self.repartidor)
        response = self.client.post("/api/repartidor/disponibilidad", {"activo": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["activo"])
        self.assertTrue(RepartidorPerfil.objects.get(usuario=self.repartidor).activo)

        response = self.client.post("/api/repartidor/disponibilidad", {"activo": False}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["activo"])


class PedidosCercanosAPITests(DeliveryAPITestBase):
    def test_requires_location_set_first(self):
        self.auth_as(self.repartidor)
        response = self.client.get("/api/repartidor/pedidos-cercanos")
        self.assertEqual(response.status_code, 400)

    def test_lists_only_accepted_orders_within_radius_and_unassigned(self):
        self.auth_as(self.repartidor)
        self.client.post(
            "/api/repartidor/ubicacion", {"latitud": RECOGIDA_LAT, "longitud": RECOGIDA_LNG}, format="json"
        )

        pedido_cercano = self.create_pedido(estado="ACEPTADO")

        ubicacion_lejana = Ubicacion.objects.create(
            direccion_texto="Lejos", latitud=RECOGIDA_LAT + 1, longitud=RECOGIDA_LNG
        )
        publicacion_lejana = Publicacion.objects.create(
            titulo="Lejano", descripcion="x", precio=1000, usuario=self.seller, ubicacion=ubicacion_lejana
        )
        self.create_pedido(estado="ACEPTADO", publicacion=publicacion_lejana)

        self.create_pedido(estado="PENDIENTE")

        response = self.client.get("/api/repartidor/pedidos-cercanos")
        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], pedido_cercano.id)
        self.assertEqual(items[0]["ganancia"], DELIVERY_FEE_COP)

    def test_excludes_orders_already_assigned(self):
        self.auth_as(self.repartidor)
        self.client.post(
            "/api/repartidor/ubicacion", {"latitud": RECOGIDA_LAT, "longitud": RECOGIDA_LNG}, format="json"
        )
        pedido = self.create_pedido(estado="ACEPTADO")
        Asignacion.objects.create(pedido=pedido, repartidor=self.other_repartidor())

        response = self.client.get("/api/repartidor/pedidos-cercanos")
        self.assertEqual(response.json()["items"], [])


class AceptarPedidoAPITests(DeliveryAPITestBase):
    def test_accept_success(self):
        self.auth_as(self.repartidor)
        pedido = self.create_pedido(estado="ACEPTADO")
        response = self.client.post(f"/api/repartidor/pedidos/{pedido.id}/aceptar")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["pedido_id"], pedido.id)
        self.assertEqual(data["estado"], "ASIGNADO")
        self.assertTrue(Asignacion.objects.filter(pedido=pedido, repartidor=self.repartidor).exists())

    def test_accept_not_found_returns_404(self):
        self.auth_as(self.repartidor)
        response = self.client.post("/api/repartidor/pedidos/999999/aceptar")
        self.assertEqual(response.status_code, 404)

    def test_accept_pedido_not_ready_returns_400(self):
        self.auth_as(self.repartidor)
        pedido = self.create_pedido(estado="PENDIENTE")
        response = self.client.post(f"/api/repartidor/pedidos/{pedido.id}/aceptar")
        self.assertEqual(response.status_code, 400)

    def test_accept_conflict_when_already_taken(self):
        self.auth_as(self.repartidor)
        pedido = self.create_pedido(estado="ACEPTADO")
        Asignacion.objects.create(pedido=pedido, repartidor=self.other_repartidor())

        response = self.client.post(f"/api/repartidor/pedidos/{pedido.id}/aceptar")
        self.assertEqual(response.status_code, 409)

    def test_cannot_accept_second_order_while_one_is_active(self):
        self.auth_as(self.repartidor)
        primero = self.create_pedido(estado="ACEPTADO")
        self.client.post(f"/api/repartidor/pedidos/{primero.id}/aceptar")

        segundo = self.create_pedido(estado="ACEPTADO")
        response = self.client.post(f"/api/repartidor/pedidos/{segundo.id}/aceptar")
        self.assertEqual(response.status_code, 400)


class UbicacionAPITests(DeliveryAPITestBase):
    def _aceptar(self):
        pedido = self.create_pedido(estado="ACEPTADO")
        self.client.post(f"/api/repartidor/pedidos/{pedido.id}/aceptar")
        return pedido

    def test_update_location_without_active_assignment_returns_null(self):
        self.auth_as(self.repartidor)
        response = self.client.post(
            "/api/repartidor/ubicacion", {"latitud": RECOGIDA_LAT, "longitud": RECOGIDA_LNG}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["asignacion"])

    def test_arriving_at_recogida_transitions_state(self):
        self.auth_as(self.repartidor)
        self._aceptar()

        response = self.client.post(
            "/api/repartidor/ubicacion",
            {"latitud": RECOGIDA_LAT + NEAR_OFFSET, "longitud": RECOGIDA_LNG},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["asignacion"]["estado"], "LLEGO_RECOGIDA")

    def test_far_from_recogida_does_not_transition(self):
        self.auth_as(self.repartidor)
        self._aceptar()

        response = self.client.post(
            "/api/repartidor/ubicacion",
            {"latitud": RECOGIDA_LAT + FAR_OFFSET, "longitud": RECOGIDA_LNG},
            format="json",
        )
        self.assertEqual(response.json()["asignacion"]["estado"], "ASIGNADO")

    def test_arriving_at_entrega_transitions_state(self):
        self.auth_as(self.repartidor)
        pedido = self._aceptar()
        asignacion = Asignacion.objects.get(pedido=pedido)
        asignacion.estado = Asignacion.EN_CAMINO_ENTREGA
        asignacion.save(update_fields=["estado"])

        response = self.client.post(
            "/api/repartidor/ubicacion",
            {"latitud": ENTREGA_LAT + NEAR_OFFSET, "longitud": ENTREGA_LNG},
            format="json",
        )
        self.assertEqual(response.json()["asignacion"]["estado"], "LLEGO_ENTREGA")


class AsignacionActivaAPITests(DeliveryAPITestBase):
    def test_no_active_assignment_returns_null(self):
        self.auth_as(self.repartidor)
        response = self.client.get("/api/repartidor/asignacion-activa")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["asignacion"])

    def test_with_active_assignment_returns_data(self):
        self.auth_as(self.repartidor)
        pedido = self.create_pedido(estado="ACEPTADO")
        self.client.post(f"/api/repartidor/pedidos/{pedido.id}/aceptar")

        response = self.client.get("/api/repartidor/asignacion-activa")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["asignacion"]["pedido_id"], pedido.id)


class MarcarSalioAPITests(DeliveryAPITestBase):
    def test_marcar_salio_success(self):
        self.auth_as(self.repartidor)
        pedido = self.create_pedido(estado="ACEPTADO")
        self.client.post(f"/api/repartidor/pedidos/{pedido.id}/aceptar")
        asignacion = Asignacion.objects.get(pedido=pedido)
        asignacion.estado = Asignacion.LLEGO_RECOGIDA
        asignacion.save(update_fields=["estado"])

        response = self.client.post(f"/api/repartidor/pedidos/{pedido.id}/salio")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["estado"], "EN_CAMINO_ENTREGA")

    def test_marcar_salio_wrong_state_returns_400(self):
        self.auth_as(self.repartidor)
        pedido = self.create_pedido(estado="ACEPTADO")
        self.client.post(f"/api/repartidor/pedidos/{pedido.id}/aceptar")

        response = self.client.post(f"/api/repartidor/pedidos/{pedido.id}/salio")
        self.assertEqual(response.status_code, 400)

    def test_marcar_salio_no_assignment_returns_404(self):
        self.auth_as(self.repartidor)
        pedido = self.create_pedido(estado="ACEPTADO")
        response = self.client.post(f"/api/repartidor/pedidos/{pedido.id}/salio")
        self.assertEqual(response.status_code, 404)

    def test_marcar_salio_not_own_assignment_returns_403(self):
        self.auth_as(self.repartidor)
        pedido = self.create_pedido(estado="ACEPTADO")
        Asignacion.objects.create(
            pedido=pedido, repartidor=self.other_repartidor(), estado=Asignacion.LLEGO_RECOGIDA
        )

        response = self.client.post(f"/api/repartidor/pedidos/{pedido.id}/salio")
        self.assertEqual(response.status_code, 403)


class MarcarFinalizadoAPITests(DeliveryAPITestBase):
    def test_marcar_finalizado_success_marks_pedido_entregado(self):
        self.auth_as(self.repartidor)
        pedido = self.create_pedido(estado="ACEPTADO")
        self.client.post(f"/api/repartidor/pedidos/{pedido.id}/aceptar")
        asignacion = Asignacion.objects.get(pedido=pedido)
        asignacion.estado = Asignacion.LLEGO_ENTREGA
        asignacion.save(update_fields=["estado"])

        response = self.client.post(f"/api/repartidor/pedidos/{pedido.id}/finalizar")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["estado"], "FINALIZADO")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "ENTREGADO")

    def test_marcar_finalizado_wrong_state_returns_400(self):
        self.auth_as(self.repartidor)
        pedido = self.create_pedido(estado="ACEPTADO")
        self.client.post(f"/api/repartidor/pedidos/{pedido.id}/aceptar")

        response = self.client.post(f"/api/repartidor/pedidos/{pedido.id}/finalizar")
        self.assertEqual(response.status_code, 400)

    def test_marcar_finalizado_no_assignment_returns_404(self):
        self.auth_as(self.repartidor)
        pedido = self.create_pedido(estado="ACEPTADO")
        response = self.client.post(f"/api/repartidor/pedidos/{pedido.id}/finalizar")
        self.assertEqual(response.status_code, 404)


class HistorialYResumenAPITests(DeliveryAPITestBase):
    def _completar_entrega(self, propina=0.0):
        pedido = self.create_pedido(estado="ACEPTADO", propina=propina)
        self.client.post(f"/api/repartidor/pedidos/{pedido.id}/aceptar")
        asignacion = Asignacion.objects.get(pedido=pedido)
        asignacion.estado = Asignacion.LLEGO_RECOGIDA
        asignacion.save(update_fields=["estado"])
        self.client.post(f"/api/repartidor/pedidos/{pedido.id}/salio")
        asignacion.refresh_from_db()
        asignacion.estado = Asignacion.LLEGO_ENTREGA
        asignacion.save(update_fields=["estado"])
        self.client.post(f"/api/repartidor/pedidos/{pedido.id}/finalizar")
        return pedido

    def test_historial_counts_finalized_deliveries(self):
        self.auth_as(self.repartidor)
        self._completar_entrega()

        response = self.client.get("/api/repartidor/historial")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_entregas"], 1)
        self.assertEqual(len(data["items"]), 1)

    def test_resumen_reflects_todays_delivery(self):
        self.auth_as(self.repartidor)
        self._completar_entrega(propina=2000)

        response = self.client.get("/api/repartidor/resumen")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["hoy"]["viajes"], 1)
        self.assertEqual(data["semana"]["viajes"], 1)
        self.assertIn("proximo_pago", data["semana"])


class EstadoEntregaAPITests(DeliveryAPITestBase):
    def test_not_found_for_other_users_order(self):
        otro_comprador = User(
            username="otro_buyer@example.com", email="otro_buyer@example.com", nombre="OtroBuyer"
        )
        otro_comprador.set_password("secret12345")
        otro_comprador.save()
        pedido = self.create_pedido(estado="ACEPTADO", usuario=otro_comprador)

        self.auth_as(self.buyer)
        response = self.client.get(f"/api/pedidos/{pedido.id}/estado-entrega")
        self.assertEqual(response.status_code, 404)

    def test_no_assignment_yet_returns_nulls(self):
        pedido = self.create_pedido(estado="ACEPTADO")

        self.auth_as(self.buyer)
        response = self.client.get(f"/api/pedidos/{pedido.id}/estado-entrega")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["estado_entrega"])

    def test_with_assignment_returns_state_and_location(self):
        pedido = self.create_pedido(estado="ACEPTADO")

        self.auth_as(self.repartidor)
        self.client.post(
            "/api/repartidor/ubicacion", {"latitud": RECOGIDA_LAT, "longitud": RECOGIDA_LNG}, format="json"
        )
        self.client.post(f"/api/repartidor/pedidos/{pedido.id}/aceptar")

        self.auth_as(self.buyer)
        response = self.client.get(f"/api/pedidos/{pedido.id}/estado-entrega")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["estado_entrega"], "ASIGNADO")
        self.assertEqual(data["repartidor"], "Repartidor")
        self.assertIsNotNone(data["ubicacion"])

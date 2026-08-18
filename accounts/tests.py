import json
from unittest.mock import MagicMock

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from common.exceptions import AuthenticationError, ConflictError, ValidationError

from .application.use_cases.login_user import LoginUserUseCase
from .application.use_cases.register_user import RegisterUserUseCase
from .application.use_cases.reset_password import ResetPasswordUseCase
from .domain.services.auth_service import AccountPolicyService
from .infrastructure.models import DireccionGuardada, User


class LoginTests(TestCase):
	def setUp(self):
		cache.clear()
		self.email = "login_test@example.com"
		self.password = "secret12345"

		User.objects.filter(email=self.email).delete()
		user = User(username=self.email, email=self.email, nombre="Login Test")
		user.set_password(self.password)
		user.save()

	def test_login_success_returns_token_and_user(self):
		payload = {"email": self.email, "password": self.password}
		response = self.client.post(
			"/api/login",
			data=json.dumps(payload),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertIn("access", data)
		self.assertIn("refresh", data)
		self.assertIn("user", data)
		self.assertEqual(data["user"]["email"], self.email)

		# Verify the returned access token can authenticate a request.
		factory = APIRequestFactory()
		request = factory.get("/any", HTTP_AUTHORIZATION=f"Bearer {data['access']}")
		authenticated = JWTAuthentication().authenticate(request)
		self.assertIsNotNone(authenticated)
		user, _token = authenticated
		self.assertEqual(user.email, self.email)

	def test_login_invalid_credentials_returns_401(self):
		payload = {"email": self.email, "password": "wrong-password"}
		response = self.client.post(
			"/api/login",
			data=json.dumps(payload),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 401)
		self.assertEqual(response.json().get("detail"), "Credenciales inválidas")

	def test_login_email_is_case_insensitive(self):
		payload = {"email": self.email.upper(), "password": self.password}
		response = self.client.post(
			"/api/login",
			data=json.dumps(payload),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["user"]["email"], self.email)


class MeTests(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.user = User(username="me@example.com", email="me@example.com", nombre="Mi Perfil")
		self.user.set_password("secret12345")
		self.user.save()

		access = str(RefreshToken.for_user(self.user).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_me_returns_authenticated_user_data(self):
		response = self.client.get("/api/me")

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(data["email"], self.user.email)
		self.assertEqual(data["nombre"], self.user.nombre)

	def test_refresh_returns_new_access_token(self):
		refresh = str(RefreshToken.for_user(self.user))

		response = self.client.post(
			"/api/token/refresh",
			data=json.dumps({"refresh": refresh}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertIn("access", response.json())


class DeleteAccountAPITests(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.user = User(username="borrar@example.com", email="borrar@example.com", nombre="Borrar Cuenta")
		self.user.set_password("secret12345")
		self.user.save()

		access = str(RefreshToken.for_user(self.user).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_delete_requires_authentication(self):
		anon = APIClient()
		response = anon.delete(
			"/api/me",
			data=json.dumps({"password": "secret12345"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 401)

	def test_delete_requires_correct_password(self):
		response = self.client.delete(
			"/api/me",
			data=json.dumps({"password": "wrong-password"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertTrue(User.objects.filter(id=self.user.id).exists())

	def test_delete_removes_account_and_cascaded_data(self):
		from market.infrastructure.models import Publicacion

		DireccionGuardada.objects.create(
			usuario=self.user,
			nombre="Casa",
			direccion_texto="Calle 1",
			latitud=6.2,
			longitud=-75.5,
		)
		Publicacion.objects.create(
			titulo="Bandeja paisa",
			descripcion="Con todo",
			stock=10,
			maximo_por_venta=5,
			precio=25000,
			usuario=self.user,
		)

		response = self.client.delete(
			"/api/me",
			data=json.dumps({"password": "secret12345"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 204)
		self.assertFalse(User.objects.filter(id=self.user.id).exists())
		self.assertFalse(DireccionGuardada.objects.filter(usuario_id=self.user.id).exists())
		self.assertFalse(Publicacion.objects.filter(usuario_id=self.user.id).exists())

	def test_delete_blocked_by_active_order_as_buyer(self):
		from market.infrastructure.models import Pedido, Publicacion

		seller = User(username="vendedor@example.com", email="vendedor@example.com", nombre="Vendedor")
		seller.set_password("secret12345")
		seller.save()

		publicacion = Publicacion.objects.create(
			titulo="Bandeja paisa",
			descripcion="Con todo",
			stock=10,
			maximo_por_venta=5,
			precio=25000,
			usuario=seller,
		)
		Pedido.objects.create(
			telefono="3000000000",
			total=25000,
			publicacion=publicacion,
			usuario=self.user,
			estado="PENDIENTE",
		)

		response = self.client.delete(
			"/api/me",
			data=json.dumps({"password": "secret12345"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 409)
		self.assertTrue(User.objects.filter(id=self.user.id).exists())

	def test_delete_blocked_by_active_order_on_own_publication(self):
		from market.infrastructure.models import Pedido, Publicacion

		buyer = User(username="comprador@example.com", email="comprador@example.com", nombre="Comprador")
		buyer.set_password("secret12345")
		buyer.save()

		publicacion = Publicacion.objects.create(
			titulo="Bandeja paisa",
			descripcion="Con todo",
			stock=10,
			maximo_por_venta=5,
			precio=25000,
			usuario=self.user,
		)
		Pedido.objects.create(
			telefono="3000000000",
			total=25000,
			publicacion=publicacion,
			usuario=buyer,
			estado="PENDIENTE",
		)

		response = self.client.delete(
			"/api/me",
			data=json.dumps({"password": "secret12345"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 409)
		self.assertTrue(User.objects.filter(id=self.user.id).exists())

	def test_delete_blocked_by_active_delivery_assignment(self):
		from delivery.infrastructure.models import Asignacion
		from market.infrastructure.models import Pedido, Publicacion

		seller = User(username="vendedor2@example.com", email="vendedor2@example.com", nombre="Vendedor")
		seller.set_password("secret12345")
		seller.save()
		buyer = User(username="comprador2@example.com", email="comprador2@example.com", nombre="Comprador")
		buyer.set_password("secret12345")
		buyer.save()

		publicacion = Publicacion.objects.create(
			titulo="Bandeja paisa",
			descripcion="Con todo",
			stock=10,
			maximo_por_venta=5,
			precio=25000,
			usuario=seller,
		)
		pedido = Pedido.objects.create(
			telefono="3000000000",
			total=25000,
			publicacion=publicacion,
			usuario=buyer,
			estado="ACEPTADO",
		)
		Asignacion.objects.create(pedido=pedido, repartidor=self.user, estado="ASIGNADO")

		response = self.client.delete(
			"/api/me",
			data=json.dumps({"password": "secret12345"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 409)
		self.assertTrue(User.objects.filter(id=self.user.id).exists())

	def test_delete_allowed_once_orders_are_delivered(self):
		from market.infrastructure.models import Pedido, Publicacion

		seller = User(username="vendedor3@example.com", email="vendedor3@example.com", nombre="Vendedor")
		seller.set_password("secret12345")
		seller.save()

		publicacion = Publicacion.objects.create(
			titulo="Bandeja paisa",
			descripcion="Con todo",
			stock=10,
			maximo_por_venta=5,
			precio=25000,
			usuario=seller,
		)
		Pedido.objects.create(
			telefono="3000000000",
			total=25000,
			publicacion=publicacion,
			usuario=self.user,
			estado="ENTREGADO",
		)

		response = self.client.delete(
			"/api/me",
			data=json.dumps({"password": "secret12345"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 204)
		self.assertFalse(User.objects.filter(id=self.user.id).exists())


class DataExportAPITests(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.user = User(username="exportar@example.com", email="exportar@example.com", nombre="Exportar Datos")
		self.user.set_password("secret12345")
		self.user.save()

		access = str(RefreshToken.for_user(self.user).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_export_requires_authentication(self):
		anon = APIClient()
		response = anon.get("/api/me/exportar")

		self.assertEqual(response.status_code, 401)

	def test_export_includes_profile_and_related_data(self):
		from market.infrastructure.models import Publicacion

		DireccionGuardada.objects.create(
			usuario=self.user,
			nombre="Casa",
			direccion_texto="Calle 1",
			latitud=6.2,
			longitud=-75.5,
		)
		Publicacion.objects.create(
			titulo="Bandeja paisa",
			descripcion="Con todo",
			stock=10,
			maximo_por_venta=5,
			precio=25000,
			usuario=self.user,
		)

		response = self.client.get("/api/me/exportar")

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertEqual(data["perfil"]["email"], self.user.email)
		self.assertEqual(len(data["direcciones_guardadas"]), 1)
		self.assertEqual(len(data["publicaciones"]), 1)
		self.assertIsNone(data["repartidor_perfil"])
		self.assertEqual(data["asignaciones_como_repartidor"], [])

	def test_export_includes_repartidor_data(self):
		from delivery.infrastructure.models import Asignacion, RepartidorPerfil
		from market.infrastructure.models import Pedido, Publicacion

		self.user.es_repartidor = True
		self.user.save(update_fields=["es_repartidor"])
		RepartidorPerfil.objects.create(usuario=self.user, activo=True)

		seller = User(username="exp_seller@example.com", email="exp_seller@example.com", nombre="Seller")
		seller.set_password("secret12345")
		seller.save()
		buyer = User(username="exp_buyer@example.com", email="exp_buyer@example.com", nombre="Buyer")
		buyer.set_password("secret12345")
		buyer.save()

		publicacion = Publicacion.objects.create(
			titulo="Bandeja paisa", descripcion="Con todo",
			stock=10, maximo_por_venta=5, precio=25000, usuario=seller,
		)
		pedido = Pedido.objects.create(
			telefono="3000000000", total=25000, publicacion=publicacion, usuario=buyer, estado="ACEPTADO",
		)
		Asignacion.objects.create(pedido=pedido, repartidor=self.user, estado="ASIGNADO")

		response = self.client.get("/api/me/exportar")

		self.assertEqual(response.status_code, 200)
		data = response.json()
		self.assertIsNotNone(data["repartidor_perfil"])
		self.assertTrue(data["repartidor_perfil"]["activo"])
		self.assertEqual(len(data["asignaciones_como_repartidor"]), 1)


class RegisterTests(TestCase):
	def setUp(self):
		cache.clear()

	def test_register_creates_user_ready_for_login(self):
		payload = {
			"nombre": "Nuevo Usuario",
			"email": "nuevo@example.com",
			"password": "secret12345",
		}

		response = self.client.post(
			"/api/registro",
			data=json.dumps(payload),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 201)
		user = User.objects.get(email="nuevo@example.com")
		self.assertEqual(user.nombre, "Nuevo Usuario")
		login_response = self.client.post(
			"/api/login",
			data=json.dumps({"email": user.email, "password": "secret12345"}),
			content_type="application/json",
		)
		self.assertEqual(login_response.status_code, 200)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetTests(TestCase):
	def setUp(self):
		cache.clear()
		self.user = User(username="reset@example.com", email="reset@example.com", nombre="Reset User")
		self.user.set_password("secret12345")
		self.user.save()

	def test_password_reset_request_sends_email(self):
		response = self.client.post(
			"/api/password-reset",
			data=json.dumps({"email": self.user.email}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn("/ui/restablecer-password/", mail.outbox[0].body)

	def test_password_reset_confirm_updates_password(self):
		uid = urlsafe_base64_encode(force_bytes(self.user.pk))
		token = default_token_generator.make_token(self.user)

		response = self.client.post(
			"/api/password-reset/confirm",
			data=json.dumps({
				"uid": uid,
				"token": token,
				"password": "nuevaClave123",
			}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 200)
		login_response = self.client.post(
			"/api/login",
			data=json.dumps({"email": self.user.email, "password": "nuevaClave123"}),
			content_type="application/json",
		)
		self.assertEqual(login_response.status_code, 200)


class AuthThrottlingTests(TestCase):
	"""El scope 'auth' (10/min) es compartido por login/registro/refresh/reset
	de password. Se usa un REMOTE_ADDR dedicado y se limpia el cache antes y
	despues para que este test no dependa del orden de ejecucion ni quede
	interferido por otros tests que tambien pegan a endpoints con scope 'auth'."""

	def setUp(self):
		cache.clear()
		self.email = "throttle_test@example.com"
		self.password = "secret12345"
		User.objects.filter(email=self.email).delete()
		user = User(username=self.email, email=self.email, nombre="Throttle Test")
		user.set_password(self.password)
		user.save()

	def tearDown(self):
		cache.clear()

	def _login_attempt(self):
		return self.client.post(
			"/api/login",
			data=json.dumps({"email": self.email, "password": "wrong-password"}),
			content_type="application/json",
			REMOTE_ADDR="203.0.113.5",
		)

	def test_11th_auth_request_within_a_minute_is_throttled(self):
		for _ in range(10):
			response = self._login_attempt()
			self.assertNotEqual(response.status_code, 429)

		response = self._login_attempt()
		self.assertEqual(response.status_code, 429)

	def test_throttle_scope_is_shared_across_auth_endpoints(self):
		for _ in range(10):
			self._login_attempt()

		response = self.client.post(
			"/api/registro",
			data=json.dumps({
				"nombre": "Otro",
				"email": "otro_throttle@example.com",
				"password": "secret12345",
			}),
			content_type="application/json",
			REMOTE_ADDR="203.0.113.5",
		)
		self.assertEqual(response.status_code, 429)


class RegisterErrorPathTests(TestCase):
	def setUp(self):
		cache.clear()

	def test_duplicate_email_returns_409(self):
		existing = User(username="dup@example.com", email="dup@example.com", nombre="Existing")
		existing.set_password("secret12345")
		existing.save()

		response = self.client.post(
			"/api/registro",
			data=json.dumps({"nombre": "Nuevo", "email": "dup@example.com", "password": "secret12345"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 409)

	def test_password_failing_django_validators_returns_400(self):
		response = self.client.post(
			"/api/registro",
			data=json.dumps({"nombre": "Nuevo", "email": "numeric_pw@example.com", "password": "123456"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertFalse(User.objects.filter(email="numeric_pw@example.com").exists())

	def test_blank_nombre_after_strip_returns_400(self):
		response = self.client.post(
			"/api/registro",
			data=json.dumps({"nombre": "   ", "email": "blanknombre@example.com", "password": "secret12345"}),
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 400)

	def test_repartidor_tipo_cuenta_sets_flag(self):
		response = self.client.post(
			"/api/registro",
			data=json.dumps({
				"nombre": "Repartidor Nuevo",
				"email": "nuevo_repartidor@example.com",
				"password": "secret12345",
				"tipo_cuenta": "repartidor",
			}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 201)
		user = User.objects.get(email="nuevo_repartidor@example.com")
		self.assertTrue(user.es_repartidor)


class PasswordResetConfirmErrorPathTests(TestCase):
	def setUp(self):
		cache.clear()
		self.user = User(username="reset_err@example.com", email="reset_err@example.com", nombre="Reset Err")
		self.user.set_password("secret12345")
		self.user.save()

	def test_invalid_token_returns_400(self):
		uid = urlsafe_base64_encode(force_bytes(self.user.pk))

		response = self.client.post(
			"/api/password-reset/confirm",
			data=json.dumps({"uid": uid, "token": "token-invalido", "password": "nuevaClave123"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 400)

	def test_malformed_uid_returns_400(self):
		response = self.client.post(
			"/api/password-reset/confirm",
			data=json.dumps({"uid": "no-es-base64!!", "token": "cualquiera", "password": "nuevaClave123"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 400)

	def test_password_failing_django_validators_returns_400(self):
		uid = urlsafe_base64_encode(force_bytes(self.user.pk))
		token = default_token_generator.make_token(self.user)

		response = self.client.post(
			"/api/password-reset/confirm",
			data=json.dumps({"uid": uid, "token": token, "password": "123456"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 400)


class DireccionGuardadaAPITests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.user = User(username="direcciones@example.com", email="direcciones@example.com", nombre="Direcciones")
		self.user.set_password("secret12345")
		self.user.save()
		access = str(RefreshToken.for_user(self.user).access_token)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def _payload(self, **overrides):
		payload = {
			"nombre": "Casa", "direccion_texto": "Calle 1", "detalles": "Apto 1",
			"latitud": "4.65", "longitud": "-74.08", "es_predeterminada": False,
		}
		payload.update(overrides)
		return payload

	def test_requires_authentication(self):
		anon = APIClient()
		response = anon.get("/api/direcciones")
		self.assertEqual(response.status_code, 401)

	def test_list_own_direcciones(self):
		self.client.post("/api/direcciones", self._payload(nombre="Casa"), format="json")

		response = self.client.get("/api/direcciones")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.json()), 1)

	def test_create_direccion(self):
		response = self.client.post("/api/direcciones", self._payload(), format="json")

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()["nombre"], "Casa")

	def test_creating_predeterminada_unsets_previous_default(self):
		self.client.post("/api/direcciones", self._payload(nombre="Casa", es_predeterminada=True), format="json")

		response = self.client.post(
			"/api/direcciones", self._payload(nombre="Oficina", es_predeterminada=True), format="json"
		)

		self.assertEqual(response.status_code, 201)
		casa = DireccionGuardada.objects.get(nombre="Casa")
		oficina = DireccionGuardada.objects.get(nombre="Oficina")
		self.assertFalse(casa.es_predeterminada)
		self.assertTrue(oficina.es_predeterminada)

	def test_patch_updates_fields(self):
		create_response = self.client.post("/api/direcciones", self._payload(), format="json")
		direccion_id = create_response.json()["id"]

		response = self.client.patch(
			f"/api/direcciones/{direccion_id}", {"nombre": "Casa actualizada"}, format="json"
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["nombre"], "Casa actualizada")

	def test_patch_as_predeterminada_unsets_other_defaults(self):
		primera = self.client.post(
			"/api/direcciones", self._payload(nombre="Casa", es_predeterminada=True), format="json"
		).json()
		segunda = self.client.post(
			"/api/direcciones", self._payload(nombre="Oficina", es_predeterminada=False), format="json"
		).json()

		response = self.client.patch(
			f"/api/direcciones/{segunda['id']}", {"es_predeterminada": True}, format="json"
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(DireccionGuardada.objects.get(id=primera["id"]).es_predeterminada)
		self.assertTrue(DireccionGuardada.objects.get(id=segunda["id"]).es_predeterminada)

	def test_patch_not_found_returns_404(self):
		response = self.client.patch("/api/direcciones/999999", {"nombre": "X"}, format="json")
		self.assertEqual(response.status_code, 404)

	def test_patch_other_users_direccion_not_found(self):
		other = User(username="other_dir@example.com", email="other_dir@example.com", nombre="Other")
		other.set_password("secret12345")
		other.save()
		other_access = str(RefreshToken.for_user(other).access_token)
		other_client = APIClient()
		other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {other_access}")
		direccion_id = self.client.post("/api/direcciones", self._payload(), format="json").json()["id"]

		response = other_client.patch(f"/api/direcciones/{direccion_id}", {"nombre": "X"}, format="json")

		self.assertEqual(response.status_code, 404)

	def test_delete_success(self):
		direccion_id = self.client.post("/api/direcciones", self._payload(), format="json").json()["id"]

		response = self.client.delete(f"/api/direcciones/{direccion_id}")

		self.assertEqual(response.status_code, 204)
		self.assertFalse(DireccionGuardada.objects.filter(id=direccion_id).exists())

	def test_delete_not_found_returns_404(self):
		response = self.client.delete("/api/direcciones/999999")
		self.assertEqual(response.status_code, 404)


class AccountModelsTests(TestCase):
	def test_user_str_falls_back_to_username_or_email(self):
		user = User(username="strtest@example.com", email="strtest@example.com", nombre="Str")
		self.assertEqual(str(user), "strtest@example.com")

	def test_direccion_guardada_str_includes_nombre_and_usuario(self):
		user = User(username="dirstr@example.com", email="dirstr@example.com", nombre="Dir")
		user.set_password("secret12345")
		user.save()
		direccion = DireccionGuardada.objects.create(
			usuario=user, nombre="Casa", direccion_texto="Calle 1", latitud="4.6", longitud="-74.0",
		)
		self.assertIn("Casa", str(direccion))
		self.assertIn(str(user.id), str(direccion))


class AccountPolicyServiceDirectTests(TestCase):
	def test_normalize_email_requires_non_blank(self):
		with self.assertRaises(ValidationError):
			AccountPolicyService.normalize_email("   ")

	def test_normalize_name_requires_non_blank(self):
		with self.assertRaises(ValidationError):
			AccountPolicyService.normalize_name("   ")

	def test_build_reset_link_appends_query_params(self):
		link_sin_query = AccountPolicyService.build_reset_link(
			reset_url_base="https://example.com/reset", uid="u1", token="t1"
		)
		self.assertEqual(link_sin_query, "https://example.com/reset?uid=u1&token=t1")

		link_con_query = AccountPolicyService.build_reset_link(
			reset_url_base="https://example.com/reset?lang=es", uid="u1", token="t1"
		)
		self.assertEqual(link_con_query, "https://example.com/reset?lang=es&uid=u1&token=t1")


class LoginUserUseCaseDirectTests(TestCase):
	def test_inactive_user_raises_authentication_error(self):
		inactive_user = MagicMock(is_active=False)
		auth_service = MagicMock()
		auth_service.authenticate_user.return_value = inactive_user

		use_case = LoginUserUseCase(auth_service=auth_service)
		with self.assertRaises(AuthenticationError):
			use_case.execute(email="inactivo@example.com", password="secret12345")


class RegisterUserUseCaseDirectTests(TestCase):
	def test_integrity_error_race_condition_becomes_conflict_error(self):
		from django.db import IntegrityError

		repo = MagicMock()
		repo.exists_by_email.return_value = False
		repo.create_user.side_effect = IntegrityError("duplicate key")

		use_case = RegisterUserUseCase(user_repository=repo)
		with self.assertRaises(ConflictError):
			use_case.execute(nombre="Carrera", email="race@example.com", password="secret12345")


class ResetPasswordUseCaseDirectTests(TestCase):
	def test_incomplete_data_raises_validation_error(self):
		use_case = ResetPasswordUseCase(user_repository=MagicMock(), auth_service=MagicMock())
		with self.assertRaises(ValidationError):
			use_case.execute(uid="", token="t", password="secret12345")


class PasswordResetRequestUnknownEmailTests(TestCase):
	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_unknown_email_still_returns_200_without_sending_mail(self):
		cache.clear()
		response = self.client.post(
			"/api/password-reset",
			data=json.dumps({"email": "no-existe@example.com"}),
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(mail.outbox), 0)


class PasswordResetRequestViewErrorWiringTests(TestCase):
	def test_translates_domain_validation_error(self):
		from unittest.mock import patch

		cache.clear()
		with patch(
			"accounts.interfaces.api.views.RequestPasswordResetUseCase.execute",
			side_effect=ValidationError("email invalido"),
		):
			response = self.client.post(
				"/api/password-reset",
				data=json.dumps({"email": "cualquiera@example.com"}),
				content_type="application/json",
			)
		self.assertEqual(response.status_code, 400)


class PasswordResetConfirmUnknownUserTests(TestCase):
	def test_uid_for_nonexistent_user_returns_400(self):
		cache.clear()
		uid = urlsafe_base64_encode(force_bytes(999999))

		response = self.client.post(
			"/api/password-reset/confirm",
			data=json.dumps({"uid": uid, "token": "cualquiera", "password": "nuevaClave123"}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 400)

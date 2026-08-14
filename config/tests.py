from django.test import TestCase


class UiPageRenderTests(TestCase):
    """Cada vista `/ui/*` solo hace `render(request, "<template>.html")`; estos
    tests confirman que las 16 paginas cargan en 200 con el template correcto,
    lo que de paso ejercita los context processors (google_maps,
    courier_tracking) que corren en cada render."""

    pages = [
        ("/", "index.html"),
        ("/ui/registro/", "registro.html"),
        ("/ui/login/", "login.html"),
        ("/ui/recuperar-password/", "recuperar_password.html"),
        ("/ui/restablecer-password/", "restablecer_password.html"),
        ("/ui/publicar/", "publicar.html"),
        ("/ui/perfil/", "perfil.html"),
        ("/ui/pedido/", "pedido.html"),
        ("/ui/carrito/", "carrito.html"),
        ("/ui/checkout/", "checkout.html"),
        ("/ui/seguimiento/", "seguimiento.html"),
        ("/ui/pago/", "pago.html"),
        ("/ui/aceptar-pedido/", "aceptar_pedido.html"),
        ("/ui/notificaciones/", "notificaciones.html"),
        ("/ui/repartidor/", "repartidor_pedidos.html"),
        ("/ui/repartidor/entrega/", "repartidor_entrega.html"),
        ("/ui/repartidor/perfil/", "repartidor_perfil.html"),
    ]

    def test_all_ui_pages_render_with_expected_template(self):
        for url, template_name in self.pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template_name)

    def test_context_processors_expose_expected_keys(self):
        response = self.client.get("/")
        self.assertIn("GOOGLE_MAPS_API_KEY", response.context)
        self.assertIn("SIMULATE_COURIER_TRACKING", response.context)

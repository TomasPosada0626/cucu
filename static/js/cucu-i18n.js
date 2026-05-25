(function () {
  "use strict";

  var STORAGE_KEY = "cucu_lang";
  var COOKIE_KEY = "django_language";
  var SUPPORTED = ["es", "en"];

  var ES_TO_EN = {
    "Navegacion principal": "Main navigation",
    "Iniciar sesion": "Sign in",
    "Inicia sesion": "Sign in",
    "Eres nuevo en CUCU?": "New to CUCU?",
    "Bienvenido a CUCU": "Welcome to CUCU",
    "Crea tu cuenta": "Create your account",
    "Unete a CUCU hoy mismo": "Join CUCU today",
    "Correo electronico": "Email",
    "Contrasena": "Password",
    "Confirma tu contrasena": "Confirm your password",
    "Mostrar u ocultar contrasena": "Show or hide password",
    "Mostrar u ocultar confirmacion de contrasena": "Show or hide password confirmation",
    "Olvidaste tu contrasena?": "Forgot your password?",
    "Recuerdame": "Remember me",
    "No tienes cuenta?": "Don't have an account?",
    "Registrate": "Sign up",
    "o": "or",
    "Continuar con Google": "Continue with Google",
    "Terminos": "Terms",
    "Privacidad": "Privacy",
    "Ayuda": "Help",
    "CUCU": "CUCU",
    "Crear cuenta": "Create account",
    "Registrate en CUCU": "Sign up for CUCU",
    "Nombre": "Name",
    "Ya tienes cuenta?": "Already have an account?",
    "Inicia sesion aqui": "Sign in here",
    "Recuperar contrasena": "Recover password",
    "Recupera tu acceso": "Recover access",
    "Escribe tu correo y te enviaremos un enlace para cambiar la contrasena.": "Enter your email and we will send you a link to change your password.",
    "Enviar enlace": "Send link",
    "Volver al login": "Back to login",
    "Te ayudamos a recuperar tu cuenta": "We help you recover your account",
    "Enviar codigo": "Send code",
    "Restablecer contrasena": "Reset password",
    "Nueva contrasena": "New password",
    "Guardar contrasena": "Save password",
    "Ingresa una contrasena nueva para recuperar tu cuenta.": "Enter a new password to recover your account.",
    "Confirmar contrasena": "Confirm password",
    "Guardar": "Save",
    "Inicio": "Home",
    "Compra": "Buy",
    "Vende": "Sell",
    "Publicar": "Publish",
    "Perfil": "Profile",
    "Pedido": "Order",
    "Carrito": "Cart",
    "Checkout": "Checkout",
    "Seguimiento": "Tracking",
    "Pago": "Payment",
    "Notificaciones": "Notifications",
    "Aceptar pedido": "Accept order",
    "Cerrar sesion": "Log out",
    "Buscar": "Search",
    "Editar": "Edit",
    "Eliminar": "Delete",
    "Guardar cambios": "Save changes",
    "Cancelar": "Cancel",
    "Confirmar": "Confirm",
    "Direccion": "Address",
    "Ciudad": "City",
    "Telefono": "Phone",
    "Total": "Total",
    "Cantidad": "Quantity",
    "Estado": "Status",
    "Pendiente": "Pending",
    "Completado": "Completed",
    "Pagado": "Paid",
    "Usuario": "User",
    "Cerrar": "Close",
    "Ver mas": "See more",
    "Volver": "Back",
    "Hola": "Hello",
    "Publicaciones": "Publications",
    "Pedidos": "Orders",
    "Actualizar": "Update",
    "Enviar": "Send",
    "Contraseña": "Password",
    "Correo electrónico": "Email",
    "Iniciar sesión": "Sign in",
    "Regístrate": "Sign up",
    "Nombre completo": "Full name",
    "Ilustracion de registro": "Registration illustration",
    "¿Olvidaste tu contraseña?": "Forgot your password?",
    "Recuérdame": "Remember me",
    "¿No tienes cuenta?": "Don't have an account?",
    "Términos": "Terms",
    "Al registrarte, aceptas nuestros": "By signing up, you accept our",
    "Terminos y Condiciones": "Terms and Conditions",
    "Ilustracion de inicio de sesion": "Sign-in illustration",
    "Ilustración de inicio de sesión": "Sign-in illustration",
    "Todos los derechos reservados.": "All rights reserved.",
    "Procesando...": "Processing...",
    "Las contraseñas no coinciden": "Passwords do not match",
    "Las contrasenas no coinciden": "Passwords do not match",
    "Ilustración": "Illustration",
    "Recuperar password": "Recover password",
    "Restablecer password": "Reset password",

    "Filtrar por": "Filter by",
    "Mexicana": "Mexican",
    "Italiana": "Italian",
    "Saludable": "Healthy",
    "Postres": "Desserts",
    "Minimo": "Minimum",
    "Mínimo": "Minimum",
    "Maximo": "Maximum",
    "Máximo": "Maximum",
    "Rango de precio": "Price range",
    "Rango actual": "Current range",
    "Distancia": "Distance",
    "Radio maximo": "Maximum radius",
    "Radio máximo": "Maximum radius",
    "Tiempo de entrega": "Delivery time",
    "Disponible ahora": "Available now",
    "Agregar al carrito": "Add to cart",
    "Agregado": "Added",
    "Agregar": "Add",
    "Agotado": "Sold out",
    "Mostrando platos alrededor de tu ubicacion actual.": "Showing dishes around your current location.",
    "Mostrando platos alrededor de tu ubicación actual.": "Showing dishes around your current location.",

    "Publicar un platillo": "Publish a dish",
    "Como ubicar tu punto de venta": "How to set your selling point",
    "Cómo ubicar tu punto de venta": "How to set your selling point",
    "Ubicacion del punto de entrega": "Delivery point location",
    "Ubicación del punto de entrega": "Delivery point location",
    "Ubicar direccion": "Locate address",
    "Ubicar dirección": "Locate address",
    "Usar mi ubicacion": "Use my location",
    "Usar mi ubicación": "Use my location",
    "Imagen del platillo": "Dish image",
    "Anadir imagen": "Add image",
    "Añadir imagen": "Add image",
    "Nombre del platillo": "Dish name",
    "Stock disponible": "Available stock",
    "Maximo permitido por venta": "Maximum per order",
    "Máximo permitido por venta": "Maximum per order",
    "Tipo de comida": "Food type",
    "Ingredientes incluidos": "Included ingredients",
    "Anadir ingrediente": "Add ingredient",
    "Añadir ingrediente": "Add ingredient",
    "Preparacion": "Preparation",
    "Preparación": "Preparation",

    "Mi perfil": "My profile",
    "Mi perfil | CUCU": "My profile | CUCU",
    "Mi perfil": "My profile",
    "Miembro desde": "Member since",
    "Mis pedidos": "My orders",
    "Mis publicaciones": "My listings",
    "Historial de pedidos": "Order history",
    "Detalle del pedido": "Order details",
    "Consulta tu historial de pedidos, administra tus publicaciones y revisa el saldo de tus ventas desde un solo lugar.": "Check your order history, manage your listings, and review your sales balance from one place.",
    "Revisa tus platos publicados desde una vista simple. Si necesitas cambiar algo, abre el detalle.": "Review your published dishes from a simple view. If you need to change something, open the details.",
    "Saldo de ventas": "Sales balance",
    "Balance acumulado a partir de las ventas registradas de tus platos.": "Accumulated balance based on your dishes' recorded sales.",
    "Todavia no tienes pedidos registrados.": "You do not have any registered orders yet.",
    "Todavía no tienes pedidos registrados.": "You do not have any registered orders yet.",
    "Cuando hagas tu primer pedido, aqui veras toda la informacion.": "When you place your first order, you will see all the information here.",
    "Cuando hagas tu primer pedido, aquí verás toda la información.": "When you place your first order, you will see all the information here.",
    "Todavia no has publicado platos. Cuando publiques uno, aqui podras editar su stock, ingredientes, valor y la informacion del menu.": "You have not published any dishes yet. When you publish one, you will be able to edit its stock, ingredients, price, and menu information here.",
    "Todavía no has publicado platos. Cuando publiques uno, aquí podrás editar su stock, ingredientes, valor y la información del menú.": "You have not published any dishes yet. When you publish one, you will be able to edit its stock, ingredients, price, and menu information here.",
    "No se pudo cargar el perfil.": "Could not load profile.",
    "Foto de perfil": "Profile picture",
    "Secciones del perfil": "Profile sections",
    "Compras": "Purchases",
    "Ventas": "Sales",
    "Platos": "Dishes",
    "Log out": "Log out",

    "Compra": "Buy",
    "cerca.": "local.",
    "Vende fresco.": "Sell fresh.",
    "Mueve tu barrio con CUCU.": "Move your neighborhood with CUCU.",
    "Descubre comida casera hecha con amor o vende tus platos en minutos.": "Discover homemade food made with love or sell your dishes in minutes.",
    "Rapido": "Fast",
    "Rápido": "Fast",
    "Sin costos escondidos": "No hidden fees",
    "En tu barrio": "In your neighborhood",
    "Como funciona?": "How does it work?",
    "¿Cómo funciona?": "How does it work?",
    "Busca comida cerca": "Find nearby food",
    "Explora platos caseros en tu zona.": "Explore homemade dishes in your area.",
    "Compra o vende": "Buy or sell",
    "Elige, paga y recibe. O publica tus platos.": "Choose, pay, and receive. Or publish your dishes.",
    "Conecta con tu comunidad de forma simple.": "Connect with your community in a simple way.",
    "Listo en minutos": "Ready in minutes",
    "Explorar comida": "Explore food",
    "Vender comida": "Sell food",
    "Quiero comprar": "I want to buy",
    "Explora platos por ubicacion": "Explore dishes by location",
    "Explora platos por ubicación": "Explore dishes by location",
    "Filtra por precio y categoria": "Filter by price and category",
    "Filtra por precio y categoría": "Filter by price and category",
    "Compra de forma segura": "Buy safely",
    "Explorar ahora →": "Explore now →",
    "Quiero vender": "I want to sell",
    "Publica tus platos en minutos": "Publish your dishes in minutes",
    "Gestiona pedidos facilmente": "Manage orders easily",
    "Gestiona pedidos fácilmente": "Manage orders easily",
    "Llega a mas clientes del barrio": "Reach more neighborhood customers",
    "Llega a más clientes del barrio": "Reach more neighborhood customers",
    "Empieza a vender →": "Start selling →",
    "Unete a CUCU y mueve tu barrio": "Join CUCU and move your neighborhood",
    "Únete a CUCU y mueve tu barrio": "Join CUCU and move your neighborhood",
    "Registrate gratis y empieza a comprar o vender hoy mismo.": "Sign up for free and start buying or selling today.",
    "Regístrate gratis y empieza a comprar o vender hoy mismo.": "Sign up for free and start buying or selling today.",
    "Crear cuenta gratis": "Create free account",
    "Hecho para tu barrio, hecho con amor.": "Made for your neighborhood, made with love.",
    "Explorar": "Explore",
    "Menu": "Menu",
    "Menú": "Menu",
    "Comunidad": "Community",
    "Como funciona": "How it works",
    "Cómo funciona": "How it works",
    "Vender": "Sell",
    "Publicar plato": "Publish dish",
    "Mis ventas": "My sales",
    "Soporte": "Support",
    "Legal": "Legal",
    "Contacto": "Contact",
    "Siguenos": "Follow us",
    "Síguenos": "Follow us",
    "Plato casero de CUCU": "Homemade CUCU dish",
    "Preparacion de comida casera para vender en CUCU": "Homemade food preparation to sell on CUCU",
    "Preparación de comida casera para vender en CUCU": "Homemade food preparation to sell on CUCU",

    "Tu pedido sigue en camino": "Your order is still on the way",
    "Puedes volver al seguimiento en cualquier momento hasta que la entrega termine.": "You can return to tracking at any time until delivery is complete.",
    "Pedido activo": "Active order",
    "Seguir mi pedido": "Track my order"
  };

  var ES_FRAGMENT_TO_EN = {
    "Miembro desde ": "Member since ",
    "Aún no has agregado ingredientes.": "You have not added ingredients yet.",
    "Aun no has agregado ingredientes.": "You have not added ingredients yet.",
    "Ajusta el pin o escribe una dirección exacta": "Adjust the pin or type an exact address",
    "Ajusta el pin o escribe una direccion exacta": "Adjust the pin or type an exact address",
    "Todos los derechos reservados.": "All rights reserved."
  };

  var EN_TO_ES = {};
  Object.keys(ES_TO_EN).forEach(function (esText) {
    var enText = ES_TO_EN[esText];
    if (!(enText in EN_TO_ES)) {
      EN_TO_ES[enText] = esText;
    }
  });

  var EN_FRAGMENT_TO_ES = {};
  Object.keys(ES_FRAGMENT_TO_EN).forEach(function (esFragment) {
    var enFragment = ES_FRAGMENT_TO_EN[esFragment];
    if (!(enFragment in EN_FRAGMENT_TO_ES)) {
      EN_FRAGMENT_TO_ES[enFragment] = esFragment;
    }
  });

  function normalizeText(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function removeAccents(value) {
    return normalizeText(value)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function preserveWhitespace(original, translated) {
    var source = String(original || "");
    var target = String(translated || "");
    var leading = source.match(/^\s*/);
    var trailing = source.match(/\s*$/);
    return (leading ? leading[0] : "") + target + (trailing ? trailing[0] : "");
  }

  function applyFragmentTranslations(text, lang) {
    var out = String(text || "");
    var fragmentMap = lang === "en" ? ES_FRAGMENT_TO_EN : EN_FRAGMENT_TO_ES;
    var keys = Object.keys(fragmentMap);
    for (var i = 0; i < keys.length; i += 1) {
      var key = keys[i];
      if (out.indexOf(key) !== -1) {
        out = out.split(key).join(fragmentMap[key]);
      }
    }
    return out;
  }

  function dictionaryLookup(text, lang) {
    var normalized = normalizeText(text);
    if (!normalized) {
      return text;
    }

    var directMap = lang === "en" ? ES_TO_EN : EN_TO_ES;
    if (directMap[normalized]) {
      return preserveWhitespace(text, directMap[normalized]);
    }

    var plain = removeAccents(normalized);
    var keys = Object.keys(directMap);
    for (var i = 0; i < keys.length; i += 1) {
      if (removeAccents(keys[i]) === plain) {
        return preserveWhitespace(text, directMap[keys[i]]);
      }
    }

    var fragmentTranslated = applyFragmentTranslations(text, lang);
    if (fragmentTranslated !== text) {
      return preserveWhitespace(text, fragmentTranslated);
    }

    return text;
  }

  function translateTextNode(node, lang) {
    if (!node || !node.nodeValue) {
      return;
    }

    var original = node.__cucuOriginalText;
    if (!original) {
      original = node.nodeValue;
      node.__cucuOriginalText = original;
    }

    var translated = dictionaryLookup(original, lang);
    if (translated !== node.nodeValue) {
      node.nodeValue = translated;
    }
  }

  function translateElementAttributes(element, lang) {
    ["placeholder", "title", "aria-label", "alt", "value"].forEach(function (attr) {
      if (!element.hasAttribute(attr)) {
        return;
      }

      var key = "__cucuOriginalAttr_" + attr;
      var original = element[key] || element.getAttribute(attr);
      element[key] = original;

      var translated = dictionaryLookup(original, lang);
      if (translated !== element.getAttribute(attr)) {
        element.setAttribute(attr, translated);
      }
    });
  }

  function shouldSkipNode(node) {
    var parent = node.parentElement;
    if (!parent) {
      return true;
    }

    var tag = parent.tagName;
    return tag === "SCRIPT" || tag === "STYLE" || tag === "NOSCRIPT" || tag === "IFRAME";
  }

  function applyLanguage(lang) {
    if (SUPPORTED.indexOf(lang) === -1) {
      lang = "es";
    }

    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) {
      if (shouldSkipNode(node)) {
        continue;
      }
      if (!normalizeText(node.nodeValue)) {
        continue;
      }
      translateTextNode(node, lang);
    }

    var nodes = document.querySelectorAll("[placeholder], [title], [aria-label], [alt], input[value], button[value]");
    for (var i = 0; i < nodes.length; i += 1) {
      translateElementAttributes(nodes[i], lang);
    }

    document.documentElement.setAttribute("lang", lang);
    markSwitcher(lang);
  }

  function setCookie(name, value, days) {
    var maxAge = days * 24 * 60 * 60;
    document.cookie = name + "=" + encodeURIComponent(value) + ";path=/;max-age=" + maxAge + ";SameSite=Lax";
  }

  function getCookie(name) {
    var parts = document.cookie.split(";");
    for (var i = 0; i < parts.length; i += 1) {
      var item = parts[i].trim();
      if (item.indexOf(name + "=") === 0) {
        return decodeURIComponent(item.substring(name.length + 1));
      }
    }
    return "";
  }

  function getCurrentLanguage() {
    var stored = localStorage.getItem(STORAGE_KEY);
    if (SUPPORTED.indexOf(stored) !== -1) {
      return stored;
    }

    var cookieValue = getCookie(COOKIE_KEY);
    if (SUPPORTED.indexOf(cookieValue) !== -1) {
      return cookieValue;
    }

    return "es";
  }

  function saveLanguage(lang) {
    localStorage.setItem(STORAGE_KEY, lang);
    setCookie(COOKIE_KEY, lang, 365);
  }

  function markSwitcher(lang) {
    var root = document.getElementById("cucu-lang-switcher");
    if (!root) {
      return;
    }

    var buttons = root.querySelectorAll("button[data-lang]");
    for (var i = 0; i < buttons.length; i += 1) {
      var button = buttons[i];
      var selected = button.getAttribute("data-lang") === lang;
      button.setAttribute("aria-pressed", selected ? "true" : "false");
      button.classList.toggle("active", selected);
    }
  }

  function addSwitcherStyles() {
    if (document.getElementById("cucu-lang-switcher-style")) {
      return;
    }

    var style = document.createElement("style");
    style.id = "cucu-lang-switcher-style";
    style.textContent =
      "#cucu-lang-switcher{position:fixed;top:14px;right:14px;z-index:9999;display:inline-flex;align-items:center;gap:6px;padding:6px;border-radius:999px;background:rgba(255,255,255,.94);border:1px solid rgba(0,0,0,.09);box-shadow:0 10px 28px rgba(0,0,0,.11);font-family:Manrope,Arial,sans-serif}" +
      "#cucu-lang-switcher button{border:0;border-radius:999px;min-width:44px;height:32px;padding:0 10px;background:transparent;color:#334155;font-size:12px;font-weight:800;cursor:pointer}" +
      "#cucu-lang-switcher button.active{background:#ff6a1a;color:#fff}";
    document.head.appendChild(style);
  }

  function createSwitcher() {
    if (document.getElementById("cucu-lang-switcher")) {
      return;
    }

    addSwitcherStyles();

    var wrapper = document.createElement("div");
    wrapper.id = "cucu-lang-switcher";
    wrapper.setAttribute("role", "group");
    wrapper.setAttribute("aria-label", "Language selector");

    ["es", "en"].forEach(function (lang) {
      var button = document.createElement("button");
      button.type = "button";
      button.setAttribute("data-lang", lang);
      button.textContent = lang.toUpperCase();
      button.addEventListener("click", function () {
        saveLanguage(lang);
        applyLanguage(lang);
      });
      wrapper.appendChild(button);
    });

    document.body.appendChild(wrapper);
  }

  function bootstrap() {
    if (!document.body) {
      return;
    }

    createSwitcher();

    var selected = getCurrentLanguage();
    saveLanguage(selected);
    applyLanguage(selected);

    var observer = new MutationObserver(function () {
      applyLanguage(getCurrentLanguage());
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();

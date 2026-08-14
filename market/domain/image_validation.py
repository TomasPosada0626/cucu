from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB


def validate_publicacion_imagen(file) -> None:
    """Rechaza archivos que no sean una imagen raster real.

    Sin esto, `imagen` acepta cualquier archivo (un .svg con <script>, un
    .html, un .php) porque FileField solo valida que sea un archivo. nginx
    sirve /media/ directo sin forzar Content-Type, asi que un SVG malicioso
    subido como "imagen" se ejecutaria en el navegador de quien lo abra
    (XSS almacenado via upload). El content_type del cliente se puede
    falsificar, por eso Image.verify() es el chequeo real: solo un archivo
    que Pillow pueda decodificar como imagen pasa.
    """
    if file is None:
        return

    if file.size > MAX_IMAGE_SIZE_BYTES:
        raise DjangoValidationError("La imagen no puede superar 5MB")

    content_type = (getattr(file, "content_type", "") or "").lower()
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise DjangoValidationError("Formato de imagen no soportado. Usa JPG, PNG, WEBP o GIF")

    try:
        image = Image.open(file)
        image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise DjangoValidationError("El archivo no es una imagen valida") from exc
    finally:
        file.seek(0)

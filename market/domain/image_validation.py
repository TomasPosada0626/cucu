from __future__ import annotations

import io
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_DIMENSION_PX = 1600
THUMBNAIL_MAX_DIMENSION_PX = 480
COMPRESSION_QUALITY = 82

_SAVE_FORMAT_BY_CONTENT_TYPE = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


def validate_publicacion_imagen(file) -> None:
    """Rechaza archivos que no sean una imagen raster real, y redimensiona/
    recomprime la que sí lo es antes de guardarla.

    Sin el chequeo de formato, `imagen` acepta cualquier archivo (un .svg con
    <script>, un .html, un .php) porque FileField solo valida que sea un
    archivo. nginx sirve /media/ directo sin forzar Content-Type, asi que un
    SVG malicioso subido como "imagen" se ejecutaria en el navegador de quien
    lo abra (XSS almacenado via upload). El content_type del cliente se puede
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

    # GIF queda exento: podria ser animado, y una pasada de resize/recompresion
    # con Pillow aplana la animacion a un solo frame.
    if content_type != "image/gif":
        _resize_and_compress_in_place(file, content_type=content_type)


def _resize_and_compress_in_place(file, *, content_type: str) -> None:
    """Redimensiona (si el lado mas largo supera MAX_IMAGE_DIMENSION_PX) y
    recomprime la imagen ya validada arriba, reemplazando los bytes del
    archivo antes de que Django lo guarde. Tambien genera una miniatura
    (THUMBNAIL_MAX_DIMENSION_PX) y la deja en `file.imagen_thumb_content`
    para que el caller (create_publicacion) la use para poblar
    Publicacion.imagen_thumb - la miniatura es para grillas (catalogo,
    carrito), donde `srcset` ahorra banda real.

    Se corre despues de `image.verify()` en el caller - verify() invalida el
    objeto Image de Pillow para cualquier uso posterior, por eso esto reabre
    la imagen desde cero en vez de reutilizar la que ya se valido.
    """
    file.seek(0)
    original_size = file.size
    image: Image.Image = Image.open(file)

    save_format = _SAVE_FORMAT_BY_CONTENT_TYPE[content_type]
    save_kwargs: dict[str, Any] = {"optimize": True}
    if save_format in ("JPEG", "WEBP"):
        save_kwargs["quality"] = COMPRESSION_QUALITY
    if save_format == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    thumb = image.copy()
    thumb.thumbnail((THUMBNAIL_MAX_DIMENSION_PX, THUMBNAIL_MAX_DIMENSION_PX), Image.Resampling.LANCZOS)
    thumb_buffer = io.BytesIO()
    thumb.save(thumb_buffer, format=save_format, **save_kwargs)
    file.imagen_thumb_content = ContentFile(
        thumb_buffer.getvalue(), name=f"thumb.{save_format.lower()}"
    )

    if max(image.size) > MAX_IMAGE_DIMENSION_PX:
        image.thumbnail((MAX_IMAGE_DIMENSION_PX, MAX_IMAGE_DIMENSION_PX), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format=save_format, **save_kwargs)
    new_bytes = buffer.getvalue()

    if len(new_bytes) >= original_size:
        # No downgradear: una imagen ya muy comprimida y sin necesidad de
        # resize puede recodificar mas pesada que el original - en ese caso
        # se deja el archivo tal cual en vez de empeorarlo. La miniatura ya
        # generada arriba se conserva de todas formas.
        file.seek(0)
        return

    file.file = io.BytesIO(new_bytes)
    file.size = len(new_bytes)
    file.seek(0)

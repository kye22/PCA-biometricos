"""Lectura de fotos: acepta una ruta, los bytes de un archivo subido o un array ya cargado.

Se lee con Pillow (no con OpenCV) porque:
- detecta el formato por el contenido, no por la extensión (en el dataset hay un AVIF y un
  WebP con extensión .jpg),
- aplica la rotación EXIF de las fotos de móvil.
Se rechazan imágenes de más de MAX_PIXELES antes de descomprimirlas (una "bomba" de pocos KB
que ocupa gigas en memoria tumbaría el sistema).
"""
import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

MAX_PIXELES = 40_000_000


def leer(foto: "str | Path | bytes | np.ndarray") -> np.ndarray:
    """Devuelve la foto como array BGR uint8 (o tal cual si ya es un array)."""
    if isinstance(foto, np.ndarray):
        return foto
    origen = io.BytesIO(foto) if isinstance(foto, (bytes, bytearray)) else foto
    try:
        abierta = Image.open(origen)   # perezoso: aún no ha descomprimido nada
        if abierta.width * abierta.height > MAX_PIXELES:
            raise ValueError(f"imagen demasiado grande ({abierta.width}x{abierta.height})")
        img = ImageOps.exif_transpose(abierta).convert("RGB")
    except Exception as e:
        raise ValueError(f"No se puede leer la imagen: {foto if not isinstance(foto, bytes) else 'bytes'}") from e
    return np.ascontiguousarray(np.asarray(img)[:, :, ::-1])

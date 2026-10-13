"""Lectura de fotos: acepta una ruta o un array ya cargado."""
from pathlib import Path

import cv2
import numpy as np


def leer(foto: "str | Path | np.ndarray") -> np.ndarray:
    """Devuelve la foto como array (BGR o gris, tal cual venga)."""
    if isinstance(foto, np.ndarray):
        return foto
    # imdecode en vez de imread: imread falla con rutas con tildes en Windows
    datos = np.fromfile(str(foto), dtype=np.uint8)
    img = cv2.imdecode(datos, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"No se puede leer la imagen: {foto}")
    return img

"""Detector de caras. Responsable: módulo 1 (detector y preprocesado).

Provisional: Haar cascade de OpenCV, se queda con la cara más grande.
Pendiente: alineado por ojos, detector más robusto (DNN), márgenes.
"""
import cv2
import numpy as np

from .excepciones import CaraNoEncontrada

_cascada = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def detectar(foto: np.ndarray) -> np.ndarray:
    """Foto completa -> recorte de la cara (sin normalizar)."""
    gris = cv2.cvtColor(foto, cv2.COLOR_BGR2GRAY) if foto.ndim == 3 else foto
    caras = _cascada.detectMultiScale(gris, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(caras) == 0:
        raise CaraNoEncontrada("No se ha detectado ninguna cara")
    x, y, w, h = max(caras, key=lambda c: c[2] * c[3])
    return foto[y:y + h, x:x + w]

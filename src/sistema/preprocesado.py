"""Normalización de una cara ya recortada. Responsable: módulo 1 (detector y preprocesado).

Lo usan tanto el camino normal (después del detector) como los métodos _sd.
"""
import cv2
import numpy as np

from . import config


def normalizar(cara: np.ndarray) -> np.ndarray:
    """Cara recortada -> gris, TAM_CARA, ecualizada, float32 en [0, 1]."""
    if cara.ndim == 3:
        cara = cv2.cvtColor(cara, cv2.COLOR_BGR2GRAY)
    cara = cv2.resize(cara, config.TAM_CARA, interpolation=cv2.INTER_AREA)
    cara = cv2.equalizeHist(cara.astype(np.uint8))
    return cara.astype(np.float32) / 255.0

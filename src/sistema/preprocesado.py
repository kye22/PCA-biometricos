"""Normalización de una cara ya recortada. Responsable: módulo 1 (detector y preprocesado).

Lo usan todos los caminos (entrenamiento, inscripción, consulta y los métodos _sd), así que
todos los templates se calculan igual.

    recorte -> gris -> TAM_CARA -> ecualización -> máscara elíptica -> media 0, desviación 1
"""
import cv2
import numpy as np

from . import config


def _mascara() -> np.ndarray:
    ancho, alto = config.TAM_CARA
    m = np.zeros((alto, ancho), np.uint8)
    cv2.ellipse(m, (ancho // 2, int(alto * 0.52)), (int(ancho * 0.42), int(alto * 0.52)), 0, 0, 360, 1, -1)
    return m.astype(bool)


MASCARA = _mascara()


def normalizar(cara: np.ndarray) -> np.ndarray:
    """Recorte de cara -> float32 (alto, ancho): solo la elipse de la cara, estandarizada.

    Fuera de la elipse vale 0 (quita esquinas con pelo/fondo). Dentro, media 0 y desviación 1:
    así una foto más clara u oscura da el mismo template.
    """
    if cara.ndim == 3:
        cara = cv2.cvtColor(cara, cv2.COLOR_BGR2GRAY)
    cara = cv2.resize(cara.astype(np.uint8), config.TAM_CARA, interpolation=cv2.INTER_AREA)
    cara = cv2.equalizeHist(cara).astype(np.float32)
    dentro = cara[MASCARA]
    salida = np.zeros_like(cara)
    salida[MASCARA] = (dentro - dentro.mean()) / (dentro.std() + 1e-6)
    return salida

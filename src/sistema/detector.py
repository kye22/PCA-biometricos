"""Detector de caras + alineado por los ojos. Responsable: módulo 1 (detector y preprocesado).

1. Busca caras con varias cascadas Haar de OpenCV (la primera que encuentre algo gana) y se
   queda con la más grande.
2. Busca los dos ojos dentro de la cara. Si no los encuentra (gafas de sol, perfil...), estima
   su posición a partir del recuadro. Nunca se inventa una cara: sin recuadro -> CaraNoEncontrada.
3. Rota y escala para que los ojos queden siempre en el mismo sitio y recorta solo la cara
   (fuera pelo, fondo y cuello en lo posible). Así PCA compara caras, no peinados.

Pendiente: detector con landmarks (YuNet) para mejores ojos y menos fallos.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from . import config
from .excepciones import CaraNoEncontrada

_HAAR = cv2.data.haarcascades
_CASCADAS = [
    (n, cv2.CascadeClassifier(_HAAR + f"haarcascade_frontalface_{n}.xml"))
    for n in ("default", "alt2", "alt")
]
_OJOS = cv2.CascadeClassifier(_HAAR + "haarcascade_eye.xml")

LADO_MAX = 1000          # se reduce la foto a esto para detectar (velocidad)
OJO_Y = 0.36             # altura de los ojos en la cara alineada (fracción del alto)
OJO_X = (0.30, 0.70)     # posición horizontal de cada ojo (fracción del ancho)


@dataclass
class Deteccion:
    caja: tuple[int, int, int, int]                      # x, y, ancho, alto en la foto original
    ojos: tuple[tuple[float, float], tuple[float, float]]  # (ojo izq. en la imagen, ojo der.)
    ojos_detectados: bool                                # False = posición estimada
    cascada: str
    cara: np.ndarray                                     # recorte alineado, gris uint8, TAM_CARA


def _iou(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    return inter / (aw * ah + bw * bh - inter)


def _caja(gris: np.ndarray):
    """Junta las caras de todas las cascadas y elige la mejor:
    1º la que tiene dos ojos detectados, 2º la que confirman al menos 2 cascadas, 3º la más grande.
    (La más grande a secas falla: en fotos de cuerpo entero confunde el torso con una cara.)
    """
    lado = min(gris.shape)
    cands = [(n, tuple(int(v) for v in c)) for n, cascada in _CASCADAS
             for c in cascada.detectMultiScale(gris, 1.1, 5, minSize=(max(24, lado // 30),) * 2)]
    if not cands:
        raise CaraNoEncontrada("No se ha detectado ninguna cara")

    def puntuacion(cand):
        _, caja = cand
        _, con_ojos = _ojos(gris, caja)
        acuerdo = sum(_iou(caja, otra) > 0.5 for _, otra in cands)
        return (con_ojos, acuerdo >= 2, caja[2] * caja[3])

    return max(cands, key=puntuacion)


def _ojos(gris: np.ndarray, caja):
    """-> ((izq, der), detectados). Coordenadas en la misma escala que `gris`."""
    x, y, w, h = caja
    estimados = ((x + 0.31 * w, y + 0.38 * h), (x + 0.69 * w, y + 0.38 * h))
    roi = gris[y:y + int(0.6 * h), x:x + w]
    cands = _OJOS.detectMultiScale(roi, 1.1, 5, minSize=(w // 10, w // 10), maxSize=(w // 3, w // 3))
    centros = [(x + ex + ew / 2, y + ey + eh / 2, ew) for ex, ey, ew, eh in cands]
    izq = [c for c in centros if c[0] < x + w / 2]
    der = [c for c in centros if c[0] >= x + w / 2]
    if not izq or not der:
        return estimados, False
    a = max(izq, key=lambda c: c[2])[:2]
    b = max(der, key=lambda c: c[2])[:2]
    distancia = np.hypot(b[0] - a[0], b[1] - a[1])
    angulo = np.degrees(np.arctan2(b[1] - a[1], b[0] - a[0]))
    if not (0.25 * w < distancia < 0.65 * w) or abs(angulo) > 25:   # pareja absurda
        return estimados, False
    return (a, b), True


def _alinear(gris: np.ndarray, ojo_izq, ojo_der) -> np.ndarray:
    """Transformación de semejanza que lleva los ojos a su sitio fijo en TAM_CARA."""
    ancho, alto = config.TAM_CARA
    (x1, y1), (x2, y2) = ojo_izq, ojo_der
    destino_dist = (OJO_X[1] - OJO_X[0]) * ancho
    escala = destino_dist / np.hypot(x2 - x1, y2 - y1)
    angulo = np.degrees(np.arctan2(y2 - y1, x2 - x1))
    centro = ((x1 + x2) / 2, (y1 + y2) / 2)
    M = cv2.getRotationMatrix2D(centro, angulo, escala)
    M[0, 2] += ancho * (OJO_X[0] + OJO_X[1]) / 2 - centro[0]
    M[1, 2] += alto * OJO_Y - centro[1]
    return cv2.warpAffine(gris, M, (ancho, alto), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)


def localizar(foto: np.ndarray) -> Deteccion:
    """Foto completa (BGR o gris) -> detección con caja, ojos y cara alineada."""
    gris = cv2.cvtColor(foto, cv2.COLOR_BGR2GRAY) if foto.ndim == 3 else foto
    gris = gris.astype(np.uint8)
    f = min(1.0, LADO_MAX / max(gris.shape))
    peq = cv2.resize(gris, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1 else gris

    cascada, caja = _caja(peq)
    (izq, der), detectados = _ojos(peq, caja)

    a_orig = lambda p: (p[0] / f, p[1] / f)
    izq, der = a_orig(izq), a_orig(der)
    caja = tuple(int(round(v / f)) for v in caja)
    return Deteccion(caja, (izq, der), detectados, cascada, _alinear(gris, izq, der))


def alinear_manual(foto: np.ndarray, ojo_izq, ojo_der) -> Deteccion:
    """Para fotos donde el detector falla: alinea con los ojos marcados a mano."""
    gris = cv2.cvtColor(foto, cv2.COLOR_BGR2GRAY) if foto.ndim == 3 else foto
    iod = np.hypot(ojo_der[0] - ojo_izq[0], ojo_der[1] - ojo_izq[1])
    caja = (int(ojo_izq[0] - 0.75 * iod), int(ojo_izq[1] - 0.9 * iod), int(2.5 * iod), int(2.5 * iod))
    return Deteccion(caja, (tuple(ojo_izq), tuple(ojo_der)), True, "manual",
                     _alinear(gris.astype(np.uint8), ojo_izq, ojo_der))


def detectar(foto: np.ndarray) -> np.ndarray:
    """Foto completa -> cara alineada (gris uint8). Lanza CaraNoEncontrada."""
    return localizar(foto).cara

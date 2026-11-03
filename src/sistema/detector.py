"""Detector de caras + alineado por los ojos. Responsable: módulo 1 (detector y preprocesado).

1. YuNet (red pequeña de OpenCV, modelos/face_detection_yunet_2023mar.onnx): da la cara y la
   posición real de los ojos. Se queda con la cara más grande.
2. Si YuNet no encuentra nada: cascadas Haar, pero SOLO se acepta la cara si además se encuentran
   los dos ojos (Haar a secas "ve" caras en fondos y texturas). Si no está el modelo YuNet,
   Haar funciona como antes (ojos estimados si no aparecen).
   Nunca se inventa una cara: sin recuadro -> CaraNoEncontrada.
3. Rota y escala para que los ojos queden siempre en el mismo sitio y recorta solo la cara
   (fuera pelo, fondo y cuello en lo posible). Así PCA compara caras, no peinados.
"""
from functools import lru_cache
from dataclasses import dataclass, field

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

UMBRAL_YUNET = 0.6       # confianza mínima de YuNet para aceptar una cara
LADO_MAX = 1000          # se reduce la foto a esto para detectar (velocidad)
OJO_Y = 0.36             # altura de los ojos en la cara alineada (fracción del alto)
OJO_X = (0.30, 0.70)     # posición horizontal de cada ojo (fracción del ancho)


@dataclass
class Deteccion:
    caja: tuple[int, int, int, int]                      # x, y, ancho, alto en la foto original
    ojos: tuple[tuple[float, float], tuple[float, float]]  # (ojo izq. en la imagen, ojo der.)
    ojos_detectados: bool                                # False = posición estimada
    cascada: str                                         # "yunet", "default", "alt2", "alt", "manual"
    cara: np.ndarray                                     # recorte alineado, gris uint8, TAM_CARA
    confianza: float = 1.0                               # de YuNet (1.0 si no viene de YuNet)
    nariz: tuple[float, float] | None = None             # puntos de YuNet en la foto original
    boca: tuple[tuple[float, float], tuple[float, float]] | None = None   # comisuras (izq., der.)
    otras: list = field(default_factory=list)            # [(caja, confianza)] de las demás caras


@lru_cache(maxsize=1)
def _yunet():
    if not config.RUTA_YUNET.exists():
        return None
    # Se pasa en memoria: OpenCV no abre rutas con tildes en Windows ("Prácticas")
    modelo = np.frombuffer(config.RUTA_YUNET.read_bytes(), np.uint8)
    return cv2.FaceDetectorYN.create("onnx", modelo, np.array([], np.uint8), (320, 320), UMBRAL_YUNET, 0.3, 50)


def _yunet_detectar(color: np.ndarray) -> list[dict] | None:
    """Todas las caras de YuNet, de mayor a menor: [{caja, confianza, ojos, nariz, boca}].
    None si no está el modelo. Ojos y comisuras ordenados por x en la imagen."""
    detector = _yunet()
    if detector is None:
        return None
    detector.setInputSize((color.shape[1], color.shape[0]))
    _, caras = detector.detect(color)
    if caras is None:
        return []
    punto = lambda c, i: (float(c[4 + 2 * i]), float(c[5 + 2 * i]))
    salida = [{"caja": tuple(int(v) for v in c[:4]), "confianza": float(c[14]),
               "ojos": tuple(sorted([punto(c, 0), punto(c, 1)])), "nariz": punto(c, 2),
               "boca": tuple(sorted([punto(c, 3), punto(c, 4)]))} for c in caras]
    return sorted(salida, key=lambda d: d["caja"][2] * d["caja"][3], reverse=True)


def parece_cara(recorte: np.ndarray, minimo: float = 0.3) -> bool | None:
    """Para los _sd: ¿YuNet ve una cara en este recorte ya alineado? None si no hay YuNet.

    Se le añade un margen (YuNet espera ver algo de contorno) y se amplía a 200 px. Con caras
    reales alineadas acierta en el 98 % de los inscritos y el 92 % de FairFace (fotos de poca
    resolución); con degradados, texturas y ruido, en el 0 % (evaluacion/medir_defensas.py)."""
    detector = _yunet()
    if detector is None:
        return None
    g = recorte if recorte.ndim == 2 else cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    g = g.astype(np.uint8)
    p = int(0.2 * max(g.shape))
    g = cv2.resize(cv2.copyMakeBorder(g, p, p, p, p, cv2.BORDER_CONSTANT, value=int(np.median(g))), (200, 200))
    detector.setInputSize((200, 200))
    detector.setScoreThreshold(minimo)
    try:
        _, caras = detector.detect(cv2.cvtColor(g, cv2.COLOR_GRAY2BGR))
    finally:
        detector.setScoreThreshold(UMBRAL_YUNET)
    return caras is not None and len(caras) > 0


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
    foto = foto.astype(np.uint8)
    color = foto if foto.ndim == 3 else cv2.cvtColor(foto, cv2.COLOR_GRAY2BGR)
    gris = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    f = min(1.0, LADO_MAX / max(gris.shape))
    reducir = lambda im: cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1 else im

    a_orig = lambda p: (p[0] / f, p[1] / f)
    caja_orig = lambda c: tuple(int(round(v / f)) for v in c)

    caras = _yunet_detectar(reducir(color))
    if caras:
        c = caras[0]
        izq, der = (a_orig(o) for o in c["ojos"])
        return Deteccion(caja_orig(c["caja"]), (izq, der), True, "yunet", _alinear(gris, izq, der),
                         confianza=c["confianza"], nariz=a_orig(c["nariz"]),
                         boca=tuple(a_orig(b) for b in c["boca"]),
                         otras=[(caja_orig(o["caja"]), o["confianza"]) for o in caras[1:]])

    peq = reducir(gris)
    cascada, caja = _caja(peq)
    (izq, der), detectados = _ojos(peq, caja)
    if caras is not None and not detectados:
        # YuNet existe y no ha visto ninguna cara: Haar sin ojos es casi siempre un falso positivo
        raise CaraNoEncontrada("No se ha detectado ninguna cara")
    izq, der = a_orig(izq), a_orig(der)
    return Deteccion(caja_orig(caja), (izq, der), detectados, cascada, _alinear(gris, izq, der))


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

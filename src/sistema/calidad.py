"""Control de calidad entre la detección y PCA. No usa ni modifica PCA.

Rechaza (CalidadInsuficiente) las fotos con las que la decisión no sería fiable o que suelen
venir de un ataque:

- varias_caras   hay otra cara de tamaño comparable: no elegimos por nuestra cuenta cuál es
                 (si no, basta poner la foto impresa de la víctima en primer plano)
- cara_pequena   menos de DIST_OJOS_MIN píxeles entre los ojos (por debajo de ~30 px solo hay
                 geometría general, sin rasgos)
- perfil         la nariz está muy desplazada respecto al centro de los ojos (cara girada)
- ojos_ocultos   la zona de los ojos es mucho más oscura que frente y mejillas (gafas de sol)
- boca_oculta    la zona de nariz y boca casi no tiene contraste (mascarilla, bufanda...)

"Sin cara" no está aquí: lo resuelve el detector (YuNet, y Haar solo si encuentra los dos ojos).

Las medidas se calculan sobre la cara alineada (gris, antes de normalizar), comparando cada zona
con una referencia de la propia cara, así no dependen de la luz de la foto. Umbrales medidos con
fotos de prueba distintas de las inscritas y ataques sintéticos (gafas de sol y mascarillas
dibujadas, fotos de grupo, fondos y texturas). Se probó también el error
de reconstrucción PCA ("distancia al espacio de caras") y NO separaba: una zona tapada y uniforme
se reconstruye tan bien o mejor que una cara normal.

Solo se aplica cuando la foto pasa por el detector (sin detector, _sd, no hay puntos ni
alineado con los que medir).
"""
from dataclasses import dataclass

import numpy as np

from . import config, preprocesado
from .detector import OJO_X, OJO_Y, Deteccion
from .excepciones import CalidadInsuficiente

# --- umbrales (ver docstring) ----------------------------------------------------------
OTRA_CARA_MIN = 0.25        # otra cara con área >= 25 % de la principal
OTRA_CARA_CONFIANZA = 0.6
DIST_OJOS_MIN = 30          # píxeles en la foto original
PERFIL_MAX = 0.45           # |nariz - centro de los ojos| / distancia entre ojos
OJOS_LUZ_MIN = 0.45         # brillo medio de los ojos / brillo de frente y mejillas
BOCA_RANGO_MIN = 0.55       # contraste (p95 - p5) de nariz-boca / el de frente y mejillas


def _zonas() -> dict[str, np.ndarray]:
    """Máscaras booleanas sobre la cara alineada (TAM_CARA), dentro de la elipse."""
    ancho, alto = config.TAM_CARA
    yy, xx = np.mgrid[0:alto, 0:ancho]
    d = (OJO_X[1] - OJO_X[0]) * ancho           # distancia entre ojos en la cara alineada
    y_ojos, cx = OJO_Y * alto, ancho / 2
    m = preprocesado.MASCARA
    return {
        "ojos": (np.abs(yy - y_ojos) <= 0.25 * d) & (np.abs(xx - cx) <= 0.85 * d) & m,
        "boca": (yy >= y_ojos + 0.55 * d) & (yy <= y_ojos + 1.35 * d) & (np.abs(xx - cx) <= 0.6 * d) & m,
        "referencia": (((yy >= y_ojos - 0.6 * d) & (yy <= y_ojos - 0.3 * d) & (np.abs(xx - cx) <= 0.55 * d))
                       | ((yy >= y_ojos + 0.3 * d) & (yy <= y_ojos + 0.65 * d)
                          & (np.abs(xx - cx) >= 0.35 * d) & (np.abs(xx - cx) <= 0.75 * d))) & m,
    }


ZONAS = _zonas()


@dataclass
class Medidas:
    caras_extra: int        # otras caras de tamaño comparable
    dist_ojos: float        # píxeles en la foto original
    perfil: float | None    # desplazamiento de la nariz / distancia entre ojos (None sin YuNet)
    ojos_luz: float
    boca_rango: float


def medir(det: Deteccion) -> Medidas:
    area = det.caja[2] * det.caja[3]
    extra = sum(1 for caja, conf in det.otras
                if conf >= OTRA_CARA_CONFIANZA and caja[2] * caja[3] >= OTRA_CARA_MIN * area)
    (x1, y1), (x2, y2) = det.ojos
    dist = float(np.hypot(x2 - x1, y2 - y1))
    perfil = None
    if det.nariz is not None and dist > 0:
        # componente de la nariz a lo largo de la línea de los ojos, respecto a su centro
        ux, uy = (x2 - x1) / dist, (y2 - y1) / dist
        nx, ny = det.nariz[0] - (x1 + x2) / 2, det.nariz[1] - (y1 + y2) / 2
        perfil = abs(nx * ux + ny * uy) / dist

    g = det.cara.astype(np.float32)
    ref = g[ZONAS["referencia"]]
    rango = lambda v: np.percentile(v, 95) - np.percentile(v, 5)
    return Medidas(extra, dist, perfil,
                   ojos_luz=float(g[ZONAS["ojos"]].mean() / (ref.mean() + 1e-3)),
                   boca_rango=float(rango(g[ZONAS["boca"]]) / (rango(ref) + 1e-3)))


MENSAJES = {
    "varias_caras": "hay varias personas en la foto",
    "cara_pequena": "la cara es demasiado pequeña",
    "perfil": "la cara está demasiado girada",
    "ojos_ocultos": "los ojos están tapados (¿gafas de sol?)",
    "boca_oculta": "la nariz o la boca están tapadas (¿mascarilla?)",
}


def problemas(m: Medidas) -> list[str]:
    p = []
    if m.caras_extra:
        p.append("varias_caras")
    if m.dist_ojos < DIST_OJOS_MIN:
        p.append("cara_pequena")
    if m.perfil is not None and m.perfil > PERFIL_MAX:
        p.append("perfil")
    if m.ojos_luz < OJOS_LUZ_MIN:
        p.append("ojos_ocultos")
    if m.boca_rango < BOCA_RANGO_MIN:
        p.append("boca_oculta")
    return p


def mensaje(motivos: list[str]) -> str:
    texto = "; ".join(MENSAJES[c] for c in motivos)
    return texto[:1].upper() + texto[1:]


def exigir(det: Deteccion) -> Medidas:
    """Lanza CalidadInsuficiente si hay algún problema; si no, devuelve las medidas."""
    m = medir(det)
    p = problemas(m)
    if p:
        raise CalidadInsuficiente(p, mensaje(p))
    return m

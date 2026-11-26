"""Métricas sobre distancia coseno: menor distancia significa mayor similitud.

FAR/FMR: fracción de intentos impostores aceptados (verificación 1:1).
FRR/FNMR: fracción de intentos genuinos rechazados (incluye errores de captura).
EER: aproximación discreta al punto en que FAR y FRR son más próximas.
"""
import numpy as np


def _vector(x, nombre: str) -> np.ndarray:
    x = np.asarray(x, dtype=float).reshape(-1)
    if not len(x) or np.isnan(x).any():
        raise ValueError(f"{nombre} debe contener distancias y no tener NaN")
    return x


def far_frr(genuinas: np.ndarray, impostoras: np.ndarray, umbrales: np.ndarray):
    """FAR(u) = impostores aceptados; FRR(u) = genuinos rechazados."""
    g = _vector(genuinas, "genuinas")
    i = _vector(impostoras, "impostoras")
    u = np.asarray(umbrales, dtype=float).reshape(-1)
    if not len(u) or np.isnan(u).any():
        raise ValueError("Se necesitan umbrales válidos")
    return (i[:, None] <= u[None, :]).mean(axis=0), (g[:, None] > u[None, :]).mean(axis=0)


def curva(genuinas, impostoras):
    """Devuelve (umbrales, FAR, FRR) e incluye los extremos de aceptación."""
    g = _vector(genuinas, "genuinas")
    i = _vector(impostoras, "impostoras")
    # Los rechazos en captura se representan como +inf; no se deben convertir
    # en aceptaciones permitiendo un umbral infinito.
    finitas = np.concatenate((g[np.isfinite(g)], i[np.isfinite(i)]))
    umbrales = np.unique(np.concatenate(([-1.0], finitas, [2.0])))
    far, frr = far_frr(g, i, umbrales)
    return umbrales, far, frr


def eer(genuinas, impostoras):
    u, far, frr = curva(genuinas, impostoras)
    pos = int(np.argmin(np.abs(far - frr)))
    return float((far[pos] + frr[pos]) / 2), float(u[pos])


def umbral_para_far(impostoras, far_objetivo: float) -> float:
    """Mayor umbral observado en [0,2] con FAR empírica <= objetivo.

    Debe usarse solo con el conjunto de CALIBRACIÓN, nunca con el de prueba.
    """
    if not 0 <= far_objetivo <= 1:
        raise ValueError("FAR objetivo fuera de [0,1]")
    i = _vector(impostoras, "impostoras")
    candidatos = np.unique(np.concatenate(([0.0], i[np.isfinite(i)], [2.0])))
    candidatos = candidatos[(candidatos >= 0) & (candidatos <= 2)]
    tasas = (i[:, None] <= candidatos[None, :]).mean(axis=0)
    validos = candidatos[tasas <= far_objetivo]
    if not len(validos):
        raise ValueError("Ningún umbral no negativo satisface la FAR objetivo")
    return float(validos[-1])


def rank1(aciertos: list[bool]) -> float:
    return float(np.mean(aciertos)) if aciertos else 0.0

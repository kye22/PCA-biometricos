"""Métricas biométricas a partir de distancias. Responsable: módulo 4 (evaluación).

Convención: distancias -> menor = más parecido; se acepta si d <= umbral.
"""
import numpy as np


def far_frr(genuinas: np.ndarray, impostoras: np.ndarray, umbrales: np.ndarray):
    """FAR(u) = impostores aceptados; FRR(u) = genuinos rechazados."""
    genuinas, impostoras = np.asarray(genuinas), np.asarray(impostoras)
    far = np.array([(impostoras <= u).mean() for u in umbrales])
    frr = np.array([(genuinas > u).mean() for u in umbrales])
    return far, frr


def eer(genuinas: np.ndarray, impostoras: np.ndarray):
    """-> (EER, umbral) en el punto donde FAR y FRR se cruzan."""
    umbrales = np.unique(np.concatenate([genuinas, impostoras]))
    far, frr = far_frr(genuinas, impostoras, umbrales)
    i = int(np.argmin(np.abs(far - frr)))
    return float((far[i] + frr[i]) / 2), float(umbrales[i])


def rank1(aciertos: list[bool]) -> float:
    return float(np.mean(aciertos)) if aciertos else 0.0

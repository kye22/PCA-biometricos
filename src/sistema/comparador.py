"""Comparación de templates. Responsable: módulo 3 (BD, comparador y API).

Provisional: distancia euclídea; contra varios templates de un id, la mínima.
Pendiente: probar coseno / Mahalanobis; umbral fijado por evaluación.
"""
import numpy as np

from . import config


def distancia(t1: np.ndarray, t2: np.ndarray) -> float:
    return float(np.linalg.norm(t1 - t2))


def distancia_a_id(template: np.ndarray, templates_id: list[np.ndarray]) -> float:
    """Distancia de un template a una persona inscrita (mínimo sobre sus templates)."""
    return min(distancia(template, t) for t in templates_id)


def acepta(d: float, umbral: float | None = None) -> bool:
    return d <= (config.UMBRAL if umbral is None else umbral)

"""Comparación de templates. Responsable: módulo 3 (BD, comparador y API).

Provisional: distancia euclídea; contra varios templates de un id, la mínima.
Pendiente: probar coseno / Mahalanobis.
"""
import numpy as np


def distancia(t1: np.ndarray, t2: np.ndarray) -> float:
    return float(np.linalg.norm(t1 - t2))


def distancia_a_id(template: np.ndarray, templates_id: list[np.ndarray]) -> float:
    """Distancia de un template a una persona inscrita (mínimo sobre sus templates)."""
    return min(distancia(template, t) for t in templates_id)


def ranking(template: np.ndarray, base: dict[str, list[np.ndarray]]) -> list[tuple[str, float]]:
    """Todos los inscritos ordenados de más cercano a más lejano: [(id, distancia), ...]."""
    return sorted(((i, distancia_a_id(template, ts)) for i, ts in base.items()), key=lambda x: x[1])


def acepta(d: float, umbral: float) -> bool:
    return d <= umbral

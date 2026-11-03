"""Comparación de templates. Responsable: módulo 3 (BD, comparador y API).

Distancia coseno entre templates blanqueados: 1 - cos(ángulo), de 0 (misma dirección) a 2
(opuestos). Mide el "tipo de cara" sin depender del tamaño del template. Contra varios
templates de un id, la mínima. Medido frente a euclídea, sin blanquear, quitando las primeras
eigenfaces, con espejos y con z-norm: evaluacion/comparar_distancias.py.
"""
import numpy as np


def distancia(t1: np.ndarray, t2: np.ndarray) -> float:
    n = np.linalg.norm(t1) * np.linalg.norm(t2)
    return float(1.0 - np.dot(t1, t2) / n) if n > 0 else 2.0


def distancia_a_id(template: np.ndarray, templates_id: list[np.ndarray]) -> float:
    """Distancia de un template a una persona inscrita (mínimo sobre sus templates)."""
    return min(distancia(template, t) for t in templates_id)


def ranking(template: np.ndarray, base: dict[str, list[np.ndarray]]) -> list[tuple[str, float]]:
    """Todos los inscritos ordenados de más cercano a más lejano: [(id, distancia), ...]."""
    return sorted(((i, distancia_a_id(template, ts)) for i, ts in base.items()), key=lambda x: x[1])


def acepta(d: float, umbral: float) -> bool:
    return d <= umbral

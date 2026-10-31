"""Análisis detallado de una foto (para la interfaz y para depurar). No es parte de los 9 métodos.

Usa exactamente los mismos pasos que api.py, así que lo que se ve en la interfaz es lo que
decidiría `identificar` / `verificar`.

Dos cosas distintas que NO hay que confundir:
- Veredicto (conjunto abierto): ¿la distancia al más cercano está por debajo del umbral?
  Si no, es DESCONOCIDO aunque haya un "más cercano".
- Confianza relativa: entre los inscritos, cuánto destaca el 1º sobre el resto. Siempre hay un
  1º, incluso para un desconocido, por eso se muestra siempre junto al veredicto.
"""
from dataclasses import dataclass

import numpy as np

from . import api, bd, comparador
from .detector import Deteccion


@dataclass
class Candidato:
    id: str
    distancia: float
    confianza: float        # relativa, suma 1 entre todos los inscritos


@dataclass
class Analisis:
    deteccion: Deteccion | None
    cara: np.ndarray                # cara normalizada que entra a PCA
    reconstruccion: np.ndarray      # lo que PCA "ve" de esa cara
    template: np.ndarray
    ranking: list[Candidato]
    umbral: float
    identificado: str | None        # = identificar(foto)
    margen: float                   # (d2 - d1) / d2: 0 = empate con el 2º, 1 = sin rival

    @property
    def mejor(self) -> Candidato | None:
        return self.ranking[0] if self.ranking else None


def confianzas(distancias: np.ndarray) -> np.ndarray:
    """Softmax de -distancia con temperatura = desviación de las distancias (sin escala fija)."""
    if len(distancias) == 1:
        return np.ones(1)
    t = distancias.std() or 1.0
    z = -(distancias - distancias.min()) / t
    e = np.exp(z)
    return e / e.sum()


def analizar(foto, con_detector: bool = True) -> Analisis:
    template, det, cara = api.extraer(foto, con_detector)
    rank = comparador.ranking(template, bd.cargar())
    u = api.umbral()

    dists = np.array([d for _, d in rank])
    conf = confianzas(dists) if len(rank) else np.array([])
    ranking = [Candidato(i, d, float(c)) for (i, d), c in zip(rank, conf)]
    margen = float((dists[1] - dists[0]) / dists[1]) if len(dists) > 1 and dists[1] > 0 else 1.0
    identificado = ranking[0].id if ranking and comparador.acepta(ranking[0].distancia, u) else None

    return Analisis(det, cara, api._modelo().reconstruir(template), template, ranking, u,
                    identificado, margen)

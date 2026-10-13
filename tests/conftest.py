"""Fixtures comunes: entorno aislado (BD y modelo en tmp) con caras sintéticas.

Los tests no necesitan fotos reales: cada "persona" es un patrón aleatorio fijo con ruido.
"""
import numpy as np
import pytest

from sistema import api, config
from sistema.pca import ModeloPCA


def cara_sintetica(persona: int, variacion: int = 0) -> np.ndarray:
    """Imagen uint8 TAM_CARA: patrón base de la persona + un poco de ruido."""
    base = np.random.default_rng(persona).integers(0, 256, config.TAM_CARA[::-1])
    ruido = np.random.default_rng(1000 + 31 * persona + variacion).normal(0, 8, base.shape)
    return np.clip(base + ruido, 0, 255).astype(np.uint8)


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """BD vacía + modelo PCA entrenado con 5 personas x 3 fotos, todo en tmp."""
    from sistema import preprocesado

    monkeypatch.setattr(config, "RUTA_BD", tmp_path / "bd.csv")
    monkeypatch.setattr(config, "RUTA_MODELO", tmp_path / "pca.npz")
    caras = np.stack([preprocesado.normalizar(cara_sintetica(p, v)) for p in range(5) for v in range(3)])
    ModeloPCA.entrenar(caras, n_componentes=10).guardar(config.RUTA_MODELO)
    api.recargar()
    yield tmp_path
    api.recargar()

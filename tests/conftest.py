"""Fixtures comunes: entorno aislado (BD y modelo en tmp) con caras sintéticas.

Los tests no necesitan fotos reales: cada "persona" es un patrón aleatorio fijo con ruido.
"""
import numpy as np
import pytest

from sistema import api, config, detector, seguridad
from sistema.pca import ModeloPCA

CLAVE_TEST = "ab" * 32


@pytest.fixture(autouse=True)
def clave(monkeypatch, tmp_path):
    """Todos los tests con una clave de prueba (nunca la de datos/clave.key)."""
    monkeypatch.setenv("SISTEMA_CLAVE", CLAVE_TEST)
    monkeypatch.setattr(config, "RUTA_CLAVE", tmp_path / "clave.key")
    seguridad.olvidar_clave()
    yield
    seguridad.olvidar_clave()


def cara_sintetica(persona: int, variacion: int = 0) -> np.ndarray:
    """Imagen uint8 TAM_CARA: patrón base de la persona + un poco de ruido."""
    base = np.random.default_rng(persona).integers(0, 256, config.TAM_CARA[::-1])
    ruido = np.random.default_rng(1000 + 31 * persona + variacion).normal(0, 8, base.shape)
    return np.clip(base + ruido, 0, 255).astype(np.uint8)


def fijar_umbral(u: float) -> None:
    """Guarda el umbral en el modelo firmado del entorno de test, como hace montar.py
    (no hay variable de entorno para cambiarlo)."""
    m = ModeloPCA.cargar(config.RUTA_MODELO, seguridad.clave_modelo())
    m.umbral = u
    m.guardar(config.RUTA_MODELO, seguridad.clave_modelo())
    api.recargar()


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """BD vacía + modelo PCA entrenado con 5 personas x 3 fotos, todo en tmp.
    K=4: con 5 personas solo hay 4 direcciones de identidad; el resto es ruido (y blanqueado pesaría igual)."""
    from sistema import preprocesado

    monkeypatch.setattr(config, "RUTA_BD", tmp_path / "bd.csv")
    # las "caras" sintéticas son ruido: YuNet no las ve. El filtro se prueba aparte (test_seguridad)
    monkeypatch.setattr(detector, "parece_cara", lambda *a, **k: True)
    monkeypatch.setattr(config, "RUTA_MODELO", tmp_path / "pca.npz")
    caras = np.stack([preprocesado.normalizar(cara_sintetica(p, v)) for p in range(5) for v in range(3)])
    ModeloPCA.entrenar(caras, n_componentes=4).guardar(config.RUTA_MODELO, seguridad.clave_modelo())
    api.recargar()
    yield tmp_path
    api.recargar()

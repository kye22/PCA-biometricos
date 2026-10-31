import numpy as np
import pytest

from sistema.excepciones import ModeloNoEntrenado
from sistema.pca import ModeloPCA


def test_entrenar_extraer_guardar_cargar(tmp_path):
    caras = np.random.default_rng(0).random((20, 10, 10), dtype=np.float32)
    modelo = ModeloPCA.entrenar(caras, n_componentes=5)
    assert modelo.dim == 5

    t = modelo.extraer(caras[0])
    assert t.shape == (5,) and t.dtype == np.float32

    modelo.guardar(tmp_path / "m.npz")
    np.testing.assert_allclose(ModeloPCA.cargar(tmp_path / "m.npz").extraer(caras[0]), t)


def test_componentes_limitadas_por_n_muestras():
    """Con N caras solo hay N-1 direcciones con información."""
    caras = np.random.default_rng(0).random((4, 10, 10))
    assert ModeloPCA.entrenar(caras, n_componentes=50).dim == 3


def test_umbral_y_forma_viajan_con_el_modelo(tmp_path):
    caras = np.random.default_rng(0).random((20, 10, 10), dtype=np.float32)
    modelo = ModeloPCA.entrenar(caras, n_componentes=19)
    modelo.umbral = 42.5
    modelo.guardar(tmp_path / "m.npz")
    cargado = ModeloPCA.cargar(tmp_path / "m.npz")
    assert cargado.umbral == 42.5 and cargado.forma == (10, 10)
    assert cargado.varianza_explicada() == pytest.approx(1.0, abs=1e-5)  # K = N-1: toda la varianza


def test_reconstruir_cara_de_entrenamiento():
    """Con todas las componentes, reconstruir(extraer(x)) devuelve x: base del ataque de inversión."""
    caras = np.random.default_rng(0).random((20, 10, 10), dtype=np.float32)
    modelo = ModeloPCA.entrenar(caras, n_componentes=19)
    np.testing.assert_allclose(modelo.reconstruir(modelo.extraer(caras[3])), caras[3], atol=1e-4)


def test_cargar_sin_modelo(tmp_path):
    with pytest.raises(ModeloNoEntrenado):
        ModeloPCA.cargar(tmp_path / "nada.npz")

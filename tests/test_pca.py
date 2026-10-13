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
    caras = np.random.default_rng(0).random((4, 10, 10))
    assert ModeloPCA.entrenar(caras, n_componentes=50).dim == 4


def test_cargar_sin_modelo(tmp_path):
    with pytest.raises(ModeloNoEntrenado):
        ModeloPCA.cargar(tmp_path / "nada.npz")

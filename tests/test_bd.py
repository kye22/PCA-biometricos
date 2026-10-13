import numpy as np

from sistema import bd


def test_guardar_y_cargar(tmp_path):
    ruta = tmp_path / "bd.csv"
    t1, t2 = np.array([1.5, -2.0, 3.25], np.float32), np.array([0.0, 1.0, 2.0], np.float32)
    bd.guardar("ana", t1, ruta)
    bd.guardar("ana", t2, ruta)
    bd.guardar("luis", t1, ruta)

    base = bd.cargar(ruta)
    assert set(base) == {"ana", "luis"}
    assert len(base["ana"]) == 2
    np.testing.assert_allclose(base["ana"][0], t1, atol=1e-6)


def test_bd_inexistente_es_vacia(tmp_path):
    assert bd.cargar(tmp_path / "no_existe.csv") == {}

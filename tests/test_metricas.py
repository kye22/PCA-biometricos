import numpy as np
import pytest

from evaluacion.metricas import curva, eer, far_frr, rank1, umbral_para_far


def test_eer_separacion_perfecta():
    valor, umbral = eer(np.array([1.0, 2.0]), np.array([5.0, 6.0]))
    assert valor == 0.0 and 2.0 <= umbral < 5.0


def test_eer_solapado():
    valor, _ = eer(np.array([1.0, 2.0, 3.0, 4.0]), np.array([3.5, 5.0, 6.0, 7.0]))
    assert 0.0 < valor <= 0.5


def test_rank1():
    assert rank1([True, False, True, True]) == 0.75


def test_far_frr_con_rechazo_en_captura():
    far, frr = far_frr([0.2, float("inf")], [0.1, 0.8, float("inf")], [0.3])
    assert far[0] == pytest.approx(1 / 3)
    assert frr[0] == pytest.approx(0.5)


def test_curva_nunca_acepta_capturas_fallidas():
    umbrales, _far, frr = curva([float("inf")], [0.2])
    assert max(umbrales) <= 2.0
    assert np.all(frr == 1)


def test_umbral_para_far_tasa_empirica():
    imp = [0.1, 0.2, 0.3, 0.4]
    assert umbral_para_far(imp, 0.25) == pytest.approx(0.1)
    assert umbral_para_far(imp, 0) == pytest.approx(0.0)
    with pytest.raises(ValueError):
        umbral_para_far(imp, 1.5)


def test_no_hay_metricas_sin_muestras():
    with pytest.raises(ValueError):
        eer([], [0.5])

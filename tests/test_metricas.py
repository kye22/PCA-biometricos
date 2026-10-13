import numpy as np

from metricas import eer, rank1


def test_eer_separacion_perfecta():
    valor, umbral = eer(np.array([1.0, 2.0]), np.array([5.0, 6.0]))
    assert valor == 0.0 and 2.0 <= umbral < 5.0


def test_eer_solapado():
    valor, _ = eer(np.array([1.0, 2.0, 3.0, 4.0]), np.array([3.5, 5.0, 6.0, 7.0]))
    assert 0.0 < valor <= 0.5


def test_rank1():
    assert rank1([True, False, True, True]) == 0.75

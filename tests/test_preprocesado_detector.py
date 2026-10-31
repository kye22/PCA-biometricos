import numpy as np

from sistema import config, detector, preprocesado


def test_normalizar_mascara_y_estandarizacion():
    cara = np.random.default_rng(0).integers(0, 256, (150, 120, 3)).astype(np.uint8)
    n = preprocesado.normalizar(cara)
    assert n.shape == config.TAM_CARA[::-1]
    assert np.all(n[~preprocesado.MASCARA] == 0)
    dentro = n[preprocesado.MASCARA]
    assert abs(dentro.mean()) < 1e-3 and abs(dentro.std() - 1) < 1e-2


def test_normalizar_insensible_a_brillo():
    cara = np.random.default_rng(1).integers(40, 200, (100, 100)).astype(np.uint8)
    np.testing.assert_allclose(preprocesado.normalizar(cara), preprocesado.normalizar(cara + 30), atol=1e-5)


def test_alinear_manual_pone_los_ojos_en_su_sitio():
    """Dos puntos blancos como 'ojos' girados: tras alinear quedan en OJO_X / OJO_Y."""
    img = np.zeros((400, 400), np.uint8)
    izq, der = (150, 200), (250, 230)
    img[izq[1] - 2:izq[1] + 3, izq[0] - 2:izq[0] + 3] = 255
    img[der[1] - 2:der[1] + 3, der[0] - 2:der[0] + 3] = 255
    cara = detector.alinear_manual(img, izq, der).cara
    ancho, alto = config.TAM_CARA
    ys, xs = np.nonzero(cara > 100)
    assert abs(ys.mean() - detector.OJO_Y * alto) < 2
    assert abs(xs.min() - detector.OJO_X[0] * ancho) < 3 and abs(xs.max() - detector.OJO_X[1] * ancho) < 3

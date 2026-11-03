import numpy as np
import pytest

from sistema import analisis, api, config

from conftest import cara_sintetica


@pytest.fixture
def inscritos(entorno, monkeypatch):
    monkeypatch.setattr(config, "UMBRAL", 0.3)
    for p in range(3):
        api.inscribir_sd(f"persona{p}", cara_sintetica(p, 0))
    return entorno


def test_coincide_con_identificar(inscritos):
    foto = cara_sintetica(1, 2)
    a = analisis.analizar(foto, con_detector=False)
    assert a.identificado == api.identificar_sd(foto) == "persona1"
    assert [c.id for c in a.ranking][0] == "persona1"
    assert abs(sum(c.confianza for c in a.ranking) - 1) < 1e-6
    assert a.reconstruccion.shape == config.TAM_CARA[::-1]


def test_desconocido_tiene_favorito_pero_no_identificado(inscritos):
    """Siempre hay un 1º con la mayor confianza relativa, pero el umbral decide."""
    a = analisis.analizar(cara_sintetica(4, 0), con_detector=False)   # persona 4 no inscrita
    assert a.identificado is None
    assert a.mejor is not None and a.mejor.confianza == max(c.confianza for c in a.ranking)


def test_confianzas_suman_uno():
    c = analisis.confianzas(np.array([1.0, 2.0, 10.0]))
    assert abs(c.sum() - 1) < 1e-9 and c[0] > c[1] > c[2]

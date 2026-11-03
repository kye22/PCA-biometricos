"""Los 9 métodos de punta a punta con caras sintéticas (sin detector real salvo en un test)."""
import numpy as np
import pytest

from sistema import api, config
from sistema.excepciones import CaraNoEncontrada, IdDesconocido, TemplateInvalido

from conftest import cara_sintetica


@pytest.fixture
def inscritos(entorno, monkeypatch):
    monkeypatch.setattr(config, "UMBRAL", 0.3)  # coseno: genuinas ~0.05, impostoras ~1
    for p in range(3):
        api.inscribir_sd(f"persona{p}", cara_sintetica(p, 0))
    return entorno


def test_verificar_sd_genuino_e_impostor(inscritos):
    assert api.verificar_sd("persona0", cara_sintetica(0, 1))
    assert not api.verificar_sd("persona0", cara_sintetica(1, 1))


def test_identificar_sd(inscritos):
    assert api.identificar_sd(cara_sintetica(2, 1)) == "persona2"


def test_template_t(inscritos):
    t = api._modelo().extraer(np.zeros(config.TAM_CARA[::-1], np.float32))
    api.inscribir_t("plantilla", t)
    assert api.verificar_t("plantilla", t)
    assert api.identificar_t(t) == "plantilla"


def test_template_invalido(inscritos):
    with pytest.raises(TemplateInvalido):
        api.verificar_t("persona0", np.zeros(3))
    with pytest.raises(TemplateInvalido):
        api.inscribir_t("x", np.full(api._modelo().dim, np.nan))


def test_id_desconocido(inscritos):
    with pytest.raises(IdDesconocido):
        api.verificar_sd("nadie", cara_sintetica(0, 1))


def test_identificar_bd_vacia(entorno):
    assert api.identificar_sd(cara_sintetica(0, 1)) is None


def test_detector_sin_cara(entorno):
    with pytest.raises(CaraNoEncontrada):
        api.verificar("persona0", np.zeros((200, 200, 3), np.uint8))

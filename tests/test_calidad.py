"""Control de calidad con detecciones construidas a mano (sin fotos reales)."""
import numpy as np
import pytest

from sistema import api, calidad, config
from sistema.detector import Deteccion
from sistema.excepciones import CalidadInsuficiente


def cara_base() -> np.ndarray:
    """Cara alineada sintética: frente/mejillas claras, ojos algo más oscuros, boca con contraste."""
    rng = np.random.default_rng(0)
    c = np.full(config.TAM_CARA[::-1], 170, np.float32) + rng.normal(0, 12, config.TAM_CARA[::-1])
    c[calidad.ZONAS["ojos"]] -= 40
    boca = calidad.ZONAS["boca"]
    c[boca] += rng.normal(0, 35, boca.sum())
    return np.clip(c, 0, 255).astype(np.uint8)


def deteccion(cara=None, ojos=((100, 100), (160, 100)), nariz=(130, 135), otras=()):
    return Deteccion(caja=(60, 50, 140, 140), ojos=ojos, ojos_detectados=True, cascada="yunet",
                     cara=cara_base() if cara is None else cara, nariz=nariz,
                     boca=((110, 165), (150, 165)), otras=list(otras))


def test_cara_buena_pasa():
    assert calidad.problemas(calidad.medir(deteccion())) == []


def test_varias_caras():
    grande = ((300, 50, 120, 120), 0.9)
    pequena = ((300, 50, 30, 30), 0.9)
    assert "varias_caras" in calidad.problemas(calidad.medir(deteccion(otras=[grande])))
    assert "varias_caras" not in calidad.problemas(calidad.medir(deteccion(otras=[pequena])))


def test_cara_pequena_y_perfil():
    assert "cara_pequena" in calidad.problemas(calidad.medir(deteccion(ojos=((100, 100), (120, 100)))))
    assert "perfil" in calidad.problemas(calidad.medir(deteccion(nariz=(162, 135))))


def test_gafas_de_sol():
    c = cara_base()
    c[calidad.ZONAS["ojos"]] = 20
    assert "ojos_ocultos" in calidad.problemas(calidad.medir(deteccion(cara=c)))


def test_mascarilla():
    c = cara_base()
    c[calidad.ZONAS["boca"]] = 210
    assert "boca_oculta" in calidad.problemas(calidad.medir(deteccion(cara=c)))


def test_exigir_lanza_con_motivos():
    c = cara_base()
    c[calidad.ZONAS["boca"]] = 210
    with pytest.raises(CalidadInsuficiente) as e:
        calidad.exigir(deteccion(cara=c, otras=[((300, 50, 120, 120), 0.9)]))
    assert set(e.value.motivos) == {"varias_caras", "boca_oculta"}


def test_identificar_rechaza_foto_sin_cara(entorno):
    from sistema.excepciones import CaraNoEncontrada
    with pytest.raises(CaraNoEncontrada):
        api.identificar(np.full((300, 300, 3), 128, np.uint8))

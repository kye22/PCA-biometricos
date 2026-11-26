"""Defensas: BD cifrada y firmada, modelo firmado, entradas _t/_sd fabricadas, ids e imágenes raras."""
import io

import numpy as np
import pytest
from PIL import Image

from sistema import api, bd, config, imagen, seguridad
from sistema.excepciones import (ClaveNoEncontrada, IdInvalido, IdYaInscrito, InscripcionRechazada,
                                 Manipulado, NoPareceCara, TemplateInvalido)
from sistema.pca import ModeloPCA

from conftest import cara_sintetica, fijar_umbral


@pytest.fixture
def inscritos(entorno):
    fijar_umbral(0.3)
    for p in range(3):
        api.inscribir_sd(f"persona{p}", cara_sintetica(p, 0))
    return entorno


def filas():
    return config.RUTA_BD.read_text(encoding="utf-8").splitlines()


def escribir(lineas):
    config.RUTA_BD.write_text("\n".join(lineas) + "\n", encoding="utf-8")


# --- BD ------------------------------------------------------------------------------------

def test_bd_no_guarda_templates_en_claro(inscritos):
    t = api._modelo().extraer(np.zeros(config.TAM_CARA[::-1], np.float32))
    texto = config.RUTA_BD.read_text(encoding="utf-8")
    assert f"{t[0]:.6f}" not in texto and "persona0" in texto      # id en claro, template no


def test_replay_de_fila_robada_no_sirve(inscritos):
    """Leer la BD no da un template utilizable en verificar_t (va cifrado)."""
    robado = filas()[1].split(",", 1)[1]
    with pytest.raises(TemplateInvalido):
        api.verificar_t("persona0", robado)


def test_escribir_fila_nueva_se_detecta(inscritos):
    """Suplantación: añadir mi template con el id de la víctima sin pasar por la API."""
    lineas = filas()
    escribir(lineas + [lineas[2].replace("persona1", "persona0", 1)])   # fila de otro, movida de id
    with pytest.raises(Manipulado):
        bd.cargar()


def test_borrar_fila_se_detecta(inscritos):
    escribir(filas()[:-1])
    with pytest.raises(Manipulado):
        api.identificar_sd(cara_sintetica(0, 1))


def test_retocar_fila_se_detecta_aunque_se_refirme(inscritos):
    """Aunque el atacante recalcule bd.firma con OTRA clave, no le sirve."""
    lineas = filas()
    id_, cifrado = lineas[1].split(",", 1)
    lineas[1] = f"{id_},{cifrado[:-6]}AAAAAA"
    escribir(lineas)
    with pytest.raises(Manipulado):
        bd.cargar()


def test_no_se_inscribe_sobre_una_bd_manipulada(inscritos):
    escribir(filas()[:-1])
    with pytest.raises(Manipulado):
        api.inscribir_sd("nuevo", cara_sintetica(4, 0))


def test_borrar_la_bd_entera_se_detecta(inscritos):
    config.RUTA_BD.unlink()
    with pytest.raises(Manipulado):
        bd.cargar()


def test_sin_clave_no_se_lee(inscritos, monkeypatch):
    monkeypatch.delenv("SISTEMA_CLAVE")
    seguridad.olvidar_clave()
    with pytest.raises(ClaveNoEncontrada):
        bd.cargar()


def test_con_otra_clave_no_se_lee(inscritos, monkeypatch):
    monkeypatch.setenv("SISTEMA_CLAVE", "cd" * 32)
    seguridad.olvidar_clave()
    with pytest.raises(Manipulado):
        bd.cargar()


# --- modelo ------------------------------------------------------------------------------

def test_cambiar_el_umbral_del_modelo_se_detecta(inscritos):
    m = ModeloPCA.cargar(config.RUTA_MODELO)
    m.umbral = 2.0                                        # "acepta a cualquiera"
    m.guardar(config.RUTA_MODELO)                         # sin la clave: sin firma válida
    api.recargar()
    with pytest.raises(Manipulado):
        api.identificar_sd(cara_sintetica(0, 1))


def test_umbral_no_se_cambia_por_entorno(inscritos, monkeypatch):
    """Con el umbral en una variable de entorno, quien controle el entorno aceptaría a cualquiera."""
    monkeypatch.setenv("SISTEMA_UMBRAL", "2")
    assert not hasattr(config, "UMBRAL")
    assert api.umbral() == pytest.approx(0.3)
    assert not api.verificar_sd("persona0", cara_sintetica(1, 1))


# --- inscripción ---------------------------------------------------------------------------

def test_no_se_puede_inscribir_sobre_un_id_existente(inscritos):
    """Secuestro de id: añadir mi cara a la identidad de otro por la API."""
    with pytest.raises(IdYaInscrito):
        api.inscribir_sd("persona0", cara_sintetica(3, 0))
    assert not api.verificar_sd("persona0", cara_sintetica(3, 1))
    assert len(bd.cargar()["persona0"]) == 1


def test_actualizar_solo_con_una_muestra_que_verifica(inscritos):
    with pytest.raises(InscripcionRechazada):
        api.inscribir_sd("persona0", cara_sintetica(3, 0), actualizar=True)
    api.inscribir_sd("persona0", cara_sintetica(0, 2), actualizar=True)
    assert len(bd.cargar()["persona0"]) == 2


def test_carga_inicial_admite_varias_fotos_por_persona(entorno):
    """montar.py inscribe varias fotos por persona con la carga inicial de administrador."""
    for v in range(2):
        api._inscribir_carga_inicial("persona0", api._template_desde_foto(cara_sintetica(0, v), con_detector=False))
    assert len(bd.cargar()["persona0"]) == 2


# --- entradas fabricadas -----------------------------------------------------------------

@pytest.fixture
def con_limites(inscritos):
    """Límites como los de pca_base.npz, medidos aquí con las caras sintéticas."""
    m = ModeloPCA.cargar(config.RUTA_MODELO)
    caras = [api.preprocesado.normalizar(cara_sintetica(p, v)) for p in range(5) for v in range(3, 8)]
    normas = [np.linalg.norm(m.extraer(c)) for c in caras]
    m.limites = {"norma_min": 0.5 * min(normas), "norma_max": 2 * max(normas),
                 "residuo_max": 1.1 * max(m.residuo(c) for c in caras)}
    m.guardar(config.RUTA_MODELO, seguridad.clave_modelo())
    api.recargar()
    return inscritos


def test_template_cero_rechazado(con_limites):
    """Ceros = "la cara media": a distancia pequeña de mucha gente con algunas métricas."""
    with pytest.raises(TemplateInvalido):
        api.identificar_t(np.zeros(api._modelo().dim))


def test_template_extremo_rechazado(con_limites):
    t = api._modelo().extraer(api.preprocesado.normalizar(cara_sintetica(0, 1)))
    with pytest.raises(TemplateInvalido):
        api.verificar_t("persona0", t * 100)


def test_template_real_aceptado(con_limites):
    t = api._modelo().extraer(api.preprocesado.normalizar(cara_sintetica(0, 1)))
    assert api.verificar_t("persona0", t)


def test_sd_rechaza_imagen_que_no_es_cara(con_limites):
    """Un tablero de ajedrez no se parece a nada del espacio de caras."""
    alto, ancho = config.TAM_CARA[::-1]
    tablero = ((np.indices((alto, ancho)).sum(0) // 10) % 2 * 255).astype(np.uint8)
    with pytest.raises(NoPareceCara):
        api.identificar_sd(tablero)


def test_id_con_formula_rechazado(entorno):
    t = api._modelo().extraer(api.preprocesado.normalizar(cara_sintetica(0, 0)))
    for malo in ("=HYPERLINK(\"x\")", "+1", "a,b", "a\nb", ""):
        with pytest.raises(IdInvalido):
            api.inscribir_t(malo, t)
    api.inscribir_t("mary-kate_olsen", t)


def test_imagen_gigante_rechazada_sin_descomprimir():
    buf = io.BytesIO()
    Image.new("L", (8000, 6000)).save(buf, "PNG")        # pocos KB comprimida, 48 Mpx
    with pytest.raises(ValueError):
        imagen.leer(buf.getvalue())


def test_parece_cara_con_yunet():
    """El filtro real de los _sd: una cara alineada sí, un degradado no."""
    import cv2
    from sistema import detector
    if detector._yunet() is None:
        pytest.skip("sin modelo YuNet")
    alto, ancho = config.TAM_CARA[::-1]
    degradado = np.tile(np.linspace(0, 255, ancho), (alto, 1)).astype(np.uint8)
    assert detector.parece_cara(degradado) is False
    foto = config.RAIZ / "datos" / "extra" / "alvaro_arbeloa_coca.jpg"
    assert detector.parece_cara(detector.localizar(imagen.leer(foto)).cara) is True

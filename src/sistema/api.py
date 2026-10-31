"""Los 9 métodos del enunciado. Responsable: módulo 3 (BD, comparador y API).

    foto      -> detector (+alineado) -> [calidad] -> preprocesado -> PCA -> comparador <- BD
    foto _sd  -----------------------> preprocesado -> PCA -> comparador <- BD
    template _t ---------------------------------------------> comparador <- BD

`foto` puede ser una ruta, bytes de un archivo o un array (BGR/gris).
`template` es un array 1D de longitud K.
verificar* -> bool. identificar* -> id del más cercano, o None si ninguno pasa el umbral.

Control de calidad (calidad.py): verificar() e identificar() lanzan CalidadInsuficiente si la foto
tiene varias caras, una cara muy pequeña o girada, o los ojos/la boca tapados. inscribir() no lo
aplica (se inscribe lo que da el dataset; montar.py avisa) y los _sd no pueden (no hay detección).
"""
from functools import lru_cache

import numpy as np

from . import bd, calidad, comparador, config, detector, imagen, preprocesado
from .excepciones import IdDesconocido, TemplateInvalido
from .pca import ModeloPCA


@lru_cache(maxsize=1)
def _modelo() -> ModeloPCA:
    return ModeloPCA.cargar(config.RUTA_MODELO)


def recargar() -> None:
    """Olvida el modelo en memoria (p. ej. tras reentrenar)."""
    _modelo.cache_clear()


def umbral() -> float:
    """El de la variable de entorno si existe; si no, el guardado con el modelo."""
    if config.UMBRAL is not None:
        return config.UMBRAL
    return _modelo().umbral if _modelo().umbral is not None else config.UMBRAL_POR_DEFECTO


# --- pasos de la cadena (los usa también analisis.py, para que la UI decida igual) ----

def extraer(foto, con_detector: bool, control: bool = False):
    """foto -> (template, deteccion | None, cara_normalizada).
    control=True aplica el control de calidad (solo tiene efecto con detector)."""
    img = imagen.leer(foto)
    det = detector.localizar(img) if con_detector else None
    if det is not None and control:
        calidad.exigir(det)
    cara = preprocesado.normalizar(det.cara if det else img)
    return _modelo().extraer(cara), det, cara


def _template_desde_foto(foto, con_detector: bool, control: bool = False) -> np.ndarray:
    return extraer(foto, con_detector, control)[0]


def validar(template) -> np.ndarray:
    t = np.asarray(template, dtype=np.float32).reshape(-1)
    if t.shape[0] != _modelo().dim or not np.all(np.isfinite(t)):
        raise TemplateInvalido(f"Se esperaba un vector finito de longitud {_modelo().dim}")
    return t


# --- núcleo común: todo acaba aquí --------------------------------------------

def inscribir_t(id: str, template) -> None:
    bd.guardar(id, validar(template))


def verificar_t(id: str, template) -> bool:
    t = validar(template)
    base = bd.cargar()
    if id not in base:
        raise IdDesconocido(id)
    return comparador.acepta(comparador.distancia_a_id(t, base[id]), umbral())


def identificar_t(template) -> str | None:
    t = validar(template)
    base = bd.cargar()
    if not base:
        return None
    mejor_id, mejor_d = comparador.ranking(t, base)[0]
    return mejor_id if comparador.acepta(mejor_d, umbral()) else None


# --- sin detector ---------------------------------------------------------------

def inscribir_sd(id: str, foto) -> None:
    inscribir_t(id, _template_desde_foto(foto, con_detector=False))


def verificar_sd(id: str, foto) -> bool:
    return verificar_t(id, _template_desde_foto(foto, con_detector=False))


def identificar_sd(foto) -> str | None:
    return identificar_t(_template_desde_foto(foto, con_detector=False))


# --- pipeline completo ------------------------------------------------------------

def inscribir(id: str, foto) -> None:
    inscribir_t(id, _template_desde_foto(foto, con_detector=True))


def verificar(id: str, foto) -> bool:
    return verificar_t(id, _template_desde_foto(foto, con_detector=True, control=True))


def identificar(foto) -> str | None:
    return identificar_t(_template_desde_foto(foto, con_detector=True, control=True))

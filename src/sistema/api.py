"""Los 9 métodos del enunciado. Responsable: módulo 3 (BD, comparador y API).

    foto      -> detector -> preprocesado -> PCA -> comparador <- BD
    foto _sd  ------------> preprocesado -> PCA -> comparador <- BD
    template _t ----------------------------------> comparador <- BD

`foto` puede ser una ruta o un array (BGR/gris). `template` es un array 1D de longitud K.
verificar* -> bool. identificar* -> id del más cercano, o None si ninguno pasa el umbral.
"""
from functools import lru_cache

import numpy as np

from . import bd, comparador, config, detector, imagen, preprocesado
from .excepciones import IdDesconocido, TemplateInvalido
from .pca import ModeloPCA


@lru_cache(maxsize=1)
def _modelo() -> ModeloPCA:
    return ModeloPCA.cargar(config.RUTA_MODELO)


def recargar() -> None:
    """Olvida el modelo en memoria (p. ej. tras reentrenar)."""
    _modelo.cache_clear()


# --- pasos de la cadena -------------------------------------------------------

def _template_desde_foto(foto, con_detector: bool) -> np.ndarray:
    img = imagen.leer(foto)
    cara = detector.detectar(img) if con_detector else img
    return _modelo().extraer(preprocesado.normalizar(cara))


def _validar(template) -> np.ndarray:
    t = np.asarray(template, dtype=np.float32).reshape(-1)
    if t.shape[0] != _modelo().dim or not np.all(np.isfinite(t)):
        raise TemplateInvalido(f"Se esperaba un vector finito de longitud {_modelo().dim}")
    return t


# --- núcleo común: todo acaba aquí --------------------------------------------

def inscribir_t(id: str, template) -> None:
    bd.guardar(id, _validar(template))


def verificar_t(id: str, template) -> bool:
    t = _validar(template)
    base = bd.cargar()
    if id not in base:
        raise IdDesconocido(id)
    return comparador.acepta(comparador.distancia_a_id(t, base[id]))


def identificar_t(template) -> str | None:
    t = _validar(template)
    base = bd.cargar()
    if not base:
        return None
    mejor_id, mejor_d = min(
        ((i, comparador.distancia_a_id(t, ts)) for i, ts in base.items()), key=lambda x: x[1]
    )
    return mejor_id if comparador.acepta(mejor_d) else None


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
    return verificar_t(id, _template_desde_foto(foto, con_detector=True))


def identificar(foto) -> str | None:
    return identificar_t(_template_desde_foto(foto, con_detector=True))

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

Defensas de entrada (límites medidos en la base de entrenamiento y guardados con el modelo):
- _sd (y verificar/identificar): NoPareceCara si PCA no puede explicar la imagen (error de
  reconstrucción alto): ruido, texturas, tableros...
- verificar_sd / identificar_sd: además, NoPareceCara si YuNet no ve una cara en el recorte
  (degradados y texturas suaves que PCA sí "explica"). inscribir_sd no lo exige: lo usa quien
  administra el sistema, p. ej. con ojos marcados a mano cuando el detector falla.
- todos los caminos, incluido _t: TemplateInvalido si la norma del template es imposible para
  una cara real (p. ej. ceros = "la cara media", o valores extremos).
- inscribir*: IdInvalido si el id no es texto simple (evita inyección de fórmulas en el .csv).
- inscribir*: IdYaInscrito si el id ya está en la BD, para que nadie añada su cara a la identidad
  de otro. Con actualizar=True se admite otra muestra, pero solo si ya verifica contra ese id
  (si no, InscripcionRechazada). La carga inicial con varias fotos por persona la hace montar.py
  con _inscribir_carga_inicial().
El umbral sale siempre del modelo firmado (no hay variable de entorno que lo cambie).
El modelo se carga comprobando su firma y la BD va cifrada y firmada (seguridad.py, bd.py).
"""
import re
from functools import lru_cache

import numpy as np

from . import bd, calidad, comparador, config, detector, imagen, preprocesado, seguridad
from .excepciones import (IdDesconocido, IdInvalido, IdYaInscrito, InscripcionRechazada, NoPareceCara,
                          TemplateInvalido)
from .pca import ModeloPCA


@lru_cache(maxsize=1)
def _modelo() -> ModeloPCA:
    return ModeloPCA.cargar(config.RUTA_MODELO, seguridad.clave_modelo())


def recargar() -> None:
    """Olvida el modelo y la clave en memoria (p. ej. tras reentrenar)."""
    _modelo.cache_clear()
    seguridad.olvidar_clave()


_ID = re.compile(r"^\w[\w().\-]{0,79}$")


def umbral() -> float:
    """El guardado (y firmado) con el modelo. No se puede cambiar por variable de entorno."""
    return _modelo().umbral if _modelo().umbral is not None else config.UMBRAL_POR_DEFECTO


# --- pasos de la cadena (los usa también analisis.py, para que la UI decida igual) ----

def extraer(foto, con_detector: bool, control: bool = False):
    """foto -> (template, deteccion | None, cara_normalizada).
    control=True: con detector, control de calidad; sin detector, que YuNet vea una cara."""
    img = imagen.leer(foto)
    det = detector.localizar(img) if con_detector else None
    if det is not None and control:
        calidad.exigir(det)
    if det is None and control and detector.parece_cara(img) is False:
        raise NoPareceCara("La imagen no parece una cara (el detector no ve ninguna en el recorte)")
    cara = preprocesado.normalizar(det.cara if det else img)
    maximo = _modelo().limites.get("residuo_max")
    if maximo is not None and (det is None or control) and _modelo().residuo(cara) > maximo:
        raise NoPareceCara("La imagen no se parece a una cara alineada (PCA no la puede representar)")
    return _modelo().extraer(cara), det, cara


def _template_desde_foto(foto, con_detector: bool, control: bool = False) -> np.ndarray:
    return extraer(foto, con_detector, control)[0]


def validar(template) -> np.ndarray:
    try:
        t = np.asarray(template, dtype=np.float32).reshape(-1)
    except (TypeError, ValueError) as e:
        raise TemplateInvalido("El template no es un vector de números") from e
    if t.shape[0] != _modelo().dim or not np.all(np.isfinite(t)):
        raise TemplateInvalido(f"Se esperaba un vector finito de longitud {_modelo().dim}")
    lim = _modelo().limites
    norma = float(np.linalg.norm(t))
    if not lim.get("norma_min", 0.0) <= norma <= lim.get("norma_max", np.inf) or norma == 0:
        raise TemplateInvalido(f"Template imposible para una cara real (norma {norma:.2f})")
    return t


# --- núcleo común: todo acaba aquí --------------------------------------------

def _validar_id(id) -> None:
    if not isinstance(id, str) or not _ID.match(id):
        raise IdInvalido(f"Id no válido: {id!r} (solo letras, números y _ ( ) . -)")


def inscribir_t(id: str, template, actualizar: bool = False) -> None:
    """Inscribe un id nuevo. Un id ya inscrito no se amplía salvo con actualizar=True y una
    muestra que ya verifique contra él: así nadie puede añadir su cara a la identidad de otro."""
    _validar_id(id)
    t = validar(template)
    base = bd.cargar()
    if id in base:
        if not actualizar:
            raise IdYaInscrito(f"'{id}' ya está inscrito (para añadir otra muestra suya: actualizar=True)")
        if not comparador.acepta(comparador.distancia_a_id(t, base[id]), umbral()):
            raise InscripcionRechazada(f"La nueva muestra no verifica contra '{id}'")
    bd.guardar(id, t)


def _inscribir_carga_inicial(id: str, template) -> None:
    """Solo para scripts/montar.py (quien administra el sistema): añade un template sin la regla
    de ids ya inscritos, para cargar varias fotos por persona en el montaje."""
    _validar_id(id)
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

def inscribir_sd(id: str, foto, actualizar: bool = False) -> None:
    inscribir_t(id, _template_desde_foto(foto, con_detector=False), actualizar)


def verificar_sd(id: str, foto) -> bool:
    return verificar_t(id, _template_desde_foto(foto, con_detector=False, control=True))


def identificar_sd(foto) -> str | None:
    return identificar_t(_template_desde_foto(foto, con_detector=False, control=True))


# --- pipeline completo ------------------------------------------------------------

def inscribir(id: str, foto, actualizar: bool = False) -> None:
    inscribir_t(id, _template_desde_foto(foto, con_detector=True), actualizar)


def verificar(id: str, foto) -> bool:
    return verificar_t(id, _template_desde_foto(foto, con_detector=True, control=True))


def identificar(foto) -> str | None:
    return identificar_t(_template_desde_foto(foto, con_detector=True, control=True))

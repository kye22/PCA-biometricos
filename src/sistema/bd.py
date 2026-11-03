"""Base de datos en .csv. Responsable: módulo 3 (BD, comparador y API).

Formato: una fila por template -> `id,template`. Una persona puede tener varias filas (varias
fotos inscritas). El id va en claro (para buscar); el template va cifrado y autenticado con
AES-256-GCM, con el id como dato asociado (seguridad.py). Junto al .csv, `bd.firma` guarda un
HMAC del archivo entero.

Al cargar se exige que todo cuadre; si no, Manipulado y no se decide nada (falla cerrado):
- quien lea el .csv no ve templates: no puede reconstruir caras ni reutilizarlos en verificar_t;
- quien escriba no puede añadir su template a nombre de otro (no tiene la clave), mover una fila
  a otro id, retocarla, ni borrar o duplicar filas sin que se note.
"""
import csv
import io
from pathlib import Path

import numpy as np

from . import config, seguridad
from .excepciones import Manipulado


def _ruta(ruta: Path | None) -> Path:
    return Path(ruta) if ruta is not None else config.RUTA_BD


def _ruta_firma(ruta: Path) -> Path:
    return ruta.with_suffix(".firma")


def _firmar(ruta: Path) -> None:
    _ruta_firma(ruta).write_text(seguridad.firmar(ruta.read_bytes(), "bd"), encoding="utf-8")


def guardar(id: str, template: np.ndarray, ruta: Path | None = None) -> None:
    ruta = _ruta(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.exists():
        cargar(ruta)   # no se añade nada a una BD manipulada (la firma nueva la "legalizaría")
    nuevo = not ruta.exists()
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["id", "template"])
        w.writerow([id, seguridad.cifrar(id, template)])
    _firmar(ruta)


def cargar(ruta: Path | None = None) -> dict[str, list[np.ndarray]]:
    """id -> lista de templates. BD inexistente = vacía. Lanza Manipulado si no cuadra."""
    ruta = _ruta(ruta)
    bd: dict[str, list[np.ndarray]] = {}
    firma = _ruta_firma(ruta)
    if not ruta.exists():
        if firma.exists():
            raise Manipulado(f"{ruta.name} ha desaparecido pero su firma sigue ahí")
        return bd
    datos = ruta.read_bytes()
    seguridad.comprobar(datos, firma.read_text(encoding="utf-8").strip() if firma.exists() else "", "bd",
                        ruta.name)
    for fila in csv.DictReader(io.StringIO(datos.decode("utf-8"), newline="")):
        bd.setdefault(fila["id"], []).append(seguridad.descifrar(fila["id"], fila["template"]))
    return bd


def borrar(ruta: Path | None = None) -> None:
    ruta = _ruta(ruta)
    ruta.unlink(missing_ok=True)
    _ruta_firma(ruta).unlink(missing_ok=True)

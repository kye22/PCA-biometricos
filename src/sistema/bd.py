"""Base de datos en .csv. Responsable: módulo 3 (BD, comparador y API).

Formato: una fila por template -> `id,template`, con el template como floats separados por
espacios. Una persona puede tener varias filas (varias fotos inscritas).
Provisional: en claro y sin integridad. Las defensas (firma, cifrado...) las decide el módulo 5.
"""
import csv
from pathlib import Path

import numpy as np

from . import config


def _ruta(ruta: Path | None) -> Path:
    return Path(ruta) if ruta is not None else config.RUTA_BD


def guardar(id: str, template: np.ndarray, ruta: Path | None = None) -> None:
    ruta = _ruta(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not ruta.exists()
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["id", "template"])
        w.writerow([id, " ".join(f"{x:.6f}" for x in template)])


def cargar(ruta: Path | None = None) -> dict[str, list[np.ndarray]]:
    """id -> lista de templates. BD inexistente = vacía."""
    ruta = _ruta(ruta)
    bd: dict[str, list[np.ndarray]] = {}
    if not ruta.exists():
        return bd
    with open(ruta, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            t = np.array(fila["template"].split(), dtype=np.float32)
            bd.setdefault(fila["id"], []).append(t)
    return bd


def borrar(ruta: Path | None = None) -> None:
    _ruta(ruta).unlink(missing_ok=True)

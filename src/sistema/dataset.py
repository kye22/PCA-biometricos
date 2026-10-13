"""Acceso al dataset de fotos en disco.

Estructura esperada:  datos/fotos/<id>/<cualquier_nombre>.jpg|png|...
El nombre de la carpeta es el id de la persona (p. ej. `Alvaro_Arbeloa_Coca`).
"""
from pathlib import Path

from . import config

EXTENSIONES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".pgm"}


def listar(raiz: Path | None = None) -> dict[str, list[Path]]:
    """id -> fotos ordenadas por nombre (orden estable = reparto train/test reproducible)."""
    raiz = Path(raiz) if raiz is not None else config.RUTA_FOTOS
    if not raiz.exists():
        raise FileNotFoundError(f"No existe {raiz}; coloca las fotos en datos/fotos/<id>/")
    return {
        d.name: sorted(p for p in d.iterdir() if p.suffix.lower() in EXTENSIONES)
        for d in sorted(raiz.iterdir())
        if d.is_dir()
    }


def separar(fotos: dict[str, list[Path]], n_inscripcion: int):
    """Primeras n fotos de cada persona para inscribir, el resto para probar."""
    inscripcion = {i: fs[:n_inscripcion] for i, fs in fotos.items()}
    prueba = {i: fs[n_inscripcion:] for i, fs in fotos.items()}
    return inscripcion, prueba

"""Acceso a las fotos en disco.

Inscripción (carpeta plana, formato del dataset):  datos/fotos/nombre_apellido_AAAA.ext
    id = nombre del archivo sin el año ni la extensión, en minúsculas y SIN corregir erratas
    (tiene que coincidir con los nombres del dataset). Ej.: serenna_williams_2017.jpg -> serenna_williams
Extra (Arbeloa y otros nuestros):                 datos/extra/   mismo formato
Pruebas (anexo, NO se inscriben):                 datos/pruebas/<id>/*.jpg
    Si <id> está inscrito -> pruebas genuinas; si no -> desconocidos (impostores).
"""
import re
import tarfile
from pathlib import Path

EXTENSIONES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".avif", ".pgm"}
_ANIO = re.compile(r"_\d{4}$")


def id_desde_archivo(ruta: Path) -> str:
    return _ANIO.sub("", Path(ruta).stem).lower()


def _fotos(carpeta: Path) -> list[Path]:
    if not carpeta.exists():
        return []
    return sorted(p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONES)


def listar_inscripcion(*carpetas: Path) -> list[tuple[str, Path]]:
    """[(id, foto), ...] de las carpetas planas de inscripción, en orden estable."""
    return [(id_desde_archivo(f), f) for c in carpetas for f in _fotos(Path(c))]


def listar_pruebas(raiz: Path) -> dict[str, list[Path]]:
    """id -> fotos de prueba (una subcarpeta por persona)."""
    raiz = Path(raiz)
    if not raiz.exists():
        return {}
    return {d.name.lower(): _fotos(d) for d in sorted(raiz.iterdir()) if d.is_dir() and _fotos(d)}


def extraer_dataset(tar: Path, destino: Path) -> int:
    """Descomprime el .tar.gz del dataset dejando las fotos planas en `destino`. -> nº de fotos."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    n = 0
    with tarfile.open(tar, "r:gz") as t:
        for m in t.getmembers():
            if not m.isfile() or Path(m.name).suffix.lower() not in EXTENSIONES:
                continue
            datos = t.extractfile(m).read()             # sin extractall: nada de rutas raras
            (destino / Path(m.name).name).write_bytes(datos)
            n += 1
    return n

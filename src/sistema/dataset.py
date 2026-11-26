"""Acceso a las fotos en disco.

Inscripción (carpeta plana, formato del dataset):  datos/fotos/nombre_apellido_AAAA.ext
    id = nombre del archivo sin el año ni la extensión, en minúsculas y SIN corregir erratas
    (tiene que coincidir con los nombres del dataset). Ej.: serenna_williams_2017.jpg -> serenna_williams
Extra (Arbeloa y otros nuestros):                 datos/extra/   mismo formato
Fotos adicionales de un inscrito:                 datos/extra/<id>/*.jpg (varios templates por persona)
Pruebas (anexo, NO se inscriben):                 datos/pruebas/<id>/*.jpg
    Si <id> está inscrito -> pruebas genuinas; si no -> desconocidos (impostores).
"""
import re
import json
import hashlib
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
    """[(id, foto), ...] de las carpetas de inscripción, en orden estable.

    Fotos sueltas: el id sale del nombre del archivo. Subcarpetas <id>/: fotos adicionales de esa
    persona (se inscriben todas; la persona queda con varios templates)."""
    pares = []
    for c in map(Path, carpetas):
        pares += [(id_desde_archivo(f), f) for f in _fotos(c)]
        if c.exists():
            for d in sorted(x for x in c.iterdir() if x.is_dir()):
                pares += [(d.name.lower(), f) for f in _fotos(d)]
    return pares


def listar_pruebas(raiz: Path) -> dict[str, list[Path]]:
    """id -> fotos de prueba (una subcarpeta por persona)."""
    raiz = Path(raiz)
    if not raiz.exists():
        return {}
    return {d.name.lower(): _fotos(d) for d in sorted(raiz.iterdir()) if d.is_dir() and _fotos(d)}


GRUPOS_PARTICION = ("inscripcion", "calibracion", "prueba", "desconocidos")


def leer_particion(ruta: Path, raiz: Path) -> dict[str, list[tuple[str, Path]]]:
    """Carga y audita un manifiesto sin mover ni modificar fotografías.

    El manifiesto contiene cuatro listas de {"id": ..., "foto": "ruta/relativa"}.
    No permite utilizar la misma imagen (ni su duplicado exacto) en dos grupos.
    """
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if datos.get("version") != 1:
        raise ValueError("Versión de partición no admitida (esperada: 1)")
    raiz = Path(raiz).resolve()
    grupos = {}
    usados = {}
    huellas = {}
    for grupo in GRUPOS_PARTICION:
        entradas = datos.get(grupo, [])
        if not isinstance(entradas, list):
            raise ValueError(f"{grupo} debe ser una lista")
        grupos[grupo] = []
        for e in entradas:
            if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not isinstance(e.get("foto"), str):
                raise ValueError(f"Entrada mal formada en {grupo}: {e!r}")
            id_ = e["id"].lower()
            if not id_ or not e["foto"]:
                raise ValueError("Una entrada tiene un id o una foto vacíos")
            f = (raiz / e["foto"]).resolve()
            if not f.is_relative_to(raiz) or not f.is_file():
                raise ValueError(f"Foto inexistente o fuera del repositorio: {e['foto']}")
            if f in usados:
                raise ValueError(f"Foto repetida en {usados[f]} y {grupo}: {f.name}")
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
            if digest in huellas:
                raise ValueError(f"Fotos con contenido idéntico en {huellas[digest]} y {grupo}: {f.name}")
            usados[f], huellas[digest] = grupo, grupo
            grupos[grupo].append((id_, f))
    if not grupos["inscripcion"]:
        raise ValueError("La partición no contiene fotos de inscripción")
    ids = {i for i, _ in grupos["inscripcion"]}
    if any(i not in ids for g in ("calibracion", "prueba") for i, _ in grupos[g]):
        raise ValueError("Una foto genuina pertenece a una identidad no inscrita")
    if any(i in ids for i, _ in grupos["desconocidos"]):
        raise ValueError("Una foto de desconocido pertenece a una identidad inscrita")
    return grupos


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

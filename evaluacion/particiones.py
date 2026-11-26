"""Genera una partición reproducible y sin solapamientos de fotografías.

    python evaluacion/particiones.py --semilla 42

Regla: la foto del profesor (o Arbeloa suelta) se reserva para inscripción.
Si hay al menos dos extras, uno va a calibración y los demás a prueba;
si hay un solo extra, va a prueba. datos/pruebas/<id> se reserva para prueba.
Los desconocidos son ids que NO aparecen en inscripción.
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sistema import config, dataset


def preparar_dataset() -> None:
    if config.RUTA_FOTOS.exists() and any(config.RUTA_FOTOS.iterdir()):
        return
    if not config.RUTA_DATASET.is_file():
        raise FileNotFoundError(f"Coloca {config.RUTA_DATASET.name} en la raíz del repo")
    print(f"Extrayendo fotos del profesor: {dataset.extraer_dataset(config.RUTA_DATASET, config.RUTA_FOTOS)}")


def generar(semilla: int = 42) -> dict:
    preparar_dataset()
    del_profesor = defaultdict(list)
    for id_, f in dataset.listar_inscripcion(config.RUTA_FOTOS):
        del_profesor[id_].append(f)
    de_extra = defaultdict(list)
    for id_, f in dataset.listar_inscripcion(config.RUTA_EXTRA):
        de_extra[id_].append(f)
    identidades = sorted(set(del_profesor) | set(de_extra))
    particion = {"version": 1, "semilla": semilla,
                 **{g: [] for g in dataset.GRUPOS_PARTICION}}

    def agregar(grupo: str, id_: str, foto: Path) -> None:
        try:
            relativa = foto.resolve().relative_to(config.RAIZ.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError(f"La foto debe estar dentro del repositorio: {foto}") from exc
        particion[grupo].append({"id": id_, "foto": relativa})

    rng = random.Random(semilla)
    for id_ in identidades:
        originales = sorted(del_profesor[id_])
        extras = sorted(de_extra[id_])
        # Solo la foto suelta de Arbeloa puede actuar como original alternativo.
        if not originales:
            sueltas = [f for f in extras if f.parent == config.RUTA_EXTRA]
            if not sueltas:
                raise ValueError(f"{id_} no tiene una foto principal de inscripción")
            originales = [sueltas[0]]
            extras.remove(sueltas[0])
        for f in originales:
            agregar("inscripcion", id_, f)
        rng.shuffle(extras)
        if len(extras) >= 2:
            agregar("calibracion", id_, extras.pop())
        for f in extras:
            agregar("prueba", id_, f)

    inscritos = set(identidades)
    for id_, fotos in dataset.listar_pruebas(config.RUTA_PRUEBAS).items():
        for f in fotos:
            agregar("prueba" if id_ in inscritos else "desconocidos", id_, f)
    return particion


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--semilla", type=int, default=42)
    p.add_argument("--salida", type=Path, default=config.RAIZ / "evaluacion" / "particion.json")
    args = p.parse_args()
    particion = generar(args.semilla)
    # Validar antes de escribir para evitar fugas por duplicados exactos de fotos.
    salida = args.salida.resolve()
    salida.parent.mkdir(parents=True, exist_ok=True)
    provisional = salida.with_name(salida.name + ".tmp")
    try:
        provisional.write_text(json.dumps(particion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        dataset.leer_particion(provisional, config.RAIZ)
        provisional.replace(salida)
    finally:
        provisional.unlink(missing_ok=True)
    for grupo in dataset.GRUPOS_PARTICION:
        fotos = particion[grupo]
        print(f"{grupo:13s}: {len(fotos):3d} fotos, {len({f['id'] for f in fotos}):2d} identidades")
    print(f"Partición verificada: {salida}")


if __name__ == "__main__":
    main()

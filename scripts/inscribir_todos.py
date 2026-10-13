"""Crea la BD inscribiendo las primeras N fotos de cada persona de datos/fotos.

    python scripts/inscribir_todos.py [--por-persona 1] [--sd] [--conservar]

Por defecto borra la BD anterior. Las fotos no usadas quedan para evaluación.
"""
import argparse

from sistema import api, bd, config, dataset
from sistema.excepciones import CaraNoEncontrada


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fotos", default=config.RUTA_FOTOS)
    p.add_argument("--por-persona", type=int, default=1)
    p.add_argument("--sd", action="store_true", help="las fotos ya son caras recortadas")
    p.add_argument("--conservar", action="store_true", help="no borrar la BD existente")
    args = p.parse_args()

    if not args.conservar:
        bd.borrar()
    inscribir = api.inscribir_sd if args.sd else api.inscribir

    inscripcion, _ = dataset.separar(dataset.listar(args.fotos), args.por_persona)
    ok, fallos = 0, []
    for id_, fotos in inscripcion.items():
        for f in fotos:
            try:
                inscribir(id_, f)
                ok += 1
            except CaraNoEncontrada:
                fallos.append(f)

    print(f"Inscritos {ok} templates de {len(inscripcion)} personas -> {config.RUTA_BD}")
    for f in fallos:
        print(f"  sin cara: {f}")


if __name__ == "__main__":
    main()

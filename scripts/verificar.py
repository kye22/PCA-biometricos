"""Prueba rápida de verificación de una foto contra un id.

    python scripts/verificar.py <id> <foto> [--sd]
"""
import argparse

from sistema import api


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("id")
    p.add_argument("foto")
    p.add_argument("--sd", action="store_true", help="omitir el detector de caras")
    args = p.parse_args()

    verificar = api.verificar_sd if args.sd else api.verificar
    print("ACEPTADO" if verificar(args.id, args.foto) else "RECHAZADO")


if __name__ == "__main__":
    main()

"""Prueba rápida de identificación de una foto.

    python scripts/identificar.py <foto> [--sd]
"""
import argparse

from sistema import api


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("foto")
    p.add_argument("--sd", action="store_true", help="omitir el detector de caras")
    args = p.parse_args()

    identificar = api.identificar_sd if args.sd else api.identificar
    print(identificar(args.foto) or "DESCONOCIDO")


if __name__ == "__main__":
    main()

"""Ataque de ejemplo: el atacante puede ESCRIBIR en la BD.

Suplantación: añade su propio template bajo el id de la víctima. Después, una foto del atacante
verifica como la víctima. Contra la BD provisional (sin integridad) el ataque funciona.

    python ataques/escritura_bd.py <id_victima> <foto_atacante> [--sd]

OJO: modifica la BD. Haz copia o regenérala luego con scripts/montar.py.
Plantilla para el resto de ataques: qué se asume del atacante, qué hace, resultado esperado.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # usar sin instalar

import argparse

from sistema import api, bd


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("victima")
    p.add_argument("foto_atacante")
    p.add_argument("--sd", action="store_true")
    args = p.parse_args()

    verificar = api.verificar_sd if args.sd else api.verificar
    print(f"Antes del ataque, ¿el atacante pasa como {args.victima}? {verificar(args.victima, args.foto_atacante)}")

    template, _, _ = api.extraer(args.foto_atacante, con_detector=not args.sd)
    bd.guardar(args.victima, template)  # escritura directa en el CSV, sin pasar por la API

    print(f"Después del ataque: {verificar(args.victima, args.foto_atacante)}")


if __name__ == "__main__":
    main()

"""Ataque de ejemplo: el atacante puede ESCRIBIR en la BD.

Suplantación: añade su propio template bajo el id de la víctima. Después, una foto del atacante
verifica como la víctima. Contra la BD provisional (sin integridad) el ataque funciona.

    python ataques/escritura_bd.py <id_victima> <foto_atacante> [--sd]

OJO: modifica la BD. Haz copia o regenérala luego con scripts/inscribir_todos.py.
Plantilla para el resto de ataques: qué se asume del atacante, qué hace, resultado esperado.
"""
import argparse

from sistema import api, bd, detector, imagen, preprocesado


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("victima")
    p.add_argument("foto_atacante")
    p.add_argument("--sd", action="store_true")
    args = p.parse_args()

    verificar = api.verificar_sd if args.sd else api.verificar
    print(f"Antes del ataque, ¿el atacante pasa como {args.victima}? {verificar(args.victima, args.foto_atacante)}")

    img = imagen.leer(args.foto_atacante)
    cara = img if args.sd else detector.detectar(img)
    bd.guardar(args.victima, api._modelo().extraer(preprocesado.normalizar(cara)))  # escritura directa

    print(f"Después del ataque: {verificar(args.victima, args.foto_atacante)}")


if __name__ == "__main__":
    main()

"""Contrasta los tres niveles de entrada sin INSCRIBIR ni modificar la BD.

    python ataques/bypass.py adele datos/pruebas/adele/foto.jpg

Para _sd se proporciona deliberadamente el recorte generado por el detector. Para _t,
un vector derivado de la foto. Esto muestra qué controles se saltan, no una suplantación probada.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sistema import api, detector, imagen, preprocesado


def intentar(nombre: str, funcion, *args) -> None:
    try:
        print(f"{nombre:20s}: {funcion(*args)}")
    except Exception as exc:
        print(f"{nombre:20s}: {type(exc).__name__} ({exc})")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("id", help="identidad inscrita cuya verificación se prueba")
    p.add_argument("foto", type=Path)
    args = p.parse_args()
    print("Comparando exactamente la misma fotografía en los tres niveles:")
    intentar("verificar", api.verificar, args.id, args.foto)
    try:
        cara = detector.localizar(imagen.leer(args.foto)).cara
    except Exception as exc:
        raise SystemExit(f"No se ha podido obtener un recorte para probar _sd y _t: {exc}")
    intentar("verificar_sd", api.verificar_sd, args.id, cara)
    try:
        t = api._modelo().extraer(preprocesado.normalizar(cara))
    except Exception as exc:
        raise SystemExit(f"No se ha podido obtener un template para _t: {exc}")
    intentar("verificar_t", api.verificar_t, args.id, t)
    print("La comparación no modifica la BD. _t recibe directamente el template.")


if __name__ == "__main__":
    main()

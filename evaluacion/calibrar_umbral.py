"""Estima un umbral usando EXCLUSIVAMENTE el conjunto de calibración.

    python evaluacion/calibrar_umbral.py --far 0.02
    python evaluacion/calibrar_umbral.py --far 0.02 --aplicar

--aplicar modifica modelos/pca.npz y actualiza su firma. No usa las fotos de prueba.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from sistema import api, config, seguridad
from sistema.excepciones import ErrorSistema
from evaluacion.evaluar import obtener_scores
from evaluacion.metricas import far_frr, umbral_para_far


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifiesto", type=Path, default=config.RAIZ / "evaluacion" / "particion.json")
    p.add_argument("--far", type=float, default=0.02, help="FAR objetivo de verificación 1:1")
    p.add_argument("--aplicar", action="store_true", help="guardar el umbral en el modelo firmado")
    args = p.parse_args()
    try:
        resultado = obtener_scores(args.manifiesto, "calibracion")
        if not resultado["n_genuinos"]:
            raise ValueError("No hay imágenes de calibración genuinas")
        imp = np.array([float("inf") if d is None else d for d in resultado["impostoras"]])
        gen = np.array([float("inf") if d is None else d for d in resultado["genuinas"]])
        nuevo = umbral_para_far(imp, args.far)
        fmr, fnmr = far_frr(gen, imp, [nuevo])
    except (OSError, ValueError, ErrorSistema) as exc:
        p.exit(2, f"No se puede calibrar: {exc}\n")
    print(f"Umbral propuesto: {nuevo:.5f}")
    print(f"FAR de calibración: {fmr[0]:.2%} ({len(imp)} intentos 1:1)")
    print(f"FRR de calibración: {fnmr[0]:.2%} ({len(gen)} intentos genuinos)")
    print("IMPORTANTE: estas tasas son de calibración, no de evaluación final.")
    if args.aplicar:
        modelo = api._modelo()
        modelo.umbral = nuevo
        modelo.guardar(config.RUTA_MODELO, seguridad.clave_modelo())
        api.recargar()
        print(f"Umbral guardado y firmado en {config.RUTA_MODELO}")
        if config.UMBRAL is not None:
            print("AVISO: SISTEMA_UMBRAL sigue sobrescribiendo el umbral del modelo")


if __name__ == "__main__":
    main()

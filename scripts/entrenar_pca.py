"""Entrena el modelo PCA con las fotos de datos/fotos y lo guarda en modelos/pca.npz.

    python scripts/entrenar_pca.py [--fotos datos/fotos] [--componentes 50] [--sd]
"""
import argparse

import numpy as np

from sistema import config, dataset, detector, imagen, preprocesado
from sistema.excepciones import CaraNoEncontrada
from sistema.pca import ModeloPCA


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fotos", default=config.RUTA_FOTOS)
    p.add_argument("--componentes", type=int, default=config.N_COMPONENTES)
    p.add_argument("--salida", default=config.RUTA_MODELO)
    p.add_argument("--sd", action="store_true", help="las fotos ya son caras recortadas (no detectar)")
    args = p.parse_args()

    caras, fallos = [], 0
    for id_, fotos in dataset.listar(args.fotos).items():
        for f in fotos:
            img = imagen.leer(f)
            try:
                cara = img if args.sd else detector.detectar(img)
            except CaraNoEncontrada:
                fallos += 1
                continue
            caras.append(preprocesado.normalizar(cara))

    if not caras:
        raise SystemExit("No hay caras para entrenar")
    modelo = ModeloPCA.entrenar(np.stack(caras), args.componentes)
    modelo.guardar(args.salida)
    print(f"PCA entrenado: {len(caras)} caras ({fallos} sin cara detectada), "
          f"K={modelo.dim} -> {args.salida}")


if __name__ == "__main__":
    main()

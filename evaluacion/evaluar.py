"""Evaluación provisional: distancias genuinas/impostoras sobre las fotos no inscritas.

    python evaluacion/evaluar.py [--por-persona 1] [--sd]

Requiere modelo entrenado y BD creada con el mismo --por-persona (scripts/inscribir_todos.py).
Pendiente (módulo 4): curvas ROC/DET, CMC, gráficas, protocolo definitivo.
"""
import argparse

import numpy as np

from metricas import eer, rank1
from sistema import api, bd, comparador, config, dataset, detector, imagen, preprocesado
from sistema.excepciones import CaraNoEncontrada


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fotos", default=config.RUTA_FOTOS)
    p.add_argument("--por-persona", type=int, default=1)
    p.add_argument("--sd", action="store_true")
    args = p.parse_args()

    modelo = api._modelo()
    base = bd.cargar()
    _, prueba = dataset.separar(dataset.listar(args.fotos), args.por_persona)

    genuinas, impostoras, aciertos, sin_cara = [], [], [], 0
    for id_real, fotos in prueba.items():
        if id_real not in base:
            continue
        for f in fotos:
            img = imagen.leer(f)
            try:
                cara = img if args.sd else detector.detectar(img)
            except CaraNoEncontrada:
                sin_cara += 1
                continue
            t = modelo.extraer(preprocesado.normalizar(cara))
            dists = {i: comparador.distancia_a_id(t, ts) for i, ts in base.items()}
            genuinas.append(dists[id_real])
            impostoras.extend(d for i, d in dists.items() if i != id_real)
            aciertos.append(min(dists, key=dists.get) == id_real)

    if not genuinas:
        raise SystemExit("No hay fotos de prueba (¿solo hay una foto por persona?)")
    valor_eer, umbral = eer(np.array(genuinas), np.array(impostoras))
    print(f"Pruebas: {len(genuinas)} genuinas, {len(impostoras)} impostoras, {sin_cara} sin cara")
    print(f"EER: {valor_eer:.2%}  (umbral {umbral:.3f}; actual en config: {config.UMBRAL})")
    print(f"Identificación rank-1: {rank1(aciertos):.2%}")


if __name__ == "__main__":
    main()

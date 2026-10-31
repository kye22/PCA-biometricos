"""Evaluación con el anexo de pruebas: fotos que NO se han usado para inscribir.

    python evaluacion/evaluar.py

Estructura: datos/pruebas/<id>/*.jpg
- <id> inscrito      -> pruebas genuinas (debería identificarse como <id>)
- <id> no inscrito   -> desconocido (debería salir DESCONOCIDO); útil para gemelos y parecidos

Requiere haber ejecutado scripts/montar.py.
Pendiente (módulo 4): curvas ROC/DET, CMC, gráficas.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # usar sin instalar

import numpy as np

from metricas import eer, rank1
from sistema import analisis, bd, config, dataset
from sistema.excepciones import CaraNoEncontrada


def main():
    pruebas = dataset.listar_pruebas(config.RUTA_PRUEBAS)
    if not pruebas:
        sys.exit(f"No hay fotos en {config.RUTA_PRUEBAS}/<id>/ (anexo de pruebas)")
    inscritos = set(bd.cargar())

    genuinas, impostoras, aciertos, sin_cara = [], [], [], []
    falsos_aceptados, falsos_rechazos = [], []
    umbral = None
    for id_real, fotos in pruebas.items():
        for f in fotos:
            try:
                a = analisis.analizar(f)
            except CaraNoEncontrada:
                sin_cara.append(f)
                continue
            umbral = a.umbral
            dist = {c.id: c.distancia for c in a.ranking}
            if id_real in inscritos:
                genuinas.append(dist[id_real])
                impostoras.extend(d for i, d in dist.items() if i != id_real)
                aciertos.append(a.mejor.id == id_real)
                if a.identificado != id_real:
                    falsos_rechazos.append((f, a.identificado, a.mejor.id, a.mejor.distancia))
            else:
                impostoras.extend(dist.values())
                if a.identificado is not None:
                    falsos_aceptados.append((f, a.identificado, a.mejor.distancia))

    print(f"Fotos de prueba: {sum(map(len, pruebas.values()))} ({len(sin_cara)} sin cara detectada)")
    print(f"Umbral actual: {umbral:.2f}")
    if genuinas:
        g = np.array(genuinas)
        valor_eer, u_eer = eer(g, np.array(impostoras))
        print(f"Genuinas: {len(g)} · distancia mediana a sí mismo {np.median(g):.1f}")
        print(f"Identificación rank-1 (sin umbral): {rank1(aciertos):.1%}")
        print(f"Tasa de falso rechazo con el umbral actual: {np.mean(g > umbral):.1%}")
        print(f"EER: {valor_eer:.1%} con umbral {u_eer:.2f}")
    print(f"Desconocidos aceptados como alguien: {len(falsos_aceptados)}")
    for f, quien, d in falsos_aceptados:
        print(f"  {f.parent.name}/{f.name} -> {quien} (d={d:.1f})")
    for f, ident, mejor, d in falsos_rechazos[:15]:
        print(f"  no reconocido: {f.parent.name}/{f.name} -> {ident or 'DESCONOCIDO'} (más cercano {mejor}, d={d:.1f})")


if __name__ == "__main__":
    main()

"""Hoja de contactos del anexo para revisarlo a ojo: una fila por persona.

    python scripts/hoja_anexo.py [salida.jpg]      (por defecto datos/pruebas/hoja.jpg)

Cada fila: [foto inscrita (borde verde)] + [fotos de prueba]. Todas como caras alineadas.
Si en una fila aparece otra persona, borra ese archivo de datos/pruebas/<id>/ (y su línea
de fuentes.csv).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # usar sin instalar

import json

import cv2
import numpy as np

from sistema import config, dataset, detector, imagen

LADO = 90
COLUMNAS = 1 + 4


def cara(ruta) -> np.ndarray:
    try:
        c = cv2.resize(detector.localizar(imagen.leer(ruta)).cara, (LADO, LADO))
    except Exception:
        c = np.full((LADO, LADO), 40, np.uint8)
    return cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)


def main():
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else config.RUTA_PRUEBAS / "hoja.jpg"
    inscritos = json.loads(config.RUTA_INSCRITOS.read_text(encoding="utf-8")) if config.RUTA_INSCRITOS.exists() else {}
    filas = []
    for id_, fotos in dataset.listar_pruebas(config.RUTA_PRUEBAS).items():
        celdas = []
        if id_ in inscritos:
            ref = cara(config.RAIZ / inscritos[id_][0]["foto"])
            celdas.append(cv2.rectangle(ref, (0, 0), (LADO - 1, LADO - 1), (0, 200, 0), 3))
        else:
            celdas.append(np.full((LADO, LADO, 3), (0, 0, 120), np.uint8))   # no inscrito
        celdas += [cara(f) for f in fotos[:COLUMNAS - 1]]
        celdas += [np.zeros((LADO, LADO, 3), np.uint8)] * (COLUMNAS - len(celdas))
        etiqueta = np.zeros((16, LADO * COLUMNAS, 3), np.uint8)
        cv2.putText(etiqueta, id_, (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        filas.append(np.vstack([etiqueta, np.hstack(celdas)]))
    if not filas:
        sys.exit("No hay fotos en datos/pruebas/")
    # en dos columnas de filas para que la imagen no sea demasiado alta
    mitad = (len(filas) + 1) // 2
    izq, der = filas[:mitad], filas[mitad:]
    der += [np.zeros_like(filas[0])] * (len(izq) - len(der))
    hoja = np.hstack([np.vstack(izq), np.full((sum(f.shape[0] for f in izq), 8, 3), 255, np.uint8), np.vstack(der)])
    cv2.imencode(".jpg", hoja)[1].tofile(str(salida))
    print(f"{len(filas)} personas -> {salida}")


if __name__ == "__main__":
    main()

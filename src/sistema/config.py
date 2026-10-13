"""Parámetros globales del sistema. Se pueden sobrescribir con variables de entorno."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# Rutas
RUTA_BD = Path(os.getenv("SISTEMA_BD", RAIZ / "datos" / "bd.csv"))
RUTA_MODELO = Path(os.getenv("SISTEMA_MODELO", RAIZ / "modelos" / "pca.npz"))
RUTA_FOTOS = Path(os.getenv("SISTEMA_FOTOS", RAIZ / "datos" / "fotos"))

# Preprocesado: tamaño (ancho, alto) de la cara normalizada
TAM_CARA = (100, 100)

# PCA
N_COMPONENTES = int(os.getenv("SISTEMA_COMPONENTES", 50))

# Comparador: distancia máxima para aceptar (provisional, lo fija evaluación)
UMBRAL = float(os.getenv("SISTEMA_UMBRAL", 10.0))

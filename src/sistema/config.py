"""Parámetros globales del sistema. Se pueden sobrescribir con variables de entorno."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# Rutas
RUTA_DATASET = Path(os.getenv("SISTEMA_DATASET", RAIZ / "Dataset.tar.gz"))  # el dataset
RUTA_FOTOS = Path(os.getenv("SISTEMA_FOTOS", RAIZ / "datos" / "fotos"))      # inscripción (plana)
RUTA_EXTRA = Path(os.getenv("SISTEMA_EXTRA", RAIZ / "datos" / "extra"))      # Arbeloa, etc.
RUTA_PRUEBAS = Path(os.getenv("SISTEMA_PRUEBAS", RAIZ / "datos" / "pruebas"))  # anexo: <id>/*.jpg
RUTA_BD = Path(os.getenv("SISTEMA_BD", RAIZ / "datos" / "bd.csv"))
RUTA_INSCRITOS = Path(os.getenv("SISTEMA_INSCRITOS", RAIZ / "datos" / "inscritos.json"))
RUTA_MODELO = Path(os.getenv("SISTEMA_MODELO", RAIZ / "modelos" / "pca.npz"))
RUTA_YUNET = RAIZ / "modelos" / "face_detection_yunet_2023mar.onnx"   # detector de caras

# Cara normalizada (ancho, alto)
TAM_CARA = (100, 100)

# PCA
N_COMPONENTES = int(os.getenv("SISTEMA_COMPONENTES", 50))

# Umbral de distancia para aceptar. Por defecto el que calcula montar.py y se guarda dentro del
# modelo; esta variable solo lo sobrescribe (útil para experimentar).
UMBRAL = float(os.environ["SISTEMA_UMBRAL"]) if "SISTEMA_UMBRAL" in os.environ else None
UMBRAL_POR_DEFECTO = 10.0  # solo si el modelo no trae umbral

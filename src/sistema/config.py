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
RUTA_MODELO = Path(os.getenv("SISTEMA_MODELO", RAIZ / "modelos" / "pca.npz"))   # modelo + umbral (montar.py)
RUTA_MODELO_BASE = RAIZ / "modelos" / "pca_base.npz"   # extractor genérico (scripts/entrenar_pca.py)
# Huella del pca_base.npz que va en git: montar.py se niega a usar otro (la imprime entrenar_pca.py)
HUELLA_MODELO_BASE = "c20b9fa59c951ccad316abf43e93b5a3b2dd6e6744b865fd16c24192b1c40df4"
RUTA_YUNET = RAIZ / "modelos" / "face_detection_yunet_2023mar.onnx"   # detector de caras
RUTA_CLAVE = Path(os.getenv("SISTEMA_CLAVE_FICHERO", RAIZ / "datos" / "clave.key"))  # secreta, fuera de git

# Cara normalizada (ancho, alto)
TAM_CARA = (100, 100)

# PCA
N_COMPONENTES = int(os.getenv("SISTEMA_COMPONENTES", 50))

# Umbral de distancia para aceptar. Por defecto el que calcula montar.py y se guarda dentro del
# modelo; esta variable solo lo sobrescribe (útil para experimentar).
UMBRAL = float(os.environ["SISTEMA_UMBRAL"]) if "SISTEMA_UMBRAL" in os.environ else None
UMBRAL_POR_DEFECTO = 0.5  # distancia coseno; solo si el modelo no trae umbral

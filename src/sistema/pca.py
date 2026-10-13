"""Extractor PCA (eigenfaces). Responsable: módulo 2 (PCA).

Provisional: PCA estándar por SVD sobre caras normalizadas.
Pendiente: elegir nº de componentes por varianza explicada, descartar las primeras
componentes (iluminación), whitening, etc.
"""
from pathlib import Path

import numpy as np

from .excepciones import ModeloNoEntrenado


class ModeloPCA:
    def __init__(self, media: np.ndarray, componentes: np.ndarray):
        self.media = media                # (D,)
        self.componentes = componentes    # (K, D), filas = eigenfaces

    @property
    def dim(self) -> int:
        return self.componentes.shape[0]

    @classmethod
    def entrenar(cls, caras: np.ndarray, n_componentes: int) -> "ModeloPCA":
        """caras: (N, alto, ancho) normalizadas -> modelo con K = min(n_componentes, N) eigenfaces."""
        X = caras.reshape(len(caras), -1).astype(np.float64)
        media = X.mean(axis=0)
        _, _, vt = np.linalg.svd(X - media, full_matrices=False)
        k = min(n_componentes, vt.shape[0])
        return cls(media.astype(np.float32), vt[:k].astype(np.float32))

    def extraer(self, cara: np.ndarray) -> np.ndarray:
        """Cara normalizada -> template (K,) float32."""
        return (self.componentes @ (cara.reshape(-1) - self.media)).astype(np.float32)

    def guardar(self, ruta: Path) -> None:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        np.savez(ruta, media=self.media, componentes=self.componentes)

    @classmethod
    def cargar(cls, ruta: Path) -> "ModeloPCA":
        ruta = Path(ruta)
        if not ruta.exists():
            raise ModeloNoEntrenado(f"No existe {ruta}; ejecuta scripts/entrenar_pca.py")
        datos = np.load(ruta)
        return cls(datos["media"], datos["componentes"])

"""Extractor PCA (eigenfaces). Responsable: módulo 2 (PCA).

Entrenar = calcular la cara media y las K direcciones de máxima varianza (eigenfaces).
Extraer  = proyectar una cara sobre ellas -> template de K números.
Reconstruir = camino inverso (aproximado). Ojo: esto es justo lo que permite a un atacante
que lea la BD recuperar una imagen de la cara a partir del template.

El umbral de decisión se guarda junto al modelo: un umbral solo tiene sentido para el modelo
con el que se calculó.
"""
from pathlib import Path

import numpy as np

from .excepciones import ModeloNoEntrenado


class ModeloPCA:
    def __init__(self, media: np.ndarray, componentes: np.ndarray, varianzas: np.ndarray | None = None,
                 forma: tuple[int, int] | None = None, umbral: float | None = None,
                 varianza_total: float | None = None):
        self.media = media                # (D,)
        self.componentes = componentes    # (K, D), filas = eigenfaces
        self.varianzas = varianzas if varianzas is not None else np.ones(len(componentes), np.float32)
        self.forma = forma                # (alto, ancho) de la cara, para reconstruir
        self.umbral = umbral
        self.varianza_total = varianza_total

    @property
    def dim(self) -> int:
        return self.componentes.shape[0]

    @classmethod
    def entrenar(cls, caras: np.ndarray, n_componentes: int) -> "ModeloPCA":
        """caras: (N, alto, ancho) normalizadas -> modelo con K = min(n_componentes, N-1).

        Con N caras centradas solo hay N-1 direcciones con información (la última es ruido).
        """
        X = caras.reshape(len(caras), -1).astype(np.float64)
        media = X.mean(axis=0)
        _, s, vt = np.linalg.svd(X - media, full_matrices=False)
        k = max(1, min(n_componentes, len(caras) - 1))
        varianzas = (s[:k] ** 2) / max(1, len(caras) - 1)
        total = float((s ** 2).sum() / max(1, len(caras) - 1))
        return cls(media.astype(np.float32), vt[:k].astype(np.float32), varianzas.astype(np.float32),
                   tuple(caras.shape[1:]), varianza_total=total)

    def varianza_explicada(self) -> float:
        """Fracción de la varianza total de las caras de entrenamiento que recogen las K."""
        return float(self.varianzas.sum() / self.varianza_total) if self.varianza_total else 1.0

    def extraer(self, cara: np.ndarray) -> np.ndarray:
        """Cara normalizada -> template (K,) float32."""
        return (self.componentes @ (cara.reshape(-1) - self.media)).astype(np.float32)

    def reconstruir(self, template: np.ndarray) -> np.ndarray:
        """Template -> cara aproximada (alto, ancho)."""
        cara = self.media + template @ self.componentes
        return cara.reshape(self.forma) if self.forma else cara

    def guardar(self, ruta: Path) -> None:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        np.savez(ruta, media=self.media, componentes=self.componentes, varianzas=self.varianzas,
                 forma=np.array(self.forma or (), np.int32),
                 umbral=np.array(np.nan if self.umbral is None else self.umbral),
                 varianza_total=np.array(np.nan if self.varianza_total is None else self.varianza_total))

    @classmethod
    def cargar(cls, ruta: Path) -> "ModeloPCA":
        ruta = Path(ruta)
        if not ruta.exists():
            raise ModeloNoEntrenado(f"No existe {ruta}; ejecuta scripts/montar.py")
        d = np.load(ruta)
        forma = tuple(int(x) for x in d["forma"]) if "forma" in d and d["forma"].size else None
        umbral = float(d["umbral"]) if "umbral" in d and np.isfinite(d["umbral"]) else None
        varianzas = d["varianzas"] if "varianzas" in d else None
        total = float(d["varianza_total"]) if "varianza_total" in d and np.isfinite(d["varianza_total"]) else None
        return cls(d["media"], d["componentes"], varianzas, forma, umbral, total)

"""Extractor PCA (eigenfaces). Responsable: módulo 2 (PCA).

Entrenar = calcular la cara media y las K direcciones de máxima varianza (eigenfaces).
Extraer  = proyectar una cara sobre ellas y dividir cada coeficiente por su desviación típica
           ("blanqueo") -> template de K números, todos en la misma escala. Sin blanquear, las
           primeras eigenfaces (luz, pose) dominan la distancia; blanqueado + coseno es la
           comparación que mejor funciona (evaluacion/comparar_distancias.py).
Reconstruir = camino inverso (aproximado). Ojo: esto es justo lo que permite a un atacante
que lea la BD recuperar una imagen de la cara a partir del template (por eso la BD va cifrada).

Con el modelo se guardan:
- el umbral de decisión (solo tiene sentido para el modelo con el que se calculó);
- los límites de lo que es "una cara normal" (medidos en la base de entrenamiento): la norma
  del template y el error de reconstrucción. Sirven para rechazar templates fabricados (_t) e
  imágenes que no son caras (_sd);
- opcionalmente, una firma HMAC (si se guarda con clave, al cargar con clave se comprueba).
"""
import hashlib
import hmac
from pathlib import Path

import numpy as np

from .excepciones import Manipulado, ModeloNoEntrenado


class ModeloPCA:
    def __init__(self, media: np.ndarray, componentes: np.ndarray, varianzas: np.ndarray | None = None,
                 forma: tuple[int, int] | None = None, umbral: float | None = None,
                 varianza_total: float | None = None, limites: dict | None = None):
        self.media = media                # (D,)
        self.componentes = componentes    # (K, D), filas = eigenfaces
        self.varianzas = varianzas if varianzas is not None else np.ones(len(componentes), np.float32)
        self.forma = forma                # (alto, ancho) de la cara, para reconstruir
        self.umbral = umbral
        self.varianza_total = varianza_total
        self.limites = dict(limites or {})   # norma_min, norma_max, residuo_max

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

    def truncar(self, k: int) -> "ModeloPCA":
        """Las k primeras eigenfaces (PCA está anidado: son las mismas que entrenando con k)."""
        k = min(k, self.dim)
        return ModeloPCA(self.media, self.componentes[:k], self.varianzas[:k], self.forma, self.umbral,
                         self.varianza_total)

    def extraer(self, cara: np.ndarray) -> np.ndarray:
        """Cara normalizada -> template blanqueado (K,) float32."""
        return ((self.componentes @ (cara.reshape(-1) - self.media)) / np.sqrt(self.varianzas)).astype(np.float32)

    def reconstruir(self, template: np.ndarray) -> np.ndarray:
        """Template -> cara aproximada (alto, ancho)."""
        cara = self.media + (template * np.sqrt(self.varianzas)) @ self.componentes
        return cara.reshape(self.forma) if self.forma else cara

    def residuo(self, cara: np.ndarray) -> float:
        """Error de reconstrucción relativo ("distancia al espacio de caras"): 0 = la imagen es
        exactamente una combinación de eigenfaces; cerca de 1 = PCA no explica casi nada de ella."""
        x = cara.reshape(-1).astype(np.float32) - self.media
        r = x - (self.extraer(cara) * np.sqrt(self.varianzas)) @ self.componentes
        return float(np.linalg.norm(r) / (np.linalg.norm(x) + 1e-6))

    def _arrays(self) -> dict[str, np.ndarray]:
        num = lambda v: np.array(np.nan if v is None else v, np.float64)
        return {"media": self.media, "componentes": self.componentes, "varianzas": self.varianzas,
                "forma": np.array(self.forma or (), np.int32), "umbral": num(self.umbral),
                "varianza_total": num(self.varianza_total),
                **{f"limite_{k}": num(v) for k, v in sorted(self.limites.items())}}

    @staticmethod
    def _huella(arrays: dict[str, np.ndarray]) -> bytes:
        """Resumen de todo el contenido (nombres, tipos, formas y datos), para firmarlo."""
        h = hashlib.sha256()
        for k in sorted(arrays):
            a = np.ascontiguousarray(arrays[k])
            h.update(f"{k}|{a.dtype.str}|{a.shape}|".encode() + a.tobytes())
        return h.digest()

    def huella(self) -> str:
        """SHA-256 del contenido (no del archivo): para fijar en el código el modelo esperado."""
        return self._huella(self._arrays()).hex()

    def guardar(self, ruta: Path, clave: bytes | None = None) -> None:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        arrays = self._arrays()
        if clave is not None:
            arrays["firma"] = np.array(hmac.new(clave, self._huella(arrays), hashlib.sha256).hexdigest())
        np.savez(ruta, **arrays)

    @classmethod
    def cargar(cls, ruta: Path, clave: bytes | None = None) -> "ModeloPCA":
        """clave: si se da, el modelo tiene que estar firmado con ella (si no, Manipulado)."""
        ruta = Path(ruta)
        if not ruta.exists():
            raise ModeloNoEntrenado(f"No existe {ruta}; ejecuta scripts/montar.py")
        with np.load(ruta, allow_pickle=False) as f:
            d = {k: f[k] for k in f.files}
        if clave is not None:
            firma = str(d.pop("firma", ""))
            esperada = hmac.new(clave, cls._huella(d), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(firma, esperada):
                raise Manipulado(f"{ruta.name}: la firma no coincide (modelo o umbral modificados)")
        num = lambda k: float(d[k]) if k in d and np.isfinite(d[k]) else None
        forma = tuple(int(x) for x in d["forma"]) if "forma" in d and d["forma"].size else None
        limites = {k[7:]: num(k) for k in d if k.startswith("limite_") and num(k) is not None}
        return cls(d["media"], d["componentes"], d.get("varianzas"), forma, num("umbral"),
                   num("varianza_total"), limites)

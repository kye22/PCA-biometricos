"""Entrena el extractor PCA con una base GENÉRICA y diversa (no con las personas inscritas).

    python scripts/entrenar_pca.py [--por-grupo 900] [--componentes 50]

El extractor se entrena una vez con miles de caras de gente que no tiene por qué estar en el
sistema; la BD (bd.csv) solo guarda los templates de quien tiene acceso. Así:
- inscribir a alguien no obliga a reentrenar ni invalida los templates de los demás,
- las eigenfaces describen caras en general, no "mezclas de los 50 inscritos",
- con una base equilibrada, ningún grupo queda comprimido en pocas direcciones (si casi todas las
  caras de entrenamiento fueran de un grupo, las personas de los demás grupos quedarían todas
  cerca entre sí y el sistema aceptaría a cualquiera de ellas como a cualquier otra).

Base: FairFace (Kärkkäinen y Joo, 2021), split de validación, margen 0.25: 10.954 caras de 7
grupos étnicos con etiquetas, licencia CC BY 4.0. Archivo (63 MB, no va en git):
  https://huggingface.co/datasets/HuggingFaceM4/FairFace/resolve/main/0.25/validation-00000-of-00001-951dbd63c8724ee1.parquet
  -> datos/base_generica/fairface_val_025.parquet      (leerlo necesita: pip install pyarrow)

Se descartan menores de 10 años, se reservan RESERVA_POR_GRUPO caras por grupo para medir el
sesgo (nunca se entrena con ellas) y se toman hasta --por-grupo caras por grupo para entrenar.
Todas pasan por la misma cadena que las fotos del sistema (YuNet, alineado, normalización).

Con las caras reservadas se miden también los límites de "cara normal" que usa api.py para
rechazar entradas fabricadas: norma del template (entre 0,9 x percentil 0,1 y 1,25 x percentil
99,9) y error de reconstrucción (hasta 1,15 x percentil 99,9).
Resultado: modelos/pca_base.npz, que sí va en git (montar.py lo usa y ya no entrena).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # usar sin instalar

import argparse

import numpy as np

from sistema import config, detector, imagen, preprocesado
from sistema.excepciones import CaraNoEncontrada
from sistema.pca import ModeloPCA

RUTA_FAIRFACE = config.RAIZ / "datos" / "base_generica" / "fairface_val_025.parquet"
RUTA_CARAS = config.RAIZ / "datos" / "base_generica" / "caras_alineadas.npz"   # caché
GRUPOS = ["East Asian", "Indian", "Black", "White", "Middle Eastern", "Latino_Hispanic", "Southeast Asian"]
EDAD_MIN = 2            # etiqueta de edad de FairFace: 0 = 0-2 años, 1 = 3-9, 2 = 10-19...
RESERVA_POR_GRUPO = 150
SEMILLA = 0


def caras_fairface() -> tuple[np.ndarray, np.ndarray]:
    """-> (caras alineadas uint8 (N, alto, ancho), grupo (N,)). Se cachea en RUTA_CARAS."""
    if RUTA_CARAS.exists():
        d = np.load(RUTA_CARAS)
        return d["caras"], d["grupo"]
    import pyarrow.parquet as pq

    if not RUTA_FAIRFACE.exists():
        sys.exit(f"Falta {RUTA_FAIRFACE}. Descárgalo (ver la ayuda de este script).")
    tabla = pq.read_table(RUTA_FAIRFACE, columns=["image", "age", "race"]).to_pandas()
    tabla = tabla[tabla["age"] >= EDAD_MIN]
    caras, grupo, fallos = [], [], 0
    for fila in tabla.itertuples():
        try:
            caras.append(detector.localizar(imagen.leer(fila.image["bytes"])).cara)
            grupo.append(fila.race)
        except (CaraNoEncontrada, ValueError):
            fallos += 1
    print(f"FairFace: {len(caras)} caras alineadas ({fallos} sin cara detectada)")
    caras, grupo = np.stack(caras), np.array(grupo)
    np.savez_compressed(RUTA_CARAS, caras=caras, grupo=grupo)
    return caras, grupo


def separar(grupo: np.ndarray, por_grupo: int):
    """-> (índices de entrenamiento, índices reservados), equilibrados por grupo y reproducibles."""
    rng = np.random.default_rng(SEMILLA)
    entreno, reserva = [], []
    for g in range(len(GRUPOS)):
        idx = rng.permutation(np.flatnonzero(grupo == g))
        reserva.extend(idx[:RESERVA_POR_GRUPO])
        entreno.extend(idx[RESERVA_POR_GRUPO:RESERVA_POR_GRUPO + por_grupo])
    return np.array(entreno), np.array(reserva)


def entrenar(caras: np.ndarray, componentes: int) -> ModeloPCA:
    """caras alineadas (uint8) -> PCA de la cara completa + PCA del interior (template doble)."""
    normalizadas = np.stack([preprocesado.normalizar(c) for c in caras])
    modelo = entrenar_normalizadas(normalizadas, componentes)
    modelo.interior = entrenar_normalizadas(np.stack([preprocesado.interior(c) for c in normalizadas]), componentes)
    return modelo


def entrenar_normalizadas(normalizadas: np.ndarray, componentes: int) -> ModeloPCA:
    """PCA por SVD aleatorizado (Halko, Martinsson y Tropp, 2011): mismo resultado que el SVD
    completo para las K primeras componentes, sin calcular las ~10.000 que no se usan."""
    forma = normalizadas.shape[1:]
    X = normalizadas.reshape(len(normalizadas), -1).astype(np.float32)
    media = X.mean(axis=0)
    X -= media
    rng = np.random.default_rng(SEMILLA)
    Q = X.T @ rng.standard_normal((X.shape[0], componentes + 20), dtype=np.float32)   # (D, k+20)
    for _ in range(3):                                   # iteraciones de potencia: más precisión
        Q, _ = np.linalg.qr(Q)
        Q = X.T @ (X @ Q)
    Q, _ = np.linalg.qr(Q)
    _, s, vt = np.linalg.svd(X @ Q, full_matrices=False)  # (N, k+20): pequeño
    comp = (vt @ Q.T)[:componentes]                       # direcciones en el espacio de píxeles
    n = len(X) - 1
    return ModeloPCA(media, comp.astype(np.float32), (s[:componentes] ** 2 / n).astype(np.float32),
                     tuple(forma), varianza_total=float((X ** 2).sum() / n))


def limites(modelo: ModeloPCA, caras: np.ndarray) -> dict:
    """Rango de la norma del template y del error de reconstrucción en caras reales no vistas."""
    normalizadas = [preprocesado.normalizar(c) for c in caras]
    normas = np.array([np.linalg.norm(modelo.extraer(c)) for c in normalizadas])
    residuos = np.array([modelo.residuo(c) for c in normalizadas])
    return {"norma_min": 0.9 * float(np.quantile(normas, 0.001)),
            "norma_max": 1.25 * float(np.quantile(normas, 0.999)),
            "residuo_max": 1.15 * float(np.quantile(residuos, 0.999))}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--por-grupo", type=int, default=900)
    p.add_argument("--componentes", type=int, default=config.N_COMPONENTES)
    args = p.parse_args()

    caras, grupo = caras_fairface()
    entreno, reserva = separar(grupo, args.por_grupo)
    cuenta = {GRUPOS[g]: int((grupo[entreno] == g).sum()) for g in range(len(GRUPOS))}
    modelo = entrenar(caras[entreno], args.componentes)
    modelo.limites = limites(modelo, caras[reserva])
    modelo.guardar(config.RUTA_MODELO_BASE)
    print(f"Entrenado con {len(entreno)} caras: {cuenta}")
    print(f"K={modelo.k} eigenfaces de la cara completa ({modelo.varianza_explicada():.0%} de la varianza) "
          f"+ {modelo.interior.k} del interior -> template de {modelo.dim} -> {config.RUTA_MODELO_BASE}")
    print("Límites de cara normal: " + ", ".join(f"{k} {v:.3f}" for k, v in modelo.limites.items()))
    print(f"Huella (copiar en config.HUELLA_MODELO_BASE): {modelo.huella()}")


if __name__ == "__main__":
    main()

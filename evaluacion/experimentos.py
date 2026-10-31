"""Compara variantes de preprocesado / PCA / distancia sobre el anexo de pruebas.

    python evaluacion/experimentos.py

Detecta y alinea todas las caras UNA vez (inscripción + anexo) y, para cada variante, entrena
PCA con las caras inscritas (+ espejos), calcula templates y mide:
- rank-1: % de fotos genuinas cuyo más cercano es la persona correcta
- EER y FRR con un umbral que acepta al 2% de los impostores (como montar.py)
- desconocidos (gemelos...) aceptados con ese umbral

Ojo: el umbral se elige y se mide sobre el mismo anexo -> cifras algo optimistas.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # usar sin instalar

import cv2
import numpy as np

from metricas import eer
from sistema import config, dataset, detector, imagen, preprocesado
from sistema.excepciones import CaraNoEncontrada


# --- preprocesados ----------------------------------------------------------------------

def tan_triggs(cara: np.ndarray, gamma=0.2, s0=1.0, s1=2.0, alfa=0.1, tau=10.0) -> np.ndarray:
    """Normalización de iluminación de Tan & Triggs (2010): gamma + diferencia de gaussianas +
    ecualización de contraste en dos pasos. Quita sombras suaves y deja la estructura."""
    x = cv2.resize(cara, config.TAM_CARA, interpolation=cv2.INTER_AREA).astype(np.float32)
    x = np.power(x + 1.0, gamma)
    x = cv2.GaussianBlur(x, (0, 0), s0) - cv2.GaussianBlur(x, (0, 0), s1)
    x = x / (np.mean(np.abs(x) ** alfa) ** (1 / alfa) + 1e-6)
    x = x / (np.mean(np.minimum(tau, np.abs(x)) ** alfa) ** (1 / alfa) + 1e-6)
    x = tau * np.tanh(x / tau)
    m = preprocesado.MASCARA
    out = np.zeros_like(x)
    out[m] = (x[m] - x[m].mean()) / (x[m].std() + 1e-6)
    return out


def clahe(cara: np.ndarray) -> np.ndarray:
    x = cv2.resize(cara, config.TAM_CARA, interpolation=cv2.INTER_AREA)
    x = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4)).apply(x).astype(np.float32)
    m = preprocesado.MASCARA
    out = np.zeros_like(x)
    out[m] = (x[m] - x[m].mean()) / (x[m].std() + 1e-6)
    return out


PREPROCESADOS = {"actual (hist+máscara)": preprocesado.normalizar, "clahe": clahe, "tan-triggs": tan_triggs}


# --- PCA y distancias -------------------------------------------------------------------

def pca(X: np.ndarray, k: int):
    media = X.mean(0)
    _, s, vt = np.linalg.svd(X - media, full_matrices=False)
    k = min(k, len(X) - 1)
    return media, vt[:k], (s[:k] ** 2) / (len(X) - 1)


def distancias(Tq: np.ndarray, Tg: np.ndarray, tipo: str) -> np.ndarray:
    """Matriz (consultas x galería)."""
    if tipo == "coseno":
        a = Tq / np.linalg.norm(Tq, axis=1, keepdims=True)
        b = Tg / np.linalg.norm(Tg, axis=1, keepdims=True)
        return 1 - a @ b.T
    return np.linalg.norm(Tq[:, None, :] - Tg[None, :, :], axis=2)


def evaluar(gal_ids, gal_caras, q_ids, q_caras, prep, k, saltar, blanquear, tipo, inscritos):
    G = np.stack([prep(c) for c in gal_caras]).reshape(len(gal_caras), -1)
    Q = np.stack([prep(c) for c in q_caras]).reshape(len(q_caras), -1)
    entreno = np.vstack([G, np.stack([prep(c[:, ::-1]) for c in gal_caras]).reshape(len(gal_caras), -1)])
    media, comp, var = pca(entreno, k + saltar)
    comp, var = comp[saltar:], var[saltar:]
    proy = lambda X: (X - media) @ comp.T / (np.sqrt(var) if blanquear else 1)
    D = distancias(proy(Q), proy(G), tipo)

    gal_ids = np.array(gal_ids)
    genu, impo, aciertos, desconocidos = [], [], [], []
    for i, qid in enumerate(q_ids):
        if qid in inscritos:
            j = np.where(gal_ids == qid)[0][0]
            genu.append(D[i, j])
            impo.extend(np.delete(D[i], j))
            aciertos.append(gal_ids[np.argmin(D[i])] == qid)
        else:
            desconocidos.append(D[i].min())
            impo.extend(D[i])
    genu, impo = np.array(genu), np.array(impo)
    umbral = np.quantile(impo, 0.02)
    valor_eer, _ = eer(genu, impo)
    return {"rank1": np.mean(aciertos), "eer": valor_eer, "frr": np.mean(genu > umbral),
            "desc": np.mean(np.array(desconocidos) <= umbral) if desconocidos else float("nan")}


def caras_alineadas(pares):
    ids, caras = [], []
    for id_, f in pares:
        try:
            caras.append(detector.localizar(imagen.leer(f)).cara)
            ids.append(id_)
        except (CaraNoEncontrada, ValueError):
            print(f"  sin cara: {f}")
    return ids, caras


def main():
    gal_ids, gal_caras = caras_alineadas(dataset.listar_inscripcion(config.RUTA_FOTOS, config.RUTA_EXTRA))
    pruebas = dataset.listar_pruebas(config.RUTA_PRUEBAS)
    q_ids, q_caras = caras_alineadas([(i, f) for i, fs in pruebas.items() for f in fs])
    inscritos = set(gal_ids)
    print(f"Galería: {len(gal_ids)} personas · pruebas: {sum(i in inscritos for i in q_ids)} genuinas, "
          f"{sum(i not in inscritos for i in q_ids)} de desconocidos\n")

    variantes = [(p, k, s, b, t) for p in PREPROCESADOS for k in (30, 50, 80) for s in (0, 3)
                 for b in (False, True) for t in ("euclídea", "coseno")]
    res = []
    for p, k, s, b, t in variantes:
        r = evaluar(gal_ids, gal_caras, q_ids, q_caras, PREPROCESADOS[p], k, s, b, t, inscritos)
        res.append(((p, k, s, b, t), r))
    res.sort(key=lambda x: (-x[1]["rank1"], x[1]["eer"]))
    print(f"{'preprocesado':22s} {'K':>3s} {'quita':>5s} {'blanq':>5s} {'distancia':9s} | "
          f"{'rank-1':>6s} {'EER':>6s} {'FRR@2%':>7s} {'desc.acept':>10s}")
    for (p, k, s, b, t), r in res:
        print(f"{p:22s} {k:3d} {s:5d} {'sí' if b else 'no':>5s} {t:9s} | {r['rank1']:6.1%} {r['eer']:6.1%} "
              f"{r['frr']:7.1%} {r['desc']:10.1%}")


if __name__ == "__main__":
    main()

"""Genera ROC, DET e histogramas a partir de resultados del evaluador.

    pip install -e ".[eval]"
    python evaluacion/graficas.py --resultados evaluacion/resultados/prueba.json

Solo lee resultados: no vuelve a procesar fotos ni modifica el modelo.
"""
import argparse
import json
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluacion.metricas import curva


def generar(resultados: Path, destino: Path) -> list[Path]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError('Falta matplotlib. Instala con: pip install -e ".[eval]"') from exc
    r = json.loads(resultados.read_text(encoding="utf-8"))
    g = np.array([float("inf") if d is None else d for d in r["genuinas"]])
    i = np.array([float("inf") if d is None else d for d in r["impostoras"]])
    if not len(g) or not len(i):
        raise ValueError("Se requieren muestras genuinas e impostoras")
    destino.mkdir(parents=True, exist_ok=True)
    umbrales, far, frr = curva(g, i)
    generados = []

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(g[np.isfinite(g)], bins=25, density=True, alpha=0.55, label="Genuinas")
    ax.hist(i[np.isfinite(i)], bins=25, density=True, alpha=0.55, label="Impostoras")
    ax.axvline(r["umbral"], color="black", linestyle="--", label="Umbral evaluado")
    ax.set(xlabel="Distancia coseno", ylabel="Densidad", title="Distancias de verificación 1:1")
    ax.legend()
    fig.tight_layout()
    generados.append(destino / "hist_distancias.png")
    fig.savefig(generados[-1], dpi=150)
    plt.close(fig)

    if r.get("cmc"):
        fig, ax = plt.subplots(figsize=(6, 4))
        valores = r["cmc"]
        ax.plot(range(1, len(valores) + 1), valores, linewidth=2)
        ax.set(xlim=(1, len(valores)), ylim=(0, 1), xlabel="Posición k",
               ylabel="Identidad real entre los k primeros", title="CMC (identificación cerrada)")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        generados.append(destino / "cmc.png")
        fig.savefig(generados[-1], dpi=150)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(far, 1 - frr, linewidth=2)
    ax.plot([0, 1], [0, 1], linestyle=":", color="gray")
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="FAR (FMR)", ylabel="TAR (1 − FRR)",
           title="Curva ROC de verificación")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    generados.append(destino / "roc.png")
    fig.savefig(generados[-1], dpi=150)
    plt.close(fig)

    # Transformación de probabilidades a escala normal para representar la curva DET.
    normal = NormalDist()
    zfar = [normal.inv_cdf(float(v)) for v in np.clip(far, 1e-4, 1 - 1e-4)]
    zfrr = [normal.inv_cdf(float(v)) for v in np.clip(frr, 1e-4, 1 - 1e-4)]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(zfar, zfrr, linewidth=2)
    tasas = [.001, .01, .05, .1, .2, .5, .8, .95]
    marcas = [normal.inv_cdf(x) for x in tasas]
    etiquetas = [f"{x:.1%}" for x in tasas]
    ax.set_xticks(marcas, etiquetas, rotation=40)
    ax.set_yticks(marcas, etiquetas)
    ax.set(xlabel="FAR (FMR)", ylabel="FRR (FNMR)", title="Curva DET de verificación")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    generados.append(destino / "det.png")
    fig.savefig(generados[-1], dpi=150)
    plt.close(fig)
    return generados


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--resultados", type=Path, default=Path("evaluacion/resultados/prueba.json"))
    p.add_argument("--destino", type=Path, default=Path("evaluacion/resultados/graficas"))
    args = p.parse_args()
    try:
        salidas = generar(args.resultados, args.destino)
    except (OSError, ValueError, RuntimeError) as exc:
        p.exit(2, f"ERROR: {exc}\n")
    for s in salidas:
        print(s)


if __name__ == "__main__":
    main()

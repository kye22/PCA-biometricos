"""Genera las figuras de docs/REPORTE.md en docs/img/.

    python evaluacion/figuras_reporte.py

Requiere haber ejecutado scripts/montar.py. Solo usa fotos del anexo (Wikimedia Commons, con
licencia libre); las del profe no se publican.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # usar sin instalar

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from sistema import analisis, api, bd, config, dataset, imagen, preprocesado
from sistema.excepciones import CaraNoEncontrada

SALIDA = config.RAIZ / "docs" / "img"
FOTO_DEMO = config.RUTA_PRUEBAS / "keanu_reeves" / "03.jpg"            # CC BY 3.0, Siebbi
GEMELA_A = config.RUTA_PRUEBAS / "ashley_olsen" / "01.jpg"             # CC BY 3.0, David Shankbone
GEMELA_B = config.RUTA_PRUEBAS / "mary-kate_olsen" / "02.jpg"          # CC BY 3.0, David Shankbone

# Paleta validada (dataviz: 2 categóricos, superficie clara)
FONDO, TINTA, TINTA_2, REJILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
AZUL, NARANJA = "#2a78d6", "#eb6834"

plt.rcParams.update({
    "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": TINTA,
    "axes.edgecolor": REJILLA, "axes.labelcolor": TINTA_2, "xtick.color": TINTA_2, "ytick.color": TINTA_2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": REJILLA, "grid.linewidth": 0.6, "axes.titleweight": "bold", "axes.titlesize": 11,
})


def visible(x: np.ndarray) -> np.ndarray:
    return (x - x.min()) / (np.ptp(x) + 1e-6)


def guardar(fig, nombre):
    SALIDA.mkdir(parents=True, exist_ok=True)
    fig.savefig(SALIDA / nombre, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  ", nombre)


def sin_ejes(ax):
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


def fig_pipeline():
    img = imagen.leer(FOTO_DEMO)
    a = analisis.analizar(FOTO_DEMO)
    d = a.deteccion
    v = img.copy()
    g = max(2, max(v.shape[:2]) // 250)
    x, y, w, h = d.caja
    cv2.rectangle(v, (x, y), (x + w, y + h), (80, 200, 80), g)
    for ox, oy in d.ojos:
        cv2.circle(v, (int(ox), int(oy)), g * 3, (0, 220, 255), -1)
    m = 0.35
    x0, y0 = max(0, int(x - m * w)), max(0, int(y - m * h))
    v = v[y0:int(y + h + m * h), x0:int(x + w + m * w)]

    fig, ejes = plt.subplots(1, 4, figsize=(11, 3.2), gridspec_kw={"width_ratios": [1.3, 1, 1, 1]})
    paneles = [
        (v[:, :, ::-1], None, "1 · Detección (YuNet)\ncara + ojos"),
        (d.cara, "gray", "2 · Alineada\nojos siempre en el mismo sitio"),
        (visible(a.cara), "gray", "3 · Normalizada\nelipse + luz igualada"),
        (visible(a.reconstruccion), "gray", f"4 · Lo que ve PCA\n{a.template.size} números"),
    ]
    for ax, (im, cmap, titulo) in zip(ejes, paneles):
        ax.imshow(im, cmap=cmap)
        ax.set_title(titulo, fontsize=9.5, color=TINTA)
        sin_ejes(ax)
    fig.tight_layout(w_pad=3)
    fig.canvas.draw()
    for izq, der in zip(ejes[:-1], ejes[1:]):   # flecha en el hueco entre cada par de imágenes
        a, b = izq.get_position(), der.get_position()
        fig.text((a.x1 + b.x0) / 2, (a.y0 + a.y1) / 2, "→", fontsize=20, color=TINTA_2, ha="center", va="center")
    guardar(fig, "01_cadena.png")


def fig_eigenfaces(modelo):
    fig, ejes = plt.subplots(2, 6, figsize=(11, 4.2))
    ejes = ejes.ravel()
    ejes[0].imshow(visible(modelo.media.reshape(modelo.forma)), cmap="gray")
    ejes[0].set_title("Cara media", fontsize=9.5)
    for i in range(11):
        ef = modelo.componentes[i].reshape(modelo.forma)
        lim = np.abs(ef).max()
        ejes[i + 1].imshow(ef, cmap="RdBu_r", vmin=-lim, vmax=lim)
        ejes[i + 1].set_title(f"Eigenface {i + 1}", fontsize=9.5)
    for ax in ejes:
        sin_ejes(ax)
    fig.suptitle("La «base» que aprende PCA: cara media + direcciones de máxima variación",
                 fontsize=11, fontweight="bold", y=1.02)
    fig.text(0.5, -0.02, "Rojo/azul = zonas que se aclaran u oscurecen juntas. Las primeras suelen "
             "recoger luz y forma general; las siguientes, rasgos más finos.", ha="center",
             fontsize=9, color=TINTA_2)
    guardar(fig, "02_eigenfaces.png")


def fig_varianza(modelo):
    acum = np.cumsum(modelo.varianzas) / modelo.varianza_total * 100
    k = np.arange(1, len(acum) + 1)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.plot(k, acum, color=AZUL, linewidth=2)
    ax.scatter([k[-1]], [acum[-1]], s=40, color=AZUL, zorder=3, edgecolor=FONDO, linewidth=2)
    ax.annotate(f"K = {k[-1]}: {acum[-1]:.0f}% de la varianza", (k[-1], acum[-1]),
                xytext=(-10, -28), textcoords="offset points", ha="right", fontsize=9.5)
    for kk in (10, 25):
        ax.annotate(f"K = {kk}: {acum[kk - 1]:.0f}%", (kk, acum[kk - 1]), xytext=(8, -14),
                    textcoords="offset points", fontsize=9, color=TINTA_2)
        ax.scatter([kk], [acum[kk - 1]], s=22, color=AZUL, zorder=3, edgecolor=FONDO, linewidth=1.5)
    ax.set_xlabel("Nº de eigenfaces (K) = longitud del template")
    ax.set_ylabel("% de varianza explicada")
    ax.set_ylim(0, 100)
    ax.set_title("¿Cuánta información conservan K números?", loc="left")
    guardar(fig, "03_varianza.png")


def fig_reconstruccion(modelo):
    cara = preprocesado.normalizar(api.extraer(FOTO_DEMO, True)[1].cara)
    x = cara.reshape(-1) - modelo.media
    fig, ejes = plt.subplots(1, 6, figsize=(11, 2.4))
    ejes[0].imshow(visible(cara), cmap="gray")
    ejes[0].set_title("Original\n(10.000 píxeles)", fontsize=9.5)
    for ax, k in zip(ejes[1:], (2, 5, 10, 25, modelo.dim)):
        c = modelo.componentes[:k]
        rec = modelo.media + (c @ x) @ c
        ax.imshow(visible(rec.reshape(modelo.forma)), cmap="gray")
        ax.set_title(f"K = {k}", fontsize=9.5)
    for ax in ejes:
        sin_ejes(ax)
    fig.suptitle("Reconstruir una cara a partir de su template: con más eigenfaces, más detalle",
                 fontsize=11, fontweight="bold", y=1.08)
    guardar(fig, "04_reconstruccion.png")


def distancias_anexo():
    inscritos = set(bd.cargar())
    gen, imp = [], []
    for id_, fotos in dataset.listar_pruebas(config.RUTA_PRUEBAS).items():
        for f in fotos:
            try:
                a = analisis.analizar(f)
            except CaraNoEncontrada:
                continue
            for c in a.ranking:
                (gen if c.id == id_ and id_ in inscritos else imp).append(c.distancia)
    return np.array(gen), np.array(imp), api.umbral()


def fig_distancias(gen, imp, umbral):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    bins = np.linspace(min(gen.min(), imp.min()), max(gen.max(), imp.max()), 28)
    ax.hist(imp, bins=bins, density=True, histtype="stepfilled", color=NARANJA, alpha=0.35,
            edgecolor=NARANJA, linewidth=1.5, label=f"Impostor: persona distinta (n={len(imp)})")
    ax.hist(gen, bins=bins, density=True, histtype="step", color=AZUL, linewidth=2.2,
            label=f"Genuina: misma persona, otra foto (n={len(gen)})")
    ax.axvline(umbral, color=TINTA, linewidth=1.3, linestyle="--")
    tope = ax.get_ylim()[1]
    ax.text(umbral - 1.5, tope * 0.96, f"se acepta ←\numbral {umbral:.0f}", fontsize=9, va="top", ha="right")
    acept = np.mean(gen <= umbral) * 100
    ax.text(umbral + 1.5, tope * 0.96, f"solo el {acept:.0f}% de las genuinas\nqueda a la izquierda",
            fontsize=9, va="top", ha="left", color=TINTA_2)
    ax.set_xlabel("Distancia entre templates (menor = más parecido)")
    ax.set_ylabel("Densidad")
    ax.set_yticks([])
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2)
    ax.set_title("El problema de fondo: genuinas e impostoras casi se solapan", loc="left")
    guardar(fig, "05_distancias.png")


def fig_gemelos():
    _, da, _ = api.extraer(GEMELA_A, True)
    _, db, _ = api.extraer(GEMELA_B, True)
    a = analisis.analizar(GEMELA_A)
    d_mk = next(c.distancia for c in a.ranking if c.id == "mary-kate_olsen")
    mediana = np.median([c.distancia for c in a.ranking])
    fig, ejes = plt.subplots(1, 2, figsize=(5.6, 3.4))
    fig.subplots_adjust(bottom=0.14)
    for ax, det, t in zip(ejes, (da, db), ("Ashley Olsen\n(NO inscrita)", "Mary-Kate Olsen\n(inscrita)")):
        ax.imshow(det.cara, cmap="gray")
        ax.set_title(t, fontsize=9.5)
        sin_ejes(ax)
    fig.suptitle(f"Ataque del gemelo: distancia {d_mk:.0f} < umbral {api.umbral():.0f} → ACEPTADA",
                 fontsize=11, fontweight="bold", color=TINTA, y=1.04)
    fig.text(0.5, 0.06, f"(la distancia típica a cualquier otro inscrito es ~{mediana:.0f})",
             ha="center", fontsize=9, color=TINTA_2)
    guardar(fig, "06_gemelos.png")


def fig_mejoras():
    # Medido el 31-10-2026 con evaluacion/evaluar.py y evaluacion/experimentos.py (ver decisiones.md)
    filas = [("Al azar (1 de 50)", 2.0), ("Sistema actual\n(1 foto inscrita)", 11.4),
             ("Mejor variante de preprocesado\n(CLAHE / coseno…)", 14.4),
             ("Varias fotos inscritas\npor persona", 38.5)]
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    y = np.arange(len(filas))[::-1]
    vals = [v for _, v in filas]
    colores = [REJILLA, AZUL, AZUL, AZUL]
    ax.barh(y, vals, height=0.55, color=colores, edgecolor=FONDO, linewidth=2)
    for yy, v in zip(y, vals):
        ax.text(v + 0.8, yy, f"{v:.1f}%", va="center", fontsize=10, color=TINTA)
    ax.set_yticks(y, [n for n, _ in filas], fontsize=9.5)
    ax.set_xlabel("Rank-1: % de fotos nuevas cuyo más parecido es la persona correcta")
    ax.set_xlim(0, 45)
    ax.grid(axis="y", visible=False)
    ax.set_axisbelow(True)
    ax.set_title("Qué mueve de verdad la aguja", loc="left")
    guardar(fig, "07_mejoras.png")


def main():
    modelo = api._modelo()
    print("Figuras ->", SALIDA)
    fig_pipeline()
    fig_eigenfaces(modelo)
    fig_varianza(modelo)
    fig_reconstruccion(modelo)
    fig_distancias(*distancias_anexo())
    fig_gemelos()
    fig_mejoras()


if __name__ == "__main__":
    main()

"""Convierte docs/REPORTE.md en docs/REPORTE.pdf (A4, con las figuras de docs/img).

    python evaluacion/reporte_pdf.py

Markdown -> HTML con estilos de impresión -> PDF con Edge o Chrome en modo headless
(vienen instalados en Windows). Si cambian las figuras: python evaluacion/figuras_reporte.py
"""
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import markdown

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "docs" / "REPORTE.md"
SALIDA = RAIZ / "docs" / "REPORTE.pdf"
NAVEGADORES = [   # Chrome primero: Edge termina antes de acabar de escribir el PDF
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google-chrome", "chromium", "chromium-browser",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", "msedge",
]

CSS = """
@page { size: A4; margin: 13mm 14mm 13mm 14mm; }
:root { --tinta:#0b0b0b; --tinta2:#52514e; --azul:#2a78d6; --borde:#e4e3df; --fondo2:#f4f3f0; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", system-ui, sans-serif; color: var(--tinta); font-size: 9.8pt;
       line-height: 1.45; margin: 0; }
h1 { font-size: 24pt; margin: 0 0 4px; letter-spacing: -0.5px; }
h1 + blockquote { margin-top: 0; }
h2 { font-size: 15pt; color: var(--azul); border-bottom: 2px solid var(--azul); padding-bottom: 3px;
     margin: 26px 0 10px; page-break-after: avoid; }
h3 { font-size: 12pt; margin: 18px 0 6px; page-break-after: avoid; }
p, li { orphans: 3; widows: 3; }
p:has(> strong:only-child), h2 + p, h3 + p { page-break-after: avoid; }   /* subtítulos en negrita */
blockquote { margin: 8px 0 14px; padding: 6px 12px; border-left: 3px solid var(--borde);
             color: var(--tinta2); font-size: 9pt; }
blockquote p { margin: 2px 0; }
code { font-family: Consolas, monospace; font-size: 9pt; background: var(--fondo2);
       padding: 1px 4px; border-radius: 3px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 14px; font-size: 9pt;
        page-break-inside: avoid; }
th { text-align: left; background: var(--fondo2); font-weight: 600; }
th, td { padding: 5px 8px; border-bottom: 1px solid var(--borde); vertical-align: top; }
tr:nth-child(even) td { background: #fafaf8; }
img { max-width: 100%; display: block; margin: 8px auto 4px; }
p:has(> img) { page-break-inside: avoid; margin: 10px 0 14px; }
hr { border: 0; border-top: 1px solid var(--borde); margin: 22px 0; }
a { color: var(--azul); text-decoration: none; }
sub { font-size: 7.5pt; color: var(--tinta2); line-height: 1.4; display: block; }
/* resumen inicial: tabla de cifras clave */
.resumen td:last-child { font-weight: 600; white-space: nowrap; }
/* figuras pequeñas: que no ocupen media página */
img[src$="03_varianza.png"] { width: 72%; }
img[src$="05_distancias.png"] { width: 86%; }
img[src$="06_gemelos.png"] { width: 46%; }
img[src$="07_mejoras.png"] { width: 78%; }
.portada-sub { color: var(--tinta2); font-size: 10pt; margin-bottom: 14px; }
"""


def navegador() -> str:
    for n in NAVEGADORES:
        ruta = shutil.which(n) or (n if Path(n).exists() else None)
        if ruta:
            return ruta
    sys.exit("No encuentro Edge ni Chrome para imprimir el PDF")


def main():
    md = ENTRADA.read_text(encoding="utf-8")
    html = markdown.markdown(md, extensions=["tables", "sane_lists"])
    html = html.replace('src="img/', f'src="{(RAIZ / "docs" / "img").as_uri()}/')
    html = html.replace('href="../', f'href="https://github.com/kye22/PCA-biometricos/blob/main/')
    html = re.sub(r"<table>", '<table class="resumen">', html, count=1)   # la primera: cifras clave
    doc = (f'<!doctype html><html lang="es"><head><meta charset="utf-8">'
           f"<title>Reporte PCA</title><style>{CSS}</style></head><body>{html}</body></html>")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        pagina = Path(tmp) / "reporte.html"
        pagina.write_text(doc, encoding="utf-8")
        pdf = Path(tmp) / "reporte.pdf"   # ruta sin tildes; luego se mueve a docs/
        # perfil propio: si no, un Edge ya abierto se queda la orden y no imprime nada
        subprocess.run([navegador(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={Path(tmp) / 'perfil'}", "--allow-file-access-from-files",
                        f"--print-to-pdf={pdf}", pagina.as_uri()],
                       check=True, capture_output=True, timeout=120)
        for _ in range(60):   # Edge sigue escribiendo tras devolver el control
            if pdf.exists() and pdf.stat().st_size > 0:
                break
            time.sleep(0.5)
        else:
            sys.exit("El navegador no generó el PDF")
        time.sleep(1)
        shutil.copyfile(pdf, SALIDA)
    print(f"PDF -> {SALIDA} ({SALIDA.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

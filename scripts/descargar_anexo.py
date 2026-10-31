"""Descarga el anexo de fotos de prueba desde Wikimedia Commons (fotos con licencia libre).

    python scripts/descargar_anexo.py [--por-persona 3] [--solo adele,tini]

- Para cada id busca en la categoría de Commons de esa persona (y sus subcategorías directas),
  NO en búsqueda libre (traería a otras personas).
- Se queda con fotos cuyo título contiene el nombre, con UNA sola cara clara (YuNet) y que no
  sean la propia foto inscrita (distancia PCA casi 0).
- Guarda en datos/pruebas/<id>/ y anota autor y licencia en datos/pruebas/fuentes.csv.
- Además de los inscritos, descarga DESCONOCIDOS (gemelos, etc.) para probar impostores.

Los filtros no garantizan que sea la persona correcta: hay que revisar el resultado a ojo
(scripts/hoja_anexo.py) antes de evaluar. En la primera revisión se quitaron a mano dibujos,
carteles, un imitador, otra persona en primer plano y duplicados recortados.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # usar sin instalar

import argparse
import csv
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request

import cv2
import numpy as np

from sistema import api, bd, comparador, config, detector, imagen
from sistema.excepciones import CaraNoEncontrada

API = "https://commons.wikimedia.org/w/api.php"
AGENTE = "PCA-biometricos-practica/0.1 (proyecto universitario; https://github.com/kye22/PCA-biometricos)"

# id (tal cual, con erratas) -> categoría de Commons
INSCRITOS = {
    "adam_pearson": "Adam Pearson (actor)", "adele": "Adele", "aitana_etxebarria_(twin_melody)": "Twin Melody",
    "anya_taylor_joy": "Anya Taylor-Joy", "arianna_grande": "Ariana Grande", "brays_efe": "Brays Efe",
    "christian_bale": "Christian Bale", "cynthia_erivo": "Cynthia Erivo", "elisabeth_ii": "Elizabeth II",
    "ellen_page": "Elliot Page", "etsy_quesada": "Esty Quesada", "eva_hache": "Eva Hache", "falete": "Falete",
    "forest_whitaker": "Forest Whitaker", "hasbulla_magomedov": "Hasbulla Magomedov",
    "hunter_schufer": "Hunter Schafer", "hwang_min-hyun": "Hwang Min-hyun", "idris_elba": "Idris Elba",
    "jackie_chan": "Jackie Chan", "james_phelps_(gemelo_weasley)": "James Phelps",
    "joe_batalan": "Joe Batalan", "jordi_hurtado": "Jordi Hurtado i Torres", "jorge_javier_vazquez": "Jorge Javier Vázquez",
    "josie_totah": "Josie Totah", "julie_walters": "Julie Walters", "keanu_reeves": "Keanu Reeves",
    "kim_jisoo": "Jisoo", "lady_gaga": "Lady Gaga", "lara_raj": "Lara Raj", "leticia_sabater": "Leticia Sabater",
    "mary-kate_olsen": "Mary-Kate Olsen", "metrika": "Metrika", "michael_jackson": "Michael Jackson",
    "mindy_kaling": "Mindy Kaling", "nicolas_maduro": "Nicolás Maduro", "rossy_de_palma": "Rossy de Palma",
    "salma_hayek": "Salma Hayek", "samuel_l_jackson": "Samuel L. Jackson", "santiago_segura": "Santiago Segura",
    "serenna_williams": "Serena Williams", "stevie_wonder": "Stevie Wonder", "taylor_swift": "Taylor Swift",
    "temuera_morrison": "Temuera Morrison", "tilda_swinton": "Tilda Swinton", "tini": "Tini Stoessel",
    "wiliem_dafoe": "Willem Dafoe", "winnie_harlow": "Winnie Harlow", "zack_efron": "Zac Efron",
    "zoe_saldana": "Zoe Saldaña", "alvaro_arbeloa_coca": "Álvaro Arbeloa",
}
# No inscritos: deberían salir DESCONOCIDO. Gemelos y parecidos de los inscritos.
DESCONOCIDOS = {
    "oliver_phelps_(gemelo_weasley)": "Oliver Phelps",
    "ashley_olsen": "Ashley Olsen",
}
# Palabras del título que delatan que no es una foto de la persona
EXCLUIR = re.compile(r"wax|tussaud|statue|estatua|mural|graffiti|poster|cartel|signature|firma|logo|"
                     r"stamp|sello|coin|moneda|painting|portrait of|cosplay|impersonat|tribute|doll|figure",
                     re.I)


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def pedir(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({"format": "json", **params})
    for intento in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENTE}), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(5 * (intento + 1))
    raise RuntimeError("Commons sigue respondiendo 429")


def resolver(categoria: str) -> str:
    """Sigue las 'redirecciones blandas' de Commons ({{Category redirect|...}})."""
    d = pedir({"action": "query", "titles": f"Category:{categoria}", "prop": "revisions",
               "rvprop": "content", "rvslots": "main"})
    pagina = next(iter(d["query"]["pages"].values()))
    texto = pagina.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("*", "")
    m = re.search(r"\{\{\s*Category redirect\s*\|\s*(?:Category:)?([^}|]+)", texto, re.I)
    return m.group(1).strip() if m else categoria


def archivos_de(categoria: str, profundidad: int = 2, max_categorias: int = 25) -> dict[str, dict]:
    """título -> imageinfo de los archivos de la categoría y sus subcategorías (hasta
    `profundidad` niveles: las fotos suelen estar en "<Nombre> in 2019", dentro de "by year")."""
    res, pendientes = {}, [(f"Category:{resolver(categoria)}", 0)]
    vistas = set()
    while pendientes and len(vistas) < max_categorias:
        cat, nivel = pendientes.pop(0)
        if cat in vistas:
            continue
        vistas.add(cat)
        cont = {}
        while True:
            d = pedir({"action": "query", "generator": "categorymembers", "gcmtitle": cat,
                       "gcmtype": "file|subcat", "gcmlimit": 200, "prop": "imageinfo",
                       "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 800,
                       "iiextmetadatafilter": "Artist|LicenseShortName", **cont})
            for p in d.get("query", {}).get("pages", {}).values():
                if p["ns"] == 14 and nivel < profundidad:
                    pendientes.append((p["title"], nivel + 1))
                elif p["ns"] == 6 and "imageinfo" in p:
                    res[p["title"]] = p["imageinfo"][0]
            if "continue" not in d or len(res) > 400:
                break
            cont = d["continue"]
            time.sleep(0.5)
        time.sleep(0.5)
    return res


def candidatos(nombre: str, info: dict[str, dict]) -> list[tuple[str, dict]]:
    """Fotos jpg/png grandes cuyo título contiene alguna palabra del nombre (la categoría ya
    restringe a la persona; esto quita logos, carteles, edificios con su nombre...)."""
    nombre = re.sub(r"\(.*?\)", "", nombre)
    claves = [_sin_tildes(p) for p in re.split(r"[\s\-.]+", nombre) if len(p) > 3] or [_sin_tildes(nombre)]
    out = []
    for titulo, ii in sorted(info.items()):
        t = _sin_tildes(titulo)
        if ii.get("mime") not in ("image/jpeg", "image/png") or ii.get("width", 0) < 500:
            continue
        if not any(c in t for c in claves) or EXCLUIR.search(titulo):
            continue
        out.append((titulo, ii))
    return out


def una_cara_clara(img: np.ndarray) -> bool:
    det = detector._yunet()
    f = min(1.0, detector.LADO_MAX / max(img.shape[:2]))
    peq = cv2.resize(img, None, fx=f, fy=f) if f < 1 else img
    det.setInputSize((peq.shape[1], peq.shape[0]))
    _, caras = det.detect(peq)
    if caras is None:
        return False
    buenas = [c for c in caras if c[14] >= 0.85]
    grandes = [c for c in buenas if c[2] >= 80]
    return len(buenas) == 1 and len(grandes) == 1


def descargar(id_: str, categoria: str, n: int, base: dict, filas: list) -> int:
    destino = config.RUTA_PRUEBAS / id_
    try:
        info = archivos_de(categoria)
    except Exception as e:
        print(f"  {id_}: error consultando Commons ({e})")
        return 0
    cands = candidatos(categoria, info)
    guardadas, plantillas, bases = 0, [], set()
    for titulo, ii in cands:
        if guardadas >= n:
            break
        base_titulo = re.sub(r"\(cropped\)|_?cropped.*|\.\w+$", "", titulo, flags=re.I).strip(" _")
        if base_titulo in bases:   # misma foto recortada / sin recortar
            continue
        try:
            req = urllib.request.Request(ii["thumburl"], headers={"User-Agent": AGENTE})
            datos = urllib.request.urlopen(req, timeout=30).read()
            img = imagen.leer(datos)
        except Exception:
            continue
        time.sleep(0.3)
        if not una_cara_clara(img):
            continue
        try:
            t, _, _ = api.extraer(img, con_detector=True)
        except CaraNoEncontrada:
            continue
        if id_ in base and comparador.distancia_a_id(t, base[id_]) < 15:   # es la foto inscrita
            continue
        if any(comparador.distancia(t, o) < 15 for o in plantillas):         # duplicada
            continue
        destino.mkdir(parents=True, exist_ok=True)
        nombre = f"{guardadas + 1:02d}.jpg"
        cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tofile(str(destino / nombre))
        plantillas.append(t)
        bases.add(base_titulo)
        meta = ii.get("extmetadata", {})
        filas.append({"id": id_, "archivo": f"{id_}/{nombre}", "fuente": ii["descriptionurl"],
                      "autor": re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip(),
                      "licencia": meta.get("LicenseShortName", {}).get("value", "")})
        guardadas += 1
    return guardadas


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--por-persona", type=int, default=3)
    p.add_argument("--solo", help="ids separados por comas")
    args = p.parse_args()

    base = bd.cargar()
    todos = {**INSCRITOS, **DESCONOCIDOS}
    if args.solo:
        todos = {k: v for k, v in todos.items() if k in args.solo.split(",")}

    ruta_fuentes = config.RUTA_PRUEBAS / "fuentes.csv"
    filas = []
    if ruta_fuentes.exists():
        with open(ruta_fuentes, newline="", encoding="utf-8") as f:
            filas = [r for r in csv.DictReader(f) if r["id"] not in todos]

    cobertura = {}
    for id_, categoria in todos.items():
        cobertura[id_] = descargar(id_, categoria, args.por_persona, base, filas)
        print(f"  {id_:38s} {cobertura[id_]} fotos  ({categoria})")

    config.RUTA_PRUEBAS.mkdir(parents=True, exist_ok=True)
    with open(ruta_fuentes, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "archivo", "fuente", "autor", "licencia"])
        w.writeheader()
        w.writerows(sorted(filas, key=lambda r: r["archivo"]))

    sin = [i for i, n in cobertura.items() if n == 0]
    print(f"\nTotal: {sum(cobertura.values())} fotos. Sin fotos ({len(sin)}): {', '.join(sin) or '—'}")
    print("Revisa el resultado a ojo: python scripts/hoja_anexo.py")


if __name__ == "__main__":
    main()

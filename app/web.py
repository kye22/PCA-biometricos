"""Interfaz web para probar el sistema subiendo fotos.

    python app/web.py            -> abrir http://localhost:5000

Muestra la detección dibujada sobre la foto, la cara alineada, lo que "ve" PCA, el veredicto
(con el umbral) y el ranking de los famosos más parecidos con su confianza relativa.
No forma parte de lo que se entrega al rival (eso es la librería); es para nosotros y la exposición.
"""
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # usar sin instalar

import cv2
import numpy as np
from flask import Flask, render_template_string, request

from sistema import analisis, api, bd, comparador, config, imagen
from sistema.excepciones import CaraNoEncontrada, ErrorSistema

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
TOP = 5


# --- utilidades de imagen ------------------------------------------------------------

def a_base64(img: np.ndarray, lado_max: int | None = None) -> str:
    if lado_max and max(img.shape[:2]) > lado_max:
        f = lado_max / max(img.shape[:2])
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    return base64.b64encode(cv2.imencode(".jpg", img)[1]).decode()


def a_gris_visible(x: np.ndarray, escala: int = 2) -> np.ndarray:
    """Array float cualquiera -> uint8 0..255 ampliado (para ver caras normalizadas)."""
    x = (x - x.min()) / (np.ptp(x) + 1e-6) * 255
    return cv2.resize(x.astype(np.uint8), None, fx=escala, fy=escala, interpolation=cv2.INTER_NEAREST)


def dibujar_deteccion(img: np.ndarray, det) -> np.ndarray:
    v = img.copy() if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    grosor = max(2, max(v.shape[:2]) // 300)
    x, y, w, h = det.caja
    cv2.rectangle(v, (x, y), (x + w, y + h), (80, 200, 80), grosor)
    color_ojos = (0, 220, 255) if det.ojos_detectados else (60, 60, 255)
    for ox, oy in det.ojos:
        cv2.circle(v, (int(ox), int(oy)), grosor * 3, color_ojos, -1)
    (x1, y1), (x2, y2) = det.ojos
    cv2.line(v, (int(x1), int(y1)), (int(x2), int(y2)), color_ojos, grosor)
    return v


# --- datos de los inscritos (miniaturas y huellas para detectar "misma foto") ----------

def inscritos() -> dict:
    if not config.RUTA_INSCRITOS.exists():
        return {}
    return json.loads(config.RUTA_INSCRITOS.read_text(encoding="utf-8"))


_miniaturas: dict[str, str] = {}


def miniatura(id_: str) -> str | None:
    if id_ not in _miniaturas:
        fotos = inscritos().get(id_, [])
        if not fotos:
            return None
        ruta = Path(fotos[0]["foto"])
        ruta = ruta if ruta.is_absolute() else config.RAIZ / ruta
        try:
            _miniaturas[id_] = a_base64(imagen.leer(ruta), 160)
        except ValueError:
            return None
    return _miniaturas[id_]


def bonito(id_: str | None) -> str:
    return id_.replace("_", " ").title() if id_ else "—"


# --- rutas -------------------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def inicio():
    ctx = {"ids": sorted(bd.cargar()), "bonito": bonito, "error": None, "r": None,
           "modo": request.form.get("modo", "identificar"), "id_ver": request.form.get("id_ver", ""),
           "sd": bool(request.form.get("sd"))}
    try:
        api._modelo()
    except ErrorSistema as e:
        ctx["error"] = f"{e}"
        return render_template_string(PLANTILLA, **ctx)

    if request.method == "POST" and request.files.get("foto"):
        datos = request.files["foto"].read()
        try:
            ctx["r"] = resultado(datos, ctx)
        except CaraNoEncontrada:
            ctx["error"] = ("No se ha detectado ninguna cara. Prueba con otra foto o marca "
                            "'sin detector' si la foto ya es un recorte de la cara.")
        except (ValueError, ErrorSistema) as e:
            ctx["error"] = str(e)
    return render_template_string(PLANTILLA, **ctx)


def resultado(datos: bytes, ctx: dict) -> dict:
    a = analisis.analizar(datos, con_detector=not ctx["sd"])
    img = imagen.leer(datos)
    huella = hashlib.sha256(datos).hexdigest()
    misma = next((i for i, fs in inscritos().items() if any(f["sha256"] == huella for f in fs)), None)

    r = {
        "a": a,
        "foto": a_base64(dibujar_deteccion(img, a.deteccion) if a.deteccion else img, 640),
        "alineada": a_base64(cv2.resize(a.deteccion.cara if a.deteccion else a_gris_visible(a.cara, 1),
                                        None, fx=2, fy=2)),
        "normalizada": a_base64(a_gris_visible(a.cara)),
        "reconstruida": a_base64(a_gris_visible(a.reconstruccion)),
        "misma": misma,
        "top": [(c, miniatura(c.id)) for c in a.ranking[:TOP]],
        "dmax": max([c.distancia for c in a.ranking[:TOP]] + [a.umbral * 1.3]),
    }
    if ctx["modo"] == "verificar" and ctx["id_ver"] in bd.cargar():
        d = comparador.distancia_a_id(a.template, bd.cargar()[ctx["id_ver"]])
        posicion = next(n for n, c in enumerate(a.ranking, 1) if c.id == ctx["id_ver"])
        r["verif"] = {"id": ctx["id_ver"], "d": d, "ok": comparador.acepta(d, a.umbral),
                      "posicion": posicion, "mini": miniatura(ctx["id_ver"])}
    return r


PLANTILLA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reconocimiento facial PCA</title>
<style>
 :root{--bg:#f6f7f9;--card:#fff;--txt:#1d2330;--sub:#5d6678;--borde:#dfe3ea;--ok:#1f8a4c;--no:#c0392b;--acento:#2f5bd3}
 @media (prefers-color-scheme: dark){:root{--bg:#14171d;--card:#1d222b;--txt:#e7eaf0;--sub:#9aa3b5;--borde:#2c3340}}
 body{font-family:system-ui,Segoe UI,sans-serif;background:var(--bg);color:var(--txt);margin:0;padding:24px}
 main{max-width:1100px;margin:auto} h1{font-size:1.4rem;margin:0 0 4px} .sub{color:var(--sub);font-size:.9rem}
 .card{background:var(--card);border:1px solid var(--borde);border-radius:10px;padding:16px;margin:16px 0}
 form{display:flex;flex-wrap:wrap;gap:12px;align-items:center}
 button{background:var(--acento);color:#fff;border:0;border-radius:6px;padding:8px 18px;font-size:1rem;cursor:pointer}
 .fila{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start} .fila figure{margin:0;text-align:center}
 figcaption{font-size:.8rem;color:var(--sub);margin-top:4px;max-width:220px}
 img{border-radius:6px;max-width:100%} .veredicto{font-size:1.5rem;font-weight:700}
 .ok{color:var(--ok)} .no{color:var(--no)} .aviso{background:#fff3cd;color:#664d03;padding:8px 12px;border-radius:6px}
 .error{background:#f8d7da;color:#842029;padding:8px 12px;border-radius:6px}
 table{border-collapse:collapse;width:100%} td,th{padding:6px 8px;border-bottom:1px solid var(--borde);text-align:left;font-size:.92rem}
 .barra{position:relative;height:14px;background:var(--bg);border-radius:7px;min-width:160px}
 .barra span{position:absolute;left:0;top:0;bottom:0;border-radius:7px}
 .barra i{position:absolute;top:-4px;bottom:-4px;width:2px;background:var(--txt)}
 .mini{width:56px;height:56px;object-fit:cover;border-radius:6px}
</style></head><body><main>
<h1>Reconocimiento facial con PCA</h1>
<div class="sub">Sistemas Biométricos · {{ ids|length }} personas inscritas</div>

<div class="card"><form method="post" enctype="multipart/form-data">
 <input type="file" name="foto" accept="image/*" required>
 <label><input type="radio" name="modo" value="identificar" {{ 'checked' if modo=='identificar' }}> Identificar (¿quién es?)</label>
 <label><input type="radio" name="modo" value="verificar" {{ 'checked' if modo=='verificar' }}> Verificar como
  <select name="id_ver">{% for i in ids %}<option value="{{i}}" {{ 'selected' if i==id_ver }}>{{ bonito(i) }}</option>{% endfor %}</select></label>
 <label title="La foto ya es un recorte de la cara: se salta el detector (métodos _sd)"><input type="checkbox" name="sd" {{ 'checked' if sd }}> sin detector</label>
 <button>Analizar</button>
</form></div>

{% if error %}<div class="error">{{ error }}</div>{% endif %}

{% if r %}{% set a = r.a %}
<div class="card">
 {% if r.misma %}<p class="aviso">⚠️ Esta es exactamente la foto con la que se inscribió a {{ bonito(r.misma) }}: la distancia ≈ 0 no demuestra nada. Prueba con otra foto suya.</p>{% endif %}
 {% if r.verif %}{% set v = r.verif %}
  <div class="veredicto {{ 'ok' if v.ok else 'no' }}">{{ 'ACEPTADO' if v.ok else 'RECHAZADO' }} como {{ bonito(v.id) }}</div>
  <p>Distancia a {{ bonito(v.id) }}: <b>{{ '%.1f'|format(v.d) }}</b> (umbral {{ '%.1f'|format(a.umbral) }}) · es el nº {{ v.posicion }} más parecido de {{ ids|length }}.</p>
 {% else %}
  {% if a.identificado %}<div class="veredicto ok">IDENTIFICADO: {{ bonito(a.identificado) }}</div>
  {% else %}<div class="veredicto no">DESCONOCIDO</div>
   <p>Nadie está por debajo del umbral. El más parecido sería {{ bonito(a.mejor.id) }}, pero no lo bastante.</p>{% endif %}
  <p>Distancia al más cercano: <b>{{ '%.1f'|format(a.mejor.distancia) }}</b> · umbral {{ '%.1f'|format(a.umbral) }} (provisional)
   · confianza relativa {{ '%.0f'|format(a.mejor.confianza*100) }}% · margen sobre el 2º {{ '%.0f'|format(a.margen*100) }}%</p>
 {% endif %}
</div>

<div class="card"><div class="fila">
 <figure><img src="data:image/jpeg;base64,{{ r.foto }}"><figcaption>
  {% if a.deteccion %}Detección ({{ a.deteccion.cascada }}): cara en verde; ojos {{ 'detectados (amarillo)' if a.deteccion.ojos_detectados else 'NO detectados, posición estimada (rojo)' }}{% else %}Sin detector (_sd): la foto entra tal cual{% endif %}</figcaption></figure>
 <figure><img src="data:image/jpeg;base64,{{ r.alineada }}"><figcaption>Cara alineada: ojos siempre en el mismo sitio</figcaption></figure>
 <figure><img src="data:image/jpeg;base64,{{ r.normalizada }}"><figcaption>Normalizada (lo que entra a PCA): elipse, luz igualada</figcaption></figure>
 <figure><img src="data:image/jpeg;base64,{{ r.reconstruida }}"><figcaption>Reconstrucción desde el template ({{ a.template|length }} números): lo que PCA "ve"</figcaption></figure>
</div></div>

<div class="card"><h3 style="margin-top:0">¿Cómo ha llegado al veredicto?</h3>
 <table><tr><th>#</th><th></th><th>Famoso</th><th>Distancia</th><th>vs. umbral (línea)</th><th>Confianza relativa</th></tr>
 {% for c, mini in r.top %}<tr>
  <td>{{ loop.index }}</td><td>{% if mini %}<img class="mini" src="data:image/jpeg;base64,{{ mini }}">{% endif %}</td>
  <td>{{ bonito(c.id) }}</td><td>{{ '%.1f'|format(c.distancia) }}</td>
  <td><div class="barra"><span style="width:{{ (100*c.distancia/r.dmax)|round }}%;background:{{ 'var(--ok)' if c.distancia<=a.umbral else 'var(--no)' }}"></span><i style="left:{{ (100*a.umbral/r.dmax)|round }}%"></i></div></td>
  <td>{{ '%.1f'|format(c.confianza*100) }}%</td></tr>{% endfor %}
 </table>
 <p class="sub">Distancia: euclídea entre templates PCA (menor = más parecido). Se acepta si queda a la izquierda de la línea (umbral).
 La <b>confianza relativa</b> reparte el 100% entre los {{ ids|length }} inscritos según lo cerca que está cada uno: siempre hay un favorito,
 incluso con un desconocido, por eso lo que decide es el umbral, no este porcentaje.</p>
</div>
{% endif %}
</main></body></html>"""


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", 5000)), debug=False)

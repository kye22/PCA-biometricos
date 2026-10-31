# Reconocimiento facial con PCA — Sistemas Biométricos

Sistema de reconocimiento facial basado en **PCA (eigenfaces)** en Python, con base de datos en
`.csv`. Inscribe a 50 personas: las 49 del dataset y Álvaro Arbeloa.

```
foto ─► detector (YuNet) ─► control de calidad ─► alineado ─► normalización ─► PCA ─► template
                                                                                           │
                                                                  comparador (distancia) ◄─┴─► bd.csv
```

## Puesta en marcha

Requisitos: Python 3.10 o superior.

```bash
python -m venv .venv
.venv\Scripts\activate             # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

Copia `Dataset.tar.gz` (el dataset de la práctica, no está en el repo) en la raíz del proyecto y:

```bash
python scripts/montar.py           # descomprime, detecta y alinea caras, entrena PCA e inscribe a todos
python app/web.py                  # interfaz web en http://localhost:5000
```

`montar.py` lista foto por foto cómo ha ido la detección y termina con el umbral calculado.
Se puede repetir cuando se quiera: rehace el modelo y la BD desde cero.

### Interfaz web

Subes una foto y muestra la detección dibujada (cara y ojos), la cara alineada y normalizada, lo
que "ve" PCA, el veredicto (identificar, o verificar contra un famoso) y los 5 más parecidos con
su distancia, el umbral y la confianza relativa.

### Línea de comandos

```bash
python scripts/identificar.py <foto>
python scripts/verificar.py <id> <foto>
```

Ambos aceptan `--sd` (omitir el detector: la foto ya es un recorte de la cara).

### Como librería

```python
import sys; sys.path.insert(0, "src")        # o: pip install -e .
from sistema import inscribir, verificar, identificar

identificar("foto.jpg")                       # -> "adele" | None
verificar("alvaro_arbeloa_coca", "foto.jpg")  # -> True | False
```

| Entrada | Inscribir | Verificar | Identificar |
|---|---|---|---|
| foto | `inscribir(id, foto)` | `verificar(id, foto)` | `identificar(foto)` |
| foto sin detector | `inscribir_sd(id, foto)` | `verificar_sd(id, foto)` | `identificar_sd(foto)` |
| template | `inscribir_t(id, template)` | `verificar_t(id, template)` | `identificar_t(template)` |

`foto` puede ser una ruta, los bytes de un archivo o un array. Los ids son el nombre del archivo
del dataset sin el año (`serenna_williams_2017.jpg` → `serenna_williams`).

## Control de calidad

`verificar()` e `identificar()` rechazan la foto (excepción `CalidadInsuficiente`, con los motivos)
si no se puede decidir con fiabilidad:

| Motivo | Cuándo |
|---|---|
| `varias_caras` | hay otra cara de tamaño comparable (no se elige una por nuestra cuenta) |
| `cara_pequena` | menos de 30 px entre los ojos |
| `perfil` | la cara está muy girada (nariz desplazada respecto a los ojos) |
| `ojos_ocultos` | la zona de los ojos es mucho más oscura que frente y mejillas (gafas de sol) |
| `boca_oculta` | la zona de nariz y boca casi no tiene contraste (mascarilla) |

Si no hay ninguna cara se lanza `CaraNoEncontrada` (YuNet; Haar solo si encuentra los dos ojos).
`inscribir()` no aplica el control (se inscribe lo que trae el dataset; `montar.py` avisa) y los
métodos `_sd` tampoco, porque sin detector no hay puntos de la cara con los que medir.
El control no usa PCA. Umbrales y medidas en `src/sistema/calidad.py`.

## Tests

```bash
pytest
```

No necesitan fotos: usan caras sintéticas.

## Docker

```bash
docker build -t pca-biometricos .
docker run --rm -p 5000:5000 pca-biometricos     # monta todo y abre la web en :5000
```

## Qué hay en el repo

| Ruta | Qué es |
|---|---|
| `src/sistema/` | la librería: detector, preprocesado, PCA, comparador, BD y los 9 métodos |
| `app/web.py` | interfaz web |
| `scripts/` | `montar.py` (todo en un comando), `identificar.py`, `verificar.py` |
| `modelos/face_detection_yunet_2023mar.onnx` | detector de caras YuNet ([opencv_zoo](https://github.com/opencv/opencv_zoo)) |
| `datos/extra/` | foto de inscripción de Álvaro Arbeloa |
| `datos/ojos_manuales.json` | ojos marcados a mano si el detector fallara en alguna foto |
| `tests/` | pruebas automáticas |

Se generan al ejecutar `montar.py` (no se suben): `datos/fotos/`, `datos/bd.csv`,
`datos/inscritos.json` y `modelos/pca.npz` (modelo + umbral).

Variables de entorno opcionales: `SISTEMA_DATASET`, `SISTEMA_FOTOS`, `SISTEMA_BD`,
`SISTEMA_MODELO`, `SISTEMA_UMBRAL`, `SISTEMA_COMPONENTES`.

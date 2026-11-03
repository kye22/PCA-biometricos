# Reconocimiento facial con PCA — Sistemas Biométricos

Sistema de reconocimiento facial basado en **PCA (eigenfaces)** en Python, con base de datos en
`.csv`. Inscribe a 50 personas: las 49 del dataset y Álvaro Arbeloa, con hasta 3 fotos por persona.

```
foto ─► detector (YuNet) ─► control de calidad ─► alineado ─► normalización ─► PCA ─► template
                                                                                           │
                                                   comparador (coseno) ◄─ bd.csv (cifrada y firmada)
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
python scripts/montar.py           # descomprime, detecta y alinea caras, crea la clave e inscribe a todos
python app/web.py                  # interfaz web en http://localhost:5000
```

`montar.py` lista foto por foto cómo ha ido la detección y termina con el umbral calculado
(`--umbral 0.45` lo fija a mano). Se puede repetir cuando se quiera: rehace el modelo y la BD desde
cero, y conserva la clave si ya existe.

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

## Extractor PCA genérico

El extractor **no se entrena con las personas inscritas**. `modelos/pca_base.npz` (en el repo) es
un PCA de 50 eigenfaces entrenado una vez con 6.300 caras de
[FairFace](https://github.com/joojs/fairface) (Kärkkäinen y Joo, 2021; CC BY 4.0): **900 por cada uno
de sus 7 grupos étnicos**, para que ningún grupo quede infrarrepresentado. La BD (`bd.csv`) solo
guarda a quien tiene acceso, e inscribir a alguien no cambia el modelo.

Los templates se **blanquean** (cada coeficiente dividido por su desviación típica) y se comparan
con **distancia coseno** (de 0 a 2). El modelo guarda también los límites de una "cara normal"
(norma del template y error de reconstrucción) que usan las defensas de abajo.

Para regenerarlo (no hace falta): descarga el split de validación de FairFace indicado en
`scripts/entrenar_pca.py` en `datos/base_generica/`, `pip install pyarrow` y
`python scripts/entrenar_pca.py`. Si cambia, copia la huella que imprime en
`config.HUELLA_MODELO_BASE` (`montar.py` se niega a usar un extractor distinto del fijado).

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

## Seguridad

Supuesto: el rival tiene el código, el modelo y la BD, pero no la **clave secreta**.
`montar.py` la crea en `datos/clave.key` (no se sube a git); también se puede pasar en hexadecimal
en la variable `SISTEMA_CLAVE` (recomendable en un despliegue: lejos del disco de la BD).

| Defensa | Contra | Excepción |
|---|---|---|
| Templates cifrados con AES-256-GCM (el id como dato asociado) | leer la BD para reconstruir caras o reutilizar templates | — |
| Firma HMAC de `bd.csv` (en `bd.firma`) | añadir, borrar, cambiar o mover filas | `Manipulado` |
| Firma HMAC de `pca.npz` (incluye el umbral) y huella fija de `pca_base.npz` | cambiar el modelo o el umbral | `Manipulado` |
| Norma del template dentro del rango de caras reales | templates fabricados en `_t` (ceros, extremos) | `TemplateInvalido` |
| Error de reconstrucción PCA y YuNet sobre el recorte | imágenes que no son caras en `_sd` | `NoPareceCara` |
| Ids solo con letras, números y `_ ( ) . -` | fórmulas o comas en el `.csv` | `IdInvalido` |
| Imágenes de más de 40 Mpx rechazadas antes de descomprimir | "bombas" de descompresión | `ValueError` |
| La web limita a 20 análisis por minuto por cliente | *hill-climbing* con las distancias de la web | HTTP 429 |

Con una BD o un modelo manipulados el sistema no decide nada (falla cerrado): se regeneran con
`montar.py`.

## Tests

```bash
pytest
```

No necesitan fotos: usan caras sintéticas y una clave de prueba.

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
| `modelos/pca_base.npz` | extractor PCA genérico (ver arriba) |
| `datos/extra/` | foto de inscripción de Álvaro Arbeloa y, en `datos/extra/<id>/`, fotos adicionales de inscritos (Wikimedia Commons; autor y licencia en `fuentes.csv`) |
| `datos/ojos_manuales.json` | ojos marcados a mano si el detector fallara en alguna foto |
| `tests/` | pruebas automáticas |

Se generan al ejecutar `montar.py` (no se suben): `datos/fotos/`, `datos/bd.csv` y `datos/bd.firma`,
`datos/inscritos.json`, `datos/clave.key` y `modelos/pca.npz` (modelo + umbral, firmado).

Variables de entorno opcionales: `SISTEMA_DATASET`, `SISTEMA_FOTOS`, `SISTEMA_BD`,
`SISTEMA_MODELO`, `SISTEMA_UMBRAL`, `SISTEMA_CLAVE`, `SISTEMA_CLAVE_FICHERO`; en la web, `MAX_ANALISIS`.

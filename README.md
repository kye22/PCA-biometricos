# Reconocimiento facial con PCA — Sistemas Biométricos

Sistema de reconocimiento facial basado en **PCA (eigenfaces)**, desarrollado en Python para la asignatura de Sistemas Biométricos.

El sistema permite inscribir, verificar e identificar personas a partir de fotografías faciales. Utiliza una base de datos en formato CSV que almacena los templates biométricos cifrados.

El proyecto trabaja con 50 identidades: las 49 presentes en el dataset proporcionado por el profesor y Álvaro Arbeloa, incorporado por el grupo.

El enunciado original de la práctica se encuentra en [`Prácticas.md`](Prácticas.md).

## 1. Arquitectura del sistema

El procesamiento de una imagen sigue, de forma general, estas etapas:

1. **Detección facial:** localización del rostro mediante YuNet y cascadas Haar.
2. **Control de calidad:** comprobación de distintas características de la imagen.
3. **Alineamiento:** corrección de la posición de la cara utilizando los ojos como referencia.
4. **Normalización:** preparación de la imagen para el extractor.
5. **Extracción PCA:** transformación de la imagen en un template de características.
6. **Comparación:** cálculo de distancias entre templates mediante distancia coseno.
7. **Decisión:** aceptación, rechazo o identificación según el umbral establecido.

El sistema dispone de tres operaciones principales:

- **Inscripción:** almacena los templates asociados a una identidad.
- **Verificación (1:1):** comprueba si una imagen corresponde a una identidad declarada.
- **Identificación (1:N):** busca la identidad más cercana entre las personas inscritas.

La implementación principal se encuentra en `src/sistema/`.

## 2. Requisitos

Para ejecutar el proyecto se necesita:

- Python 3.10 o superior. Se recomienda Python 3.11.
- OpenCV 4.x.
- Las dependencias definidas en `pyproject.toml`.
- El archivo `Dataset.tar.gz`, proporcionado por el profesor, para realizar la inscripción inicial.

El proyecto utiliza `uv.lock` para facilitar una instalación reproducible de las dependencias.

También puede ejecutarse mediante Docker.

## 3. Instalación y ejecución local

### 3.1. Instalación recomendada con uv

Desde una terminal PowerShell de VS Code, situada en la raíz del repositorio:

```powershell
py -m uv sync --locked --extra dev
```

Este comando crea o actualiza el entorno virtual `.venv` e instala las dependencias del proyecto.

Para comprobar la instalación:

```powershell
py -m uv run --locked --extra dev python -m pytest -q
```

Los tests automatizados no necesitan el dataset del profesor.

### 3.2. Instalación alternativa con venv y pip

Si no se desea utilizar `uv`, también es posible crear un entorno virtual manualmente.

En Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

**Importante:** el proyecto requiere OpenCV 4.x. Se ha restringido la versión de la dependencia para evitar incompatibilidades con las funciones de detección utilizadas.

También se ha corregido la carga de los clasificadores Haar para permitir su funcionamiento en Windows cuando la ruta del proyecto contiene caracteres Unicode, como tildes.

## 4. Preparación del dataset

El archivo `Dataset.tar.gz` no se incluye en Git debido a su tamaño y a que ha sido proporcionado por el profesor.

Debe colocarse en la raíz del repositorio:

```text
PCA-biometricos/
├── Dataset.tar.gz
├── README.md
├── pyproject.toml
├── scripts/
├── src/
├── tests/
├── datos/
└── modelos/
```

El script `scripts/montar.py` se encarga de:

1. Extraer las fotografías del dataset, si todavía no están disponibles.
2. Incorporar las imágenes adicionales de `datos/extra/`.
3. Detectar y alinear los rostros.
4. Cargar el extractor PCA genérico y preparar los templates biométricos.
5. Crear o reutilizar la clave secreta del sistema.
6. Inscribir las identidades en la base de datos.
7. Calcular un umbral provisional de comparación.

### 4.1. Primera ejecución

Con `uv`:

```powershell
py -m uv run --locked --extra dev python scripts/montar.py
```

Con el entorno virtual activado:

```powershell
python scripts/montar.py
```

Durante la ejecución se muestra información sobre la detección de cada fotografía y los posibles problemas encontrados.

Al finalizar, se indica el número de personas inscritas y el umbral provisional calculado.

### 4.2. Protección frente a reconstrucciones accidentales

**El script no reconstruye automáticamente un sistema que ya esté montado.**

Si detecta que existe una base de datos, su firma o un modelo generado previamente, detiene la ejecución para evitar sobrescribir información por accidente.

Para reconstruir deliberadamente el sistema, debe utilizarse:

```powershell
py -m uv run --locked --extra dev python scripts/montar.py --recrear
```

O, con el entorno virtual activado:

```powershell
python scripts/montar.py --recrear
```

**Advertencia:** `--recrear` reconstruye la base de datos y el modelo operativo. Los templates y resultados de inscripción anteriores se sustituyen por los de la nueva ejecución.

La clave secreta existente se conserva.

Por tanto, debe utilizarse `--recrear` únicamente cuando se quiera volver a montar el sistema de forma consciente.

### 4.3. Extractor genérico obligatorio

El montaje necesita el archivo:

```text
modelos/pca_base.npz
```

Este es el extractor PCA genérico entrenado previamente y distribuido con el repositorio.

**El sistema no entrena un PCA alternativo con las fotografías inscritas si falta este archivo.**

En ese caso, `montar.py` cancela la ejecución y muestra un mensaje de error.

Además, cuando el archivo está presente, se verifica que su huella coincide con la establecida en `config.HUELLA_MODELO_BASE`.

Estas comprobaciones permiten mantener un extractor consistente entre diferentes montajes y evitan sustituirlo accidentalmente por otro modelo.

### 4.4. Umbral de decisión

Por defecto, `montar.py` calcula un **umbral provisional** a partir de las distancias entre identidades diferentes.

Se puede ajustar la proporción utilizada en ese cálculo:

```powershell
python scripts/montar.py --far 0.02
```

También se puede fijar manualmente un umbral:

```powershell
python scripts/montar.py --umbral 0.45
```

Si ya existe un sistema montado y se desea reconstruirlo con otro umbral, será necesario añadir `--recrear`.

**Importante:** el umbral calculado automáticamente durante el montaje es provisional. No constituye por sí solo una evaluación biométrica completa.

Para evaluar correctamente el sistema será necesario utilizar fotografías independientes de las empleadas en la inscripción y calcular métricas como FAR y FRR.

## 5. Interfaz web

Una vez montado el sistema, puede iniciarse la aplicación:

Con `uv`:

```powershell
py -m uv run --locked --extra dev python app/web.py
```

Con el entorno virtual activado:

```powershell
python app/web.py
```

La interfaz estará disponible en:

http://localhost:5000

Desde ella es posible:

- Subir fotografías faciales.
- Visualizar la detección y el procesamiento de la cara.
- Realizar operaciones de identificación y verificación.
- Consultar los candidatos más parecidos.
- Observar las distancias y el umbral utilizados en la decisión.

## 6. Ejecución desde la línea de comandos

El repositorio también incluye scripts para realizar operaciones biométricas sin utilizar la interfaz web.

### Identificación

```powershell
python scripts/identificar.py foto.jpg
```

### Verificación

```powershell
python scripts/verificar.py identificador foto.jpg
```

Ambos scripts admiten la opción `--sd`, destinada a trabajar con imágenes faciales ya recortadas.

## 7. Uso como librería

Las operaciones principales se encuentran disponibles mediante la API de `sistema`.

Ejemplo:

```python
import sys
sys.path.insert(0, "src")

from sistema import inscribir, verificar, identificar

resultado = identificar("foto.jpg")
es_correcto = verificar("adele", "foto.jpg")
```

La API incluye tres modalidades de entrada:

| Modalidad | Inscripción | Verificación | Identificación |
|---|---|---|---|
| Fotografía | `inscribir(id, foto)` | `verificar(id, foto)` | `identificar(foto)` |
| Sin detector inicial | `inscribir_sd(id, foto)` | `verificar_sd(id, foto)` | `identificar_sd(foto)` |
| Template | `inscribir_t(id, template)` | `verificar_t(id, template)` | `identificar_t(template)` |

La modalidad `_t` permite trabajar directamente con templates.

La modalidad `_sd` evita la detección y el alineamiento iniciales, aunque algunas operaciones mantienen comprobaciones adicionales de seguridad mediante YuNet.

## 8. Extractor PCA

El sistema utiliza **PCA (Principal Component Analysis)** para reducir la dimensionalidad de las imágenes faciales y obtener sus representaciones biométricas.

El repositorio contiene un extractor PCA genérico en:

```text
modelos/pca_base.npz
```

Este modelo se entrenó previamente utilizando imágenes de FairFace, de manera independiente a las identidades inscritas en el sistema.

La implementación actual combina características obtenidas de la cara completa y de una región interior de la cara.

Los coeficientes se normalizan y los templates se comparan mediante distancia coseno.

### Independencia del extractor

El extractor PCA utilizado durante la inscripción es el modelo genérico incluido en el repositorio.

Si dicho modelo no está disponible, el montaje se cancela.

Por tanto:

- La inscripción de una identidad no requiere volver a entrenar el PCA.
- La incorporación de nuevas personas no modifica el extractor.
- Los templates se obtienen utilizando una representación común.
- El montaje no sustituye el extractor por otro entrenado con los propios inscritos.

Esta separación entre entrenamiento del extractor e inscripción es importante para la evaluación del sistema biométrico.

## 9. Control de calidad de las imágenes

El sistema incorpora comprobaciones orientadas a detectar fotografías que puedan dificultar el reconocimiento.

Entre las condiciones contempladas se encuentran:

| Condición | Descripción |
|---|---|
| Varias caras | Hay más de un rostro relevante en la fotografía. |
| Cara pequeña | El rostro no tiene suficiente resolución. |
| Perfil | La orientación de la cara se aleja de una posición frontal. |
| Ojos ocultos | La región de los ojos presenta características compatibles con una oclusión. |
| Boca oculta | La región inferior de la cara presenta características compatibles con una oclusión. |

Si no se encuentra ningún rostro, puede producirse la excepción `CaraNoEncontrada`.

Si la fotografía no satisface los criterios de calidad, puede producirse `CalidadInsuficiente`.

Estos controles son heurísticos y deberán tenerse en cuenta al estudiar las fortalezas y debilidades del sistema.

## 10. Medidas de seguridad

La implementación incorpora distintas defensas para proteger los datos biométricos y detectar modificaciones no autorizadas.

| Medida | Objetivo |
|---|---|
| Cifrado AES-256-GCM | Proteger los templates almacenados en la base de datos. |
| Firma HMAC de la base de datos | Detectar modificaciones en el archivo CSV. |
| Firma HMAC del modelo operativo | Detectar cambios no autorizados en el modelo y su umbral. |
| Verificación de la huella del PCA genérico | Comprobar la identidad del extractor utilizado. |
| Validación de templates | Rechazar determinadas representaciones anómalas. |
| Validación de identificadores | Evitar entradas no permitidas en los identificadores. |
| Límites en el procesamiento de imágenes | Reducir riesgos asociados a entradas excesivamente grandes. |
| Limitación de peticiones web | Dificultar determinados ataques repetitivos. |

La clave secreta se almacena por defecto en:

```text
datos/clave.key
```

Este archivo no debe incluirse en Git.

El sistema también permite configurar la clave mediante variables de entorno.

**Limitación conocida:** la protección de integridad de la base de datos presupone que se dispone de los archivos necesarios para verificarla. La eliminación simultánea de la base de datos y su firma es un escenario que debe tratarse separadamente durante la evaluación de seguridad.

## 11. Tests automatizados

El repositorio dispone de pruebas unitarias en `tests/`.

Para ejecutarlas:

```powershell
py -m uv run --locked --extra dev python -m pytest -q
```

Las pruebas cubren diferentes componentes del sistema, incluyendo operaciones de la API, detección, calidad, templates y mecanismos de seguridad.

Los tests emplean datos preparados para las pruebas y no requieren el dataset original del profesor.

Se ha comprobado su ejecución en Windows con OpenCV 4.x.

### Integración continua

El repositorio incluye un workflow de GitHub Actions en:

```text
.github/workflows/tests.yml
```

Este workflow permite ejecutar automáticamente los tests en GitHub.

La ejecución local de `pytest` sigue siendo recomendable antes de realizar commits o publicar cambios.

## 12. Ejecución con Docker

El repositorio incluye un `Dockerfile` para ejecutar el sistema sin instalar manualmente sus dependencias de Python.

El archivo `Dataset.tar.gz` debe encontrarse en la raíz del proyecto.

### Construcción de la imagen

```powershell
docker build -t pca-biometricos .
```

### Ejecución en PowerShell

```powershell
docker run --rm -p 5000:5000 --mount "type=bind,source=${PWD}/Dataset.tar.gz,target=/app/Dataset.tar.gz,readonly" pca-biometricos
```

El dataset se proporciona al contenedor mediante un montaje de solo lectura.

De este modo, no es necesario incorporar el archivo del profesor dentro de la imagen Docker.

La imagen sí debe incluir los recursos del repositorio necesarios para ejecutar el extractor y los detectores.

Una vez iniciado el contenedor, la aplicación está disponible en:

http://localhost:5000

**Importante:** en esta configuración, la base de datos y los archivos generados se almacenan dentro del contenedor. Al eliminarlo con `--rm`, esos resultados no se conservan.

Para conservar los datos entre ejecuciones sería necesario configurar volúmenes adicionales.

## 13. Estructura del repositorio

| Ruta | Contenido |
|---|---|
| `app/` | Aplicación web. |
| `src/sistema/` | Implementación de la librería biométrica. |
| `scripts/montar.py` | Preparación e inscripción inicial del sistema. |
| `scripts/identificar.py` | Identificación mediante línea de comandos. |
| `scripts/verificar.py` | Verificación mediante línea de comandos. |
| `scripts/entrenar_pca.py` | Entrenamiento del extractor PCA genérico. |
| `datos/extra/` | Fotografías adicionales utilizadas en el proyecto. |
| `datos/ojos_manuales.json` | Referencias manuales para determinadas fotografías. |
| `modelos/pca_base.npz` | Extractor PCA genérico. |
| `modelos/face_detection_yunet_2023mar.onnx` | Modelo de detección facial YuNet. |
| `tests/` | Pruebas automatizadas. |
| `.github/workflows/tests.yml` | Ejecución automática de tests en GitHub Actions. |
| `Dockerfile` | Configuración de la imagen Docker. |
| `pyproject.toml` | Configuración del proyecto y sus dependencias. |
| `uv.lock` | Versiones bloqueadas de las dependencias. |
| `Prácticas.md` | Enunciado original de la práctica. |

Durante el montaje se generan archivos que no deben subirse al repositorio, entre ellos:

- `datos/fotos/`: fotografías extraídas del dataset.
- `datos/bd.csv`: base de datos biométrica.
- `datos/bd.firma`: firma de integridad de la base de datos.
- `datos/clave.key`: clave secreta.
- `datos/inscritos.json`: información de las fotografías inscritas.
- `modelos/pca.npz`: modelo operativo y umbral.

Los directorios `.venv/` y `.pytest_cache/` también son archivos locales generados automáticamente y no deben versionarse.

## 14. Estado del proyecto y evaluación pendiente

El repositorio implementa las funciones principales del sistema biométrico facial y dispone de pruebas automatizadas.

Se han realizado correcciones relacionadas con:

- La compatibilidad de OpenCV.
- La carga de los clasificadores Haar en rutas de Windows con caracteres Unicode.
- La ejecución mediante Docker.
- Las instrucciones de instalación y ejecución.
- La protección frente a reconstrucciones accidentales de la base de datos.
- El uso obligatorio del PCA genérico durante el montaje.
- La integración de pruebas mediante GitHub Actions.

Queda pendiente desarrollar un protocolo de evaluación específico que permita medir el rendimiento y estudiar las limitaciones del sistema.

La evaluación deberá considerar, entre otros aspectos:

- La separación entre imágenes de inscripción y de prueba.
- El rendimiento en verificación e identificación.
- Las tasas de falsa aceptación y falso rechazo.
- La selección y justificación del umbral.
- El comportamiento ante variaciones de las fotografías.
- La influencia de la detección y del control de calidad.
- La resistencia y las limitaciones de las medidas de seguridad.
- La facilidad de instalación y reproducción del sistema.

Los resultados de esa evaluación se incorporarán posteriormente al informe y a la presentación de la práctica.
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
├── evaluacion/
├── datos/
└── modelos/
```

El script `scripts/montar.py` se encarga de:

1. Extraer las fotografías del dataset, si todavía no están disponibles.
2. Seleccionar las fotografías que deben inscribirse.
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

**Atención:** sin `--manifiesto`, el script conserva el comportamiento original del repositorio y utiliza tanto las fotografías del profesor como las adicionales de `datos/extra/`.

Para realizar una evaluación independiente, debe utilizarse el manifiesto de inscripción descrito a continuación.

### 4.2. Separación de fotografías para evaluación

Una evaluación biométrica debe evitar que las mismas fotografías se utilicen simultáneamente para inscribir identidades y para medir el rendimiento del sistema.

Para ello se incluye el script:

```text
evaluacion/particiones.py
```

Este script genera una distribución reproducible de las imágenes utilizando una semilla fija.

Se distinguen cuatro grupos:

| Grupo | Utilización |
|---|---|
| `inscripcion` | Fotografías para construir la base de datos biométrica. |
| `calibracion` | Fotografías reservadas para seleccionar el umbral. |
| `prueba` | Fotografías reservadas para medir el rendimiento final. |
| `desconocidos` | Fotografías de personas no inscritas, si están disponibles. |

La distribución utilizada por el proyecto reserva las fotografías originales del profesor para inscripción, junto con la fotografía principal de Álvaro Arbeloa.

Las fotografías adicionales se destinan a calibración o prueba.

#### Generar la partición

Con `uv`:

```powershell
py -m uv run --locked --extra dev python evaluacion/particiones.py --semilla 42
```

Con el entorno activado:

```powershell
python evaluacion/particiones.py --semilla 42
```

Se genera el archivo:

```text
evaluacion/particion.json
```

El manifiesto contiene las rutas relativas de las fotografías asignadas a cada grupo.

La generación comprueba que no existan solapamientos indebidos entre los grupos. También utiliza hashes SHA-256 para detectar archivos con contenido exactamente idéntico.

Esta comprobación no sustituye una inspección manual de imágenes visualmente duplicadas o casi idénticas.

### 4.3. Montaje utilizando el manifiesto

Una vez generado el manifiesto, se puede montar el sistema utilizando únicamente las fotografías de inscripción:

```powershell
python scripts/montar.py --manifiesto evaluacion/particion.json
```

Con `uv`:

```powershell
py -m uv run --locked --extra dev python scripts/montar.py --manifiesto evaluacion/particion.json
```

El script carga el manifiesto, comprueba su validez y utiliza exclusivamente las imágenes del grupo `inscripcion`.

**Las fotografías de calibración y prueba no se utilizan para crear templates de inscripción.**

Este procedimiento es el recomendado para preparar el sistema antes de evaluarlo.

### 4.4. Protección frente a reconstrucciones accidentales

**El script no reconstruye automáticamente un sistema que ya esté montado.**

Si detecta que existe una base de datos, su firma o un modelo generado previamente, detiene la ejecución para evitar sobrescribir información por accidente.

Para reconstruir deliberadamente el sistema utilizando el manifiesto:

```powershell
python scripts/montar.py --manifiesto evaluacion/particion.json --recrear
```

Con `uv`:

```powershell
py -m uv run --locked --extra dev python scripts/montar.py --manifiesto evaluacion/particion.json --recrear
```

**Advertencia:** `--recrear` reconstruye la base de datos y el modelo operativo. Los templates y resultados de inscripción anteriores se sustituyen por los de la nueva ejecución.

La clave secreta existente se conserva.

Por tanto, debe utilizarse `--recrear` únicamente cuando se quiera volver a montar el sistema de forma consciente.

### 4.5. Extractor genérico obligatorio

El montaje necesita el archivo:

```text
modelos/pca_base.npz
```

Este es el extractor PCA genérico entrenado previamente y distribuido con el repositorio.

**El sistema no entrena un PCA alternativo con las fotografías inscritas si falta este archivo.**

En ese caso, `montar.py` cancela la ejecución y muestra un mensaje de error.

Además, cuando el archivo está presente, se verifica que su huella coincide con la establecida en `config.HUELLA_MODELO_BASE`.

Estas comprobaciones permiten mantener un extractor consistente entre diferentes montajes.

### 4.6. Validaciones previas al montaje

Antes de modificar la base de datos, el script realiza varias comprobaciones:

- Que los parámetros introducidos sean válidos.
- Que exista el extractor PCA genérico.
- Que haya suficientes identidades para calcular el umbral provisional.
- Que las fotografías puedan detectarse y alinearse correctamente.

Si una fotografía falla durante la fase inicial de detección o alineamiento, el montaje se cancela antes de reconstruir la base de datos.

Esto reduce el riesgo de generar una inscripción incompleta.

No obstante, el montaje todavía no implementa una sustitución completamente transaccional de todos los archivos: un fallo inesperado posterior podría producir una escritura parcial.

### 4.7. Umbral de decisión

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

Para evaluar correctamente el sistema será necesario utilizar las fotografías independientes reservadas y calcular métricas como FAR y FRR.

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

La separación entre el entrenamiento del extractor, la inscripción y la evaluación es importante para interpretar correctamente los resultados biométricos.

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

También se incluyen pruebas para comprobar la reproducibilidad de las particiones y rechazar fotografías duplicadas entre grupos.

Los tests emplean datos preparados para las pruebas y no requieren el dataset original del profesor.

### Integración continua

El repositorio incluye un workflow de GitHub Actions en:

```text
.github/workflows/tests.yml
```

Este workflow permite ejecutar automáticamente los tests en GitHub.

La ejecución local de `pytest` sigue siendo recomendable antes de realizar commits o publicar cambios.

## 12. Ejecución con Docker

El repositorio incluye un `Dockerfile` que permite entregar el sistema a otro grupo sin que tenga que instalar manualmente sus dependencias de Python.

El archivo `Dataset.tar.gz` debe encontrarse en la raíz del proyecto.

### 12.1. Construir la imagen

Desde PowerShell:

```powershell
docker build -t pca-biometricos .
```

### 12.2. Ejecutar el contenedor

```powershell
docker run --rm -p 5000:5000 --mount "type=bind,source=${PWD}/Dataset.tar.gz,target=/app/Dataset.tar.gz,readonly" pca-biometricos
```

El dataset se proporciona al contenedor mediante un montaje de solo lectura.

De este modo, no es necesario incorporar el archivo del profesor dentro de la imagen Docker.

### 12.3. Montaje automático con particiones

Al iniciar el contenedor se ejecuta automáticamente el siguiente proceso:

1. Se extraen las fotografías del dataset del profesor.
2. Se genera una partición reproducible con semilla `42`.
3. Se valida el manifiesto de partición.
4. Se monta el sistema utilizando únicamente el grupo `inscripcion`.
5. Se inicia la aplicación web.

Las fotografías adicionales reservadas para calibración y prueba no se inscriben en la base de datos del contenedor.

Esto permite entregar al grupo rival un sistema preparado para recibir fotografías nuevas, distintas de las utilizadas en la inscripción.

### 12.4. Acceder a la aplicación

Una vez iniciado el contenedor, abre:

http://localhost:5000

Desde la interfaz web pueden realizarse operaciones de identificación y verificación.

### 12.5. Persistencia de los datos

En esta configuración, la base de datos y los archivos generados se almacenan dentro del contenedor.

Al eliminarlo con `--rm`, esos resultados no se conservan.

Para conservar los datos entre ejecuciones sería necesario configurar volúmenes adicionales.

El extractor PCA genérico y los archivos necesarios para el funcionamiento del sistema sí están incluidos en la imagen Docker.

## 13. Estructura del repositorio

| Ruta | Contenido |
|---|---|
| `app/` | Aplicación web. |
| `src/sistema/` | Implementación de la librería biométrica. |
| `scripts/montar.py` | Preparación e inscripción inicial del sistema. |
| `scripts/identificar.py` | Identificación mediante línea de comandos. |
| `scripts/verificar.py` | Verificación mediante línea de comandos. |
| `scripts/entrenar_pca.py` | Entrenamiento del extractor PCA genérico. |
| `evaluacion/particiones.py` | Generación de particiones reproducibles. |
| `datos/extra/` | Fotografías adicionales utilizadas en el proyecto. |
| `datos/ojos_manuales.json` | Referencias manuales para determinadas fotografías. |
| `modelos/pca_base.npz` | Extractor PCA genérico. |
| `modelos/face_detection_yunet_2023mar.onnx` | Modelo de detección facial YuNet. |
| `tests/` | Pruebas automatizadas. |
| `.github/workflows/tests.yml` | Ejecución automática de tests en GitHub Actions. |
| `Dockerfile` | Configuración de la imagen Docker. |
| `.dockerignore` | Exclusiones utilizadas al construir la imagen. |
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
- `evaluacion/particion.json`: manifiesto generado de las particiones.

Los directorios `.venv/` y `.pytest_cache/` también son archivos locales generados automáticamente y no deben versionarse.

## 14. Estado del proyecto y evaluación pendiente

El repositorio implementa las funciones principales del sistema biométrico facial y dispone de pruebas automatizadas.

Se han realizado correcciones y mejoras relacionadas con:

- La compatibilidad de OpenCV.
- La carga de los clasificadores Haar en rutas de Windows con caracteres Unicode.
- La ejecución mediante Docker.
- Las instrucciones de instalación y ejecución.
- La protección frente a reconstrucciones accidentales de la base de datos.
- El uso obligatorio del PCA genérico durante el montaje.
- La cancelación del montaje ante errores de detección iniciales.
- La generación de particiones reproducibles.
- El montaje mediante un manifiesto de inscripción.
- La preparación de Docker para utilizar únicamente las fotografías de inscripción.
- La integración de pruebas mediante GitHub Actions.

Queda pendiente desarrollar el protocolo de evaluación cuantitativa que permita medir el rendimiento y estudiar las limitaciones del sistema.

La evaluación deberá considerar, entre otros aspectos:

- El rendimiento en verificación e identificación.
- Las tasas de falsa aceptación y falso rechazo.
- La selección y justificación del umbral.
- El comportamiento ante variaciones de las fotografías.
- La influencia de la detección y del control de calidad.
- La resistencia y las limitaciones de las medidas de seguridad.
- La facilidad de instalación y reproducción del sistema.

Se distinguirán los resultados de evaluación propia de los resultados obtenidos por el grupo rival con fotografías externas.

Los resultados se incorporarán posteriormente al informe y a la presentación de la práctica.
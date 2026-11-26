# Reconocimiento facial con PCA — Sistemas Biométricos

Sistema de reconocimiento facial desarrollado en Python y basado en
**PCA (Principal Component Analysis / Eigenfaces)**.

El sistema utiliza una base de datos CSV y permite inscribir, verificar
e identificar personas mediante fotografías faciales.

La base de datos contiene 50 identidades:
- 49 personas del dataset proporcionado por el profesor.
- Álvaro Arbeloa, elegido por el grupo.

Se permite inscribir varias fotografías por persona, almacenando
un template diferente para cada una.

## Arquitectura del sistema

El reconocimiento facial sigue el siguiente proceso:

```text
Fotografía
    |
    v
Detector facial (YuNet / Haar)
    |
    v
Alineamiento y control de calidad
    |
    v
Normalización de la cara
    |
    v
Extracción de características PCA
    |
    v
Template facial
    |
    v
Comparación mediante distancia coseno
    |
    v
Base de datos CSV cifrada y firmada
    |
    v
Decisión: verificación / identificación
```

## 1. Requisitos

Para ejecutar el proyecto localmente se necesita:

- Python 3.10 o superior (recomendado Python 3.11).
- Git.
- El archivo `Dataset.tar.gz` proporcionado por el profesor.

Opcionalmente:

- Visual Studio Code como entorno de desarrollo.
- Docker Desktop para ejecutar el sistema mediante contenedores.

Las dependencias de Python se encuentran en `pyproject.toml`
y pueden instalarse utilizando `requirements.txt`.

El proyecto utiliza OpenCV 4.x para garantizar la compatibilidad
con los detectores faciales implementados.

## 2. Instalación local

### 2.1. Windows (PowerShell / VS Code)

Abre una terminal de PowerShell desde la raíz del repositorio.

Crea un entorno virtual:

```powershell
py -3 -m venv .venv
```

Actívalo:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```powershell
python -m pip install -r requirements.txt
```

Si PowerShell impide activar el entorno virtual, puedes utilizar
directamente su intérprete:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

En este último caso, también tendrás que utilizar ese intérprete
para ejecutar los scripts.

### 2.2. Linux / macOS

Desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2.3. Instalación alternativa con uv

El repositorio también dispone de `uv.lock`, que permite
reproducir las versiones de las dependencias.

Si tienes instalado `uv`, puedes ejecutar:

```bash
uv sync --extra dev
```

Para ejecutar un script mediante `uv`:

```bash
uv run python scripts/montar.py
```

## 3. Preparación del dataset

El dataset de la práctica se proporciona por separado
y no está incluido en el repositorio.

Coloca el archivo:

```text
Dataset.tar.gz
```

en la raíz del proyecto.

La estructura esperada es:

```text
PCA-biometricos/
    |
    |-- Dataset.tar.gz
    |-- README.md
    |-- Dockerfile
    |-- pyproject.toml
    |-- requirements.txt
    |
    |-- src/
    |-- scripts/
    |-- app/
    |-- datos/
    |-- modelos/
    |-- tests/
```

No es necesario descomprimir el dataset manualmente.

El script de montaje se encarga de extraer las fotografías
en `datos/fotos/`.

El sistema también incorpora fotografías adicionales
en `datos/extra/`, incluyendo las de Álvaro Arbeloa.

## 4. Montaje inicial del sistema

Una vez instaladas las dependencias y colocado el dataset,
ejecuta:

```bash
python scripts/montar.py
```

Este script realiza automáticamente las siguientes operaciones:

1. Descomprime `Dataset.tar.gz` si todavía no se ha extraído.
2. Reúne las fotografías del profesor y las adicionales.
3. Detecta y alinea las caras.
4. Comprueba la calidad de las fotografías e informa de posibles problemas.
5. Carga el extractor PCA genérico.
6. Genera una clave criptográfica si todavía no existe.
7. Inscribe las identidades en la base de datos CSV.
8. Calcula un umbral provisional de reconocimiento.

Al finalizar, muestra información sobre las fotografías procesadas,
las personas inscritas y el umbral obtenido.

### Umbral de reconocimiento

El sistema compara templates mediante distancia coseno.

Por defecto, `montar.py` calcula un umbral provisional
a partir de las distancias entre personas distintas.

También es posible especificar uno manualmente:

```bash
python scripts/montar.py --umbral 0.45
```

**Importante:** el umbral calculado durante el montaje es
provisional y no equivale a una FAR medida sobre fotografías
independientes.

### Advertencia sobre el montaje

Volver a ejecutar `montar.py` reconstruye la base de datos
y puede sobrescribir los resultados de inscripciones anteriores.

Por tanto, no debe ejecutarse nuevamente si se desea conservar
la base de datos actual.

La clave criptográfica existente se conserva, salvo que
se elimine expresamente.

## 5. Interfaz web

Una vez montado el sistema, ejecuta:

```bash
python app/web.py
```

Abre un navegador y accede a:

http://localhost:5000

La interfaz permite:

- Subir una fotografía facial.
- Visualizar la detección de la cara y los ojos.
- Observar la cara alineada y normalizada.
- Visualizar una reconstrucción aproximada mediante PCA.
- Identificar a la persona más parecida.
- Verificar una identidad seleccionada.
- Consultar los cinco candidatos más cercanos.
- Observar las distancias y el umbral de decisión.

La confianza mostrada en la interfaz es una medida relativa
entre los candidatos, no una probabilidad calibrada de identidad.

## 6. Ejecución desde la terminal

El repositorio incluye scripts para realizar operaciones
sin utilizar la interfaz web.

### Identificación

```bash
python scripts/identificar.py <ruta_fotografia>
```

Ejemplo:

```bash
python scripts/identificar.py foto.jpg
```

### Verificación

```bash
python scripts/verificar.py <identidad> <ruta_fotografia>
```

Ejemplo:

```bash
python scripts/verificar.py adele foto.jpg
```

Ambos scripts admiten la opción `--sd` cuando se proporciona
una imagen con la cara previamente recortada.

## 7. API del sistema

El sistema implementa los nueve métodos exigidos por el enunciado.

| Entrada | Inscripción | Verificación | Identificación |
|---|---|---|---|
| Fotografía | `inscribir(id, foto)` | `verificar(id, foto)` | `identificar(foto)` |
| Fotografía sin detección inicial | `inscribir_sd(id, foto)` | `verificar_sd(id, foto)` | `identificar_sd(foto)` |
| Template | `inscribir_t(id, template)` | `verificar_t(id, template)` | `identificar_t(template)` |

### Utilización como librería

Una vez instalado el paquete:

```python
from sistema import inscribir, verificar, identificar

# Identificación
resultado = identificar("foto.jpg")

# Verificación
valido = verificar("alvaro_arbeloa_coca", "foto.jpg")
```

Los métodos de verificación devuelven `True` o `False`.

Los métodos de identificación devuelven el identificador
de la persona reconocida o `None` si no se supera el umbral.

Las fotografías pueden proporcionarse como rutas,
bytes o arrays de NumPy.

Los identificadores se obtienen del nombre del archivo
del dataset eliminando el año y la extensión.

Por ejemplo:

```text
serenna_williams_2017.jpg -> serenna_williams
```

## 8. Extractor PCA genérico

El reconocimiento utiliza un modelo PCA preentrenado
que se encuentra en:

```text
modelos/pca_base.npz
```

El modelo se entrenó utilizando 6.300 caras de FairFace
(Kärkkäinen y Joo, 2021; CC BY 4.0), con 900 muestras
de cada uno de sus siete grupos étnicos.

Referencia:

https://github.com/joojs/fairface

El sistema utiliza dos representaciones PCA:

- 50 componentes correspondientes a la cara completa.
- 50 componentes correspondientes al interior de la cara.

Por tanto, el template facial contiene 100 características.

Los coeficientes PCA se blanquean dividiendo cada componente
por su desviación típica.

Los templates se comparan mediante distancia coseno,
donde los valores menores indican mayor similitud.

### Independencia del extractor

El modelo PCA genérico es independiente de las personas inscritas.

Esto permite incorporar nuevas identidades sin tener
que volver a entrenar el extractor.

Las inscripciones se almacenan en la base de datos,
pero no modifican las eigenfaces del modelo genérico.

Es importante conservar `modelos/pca_base.npz`.
Si falta, la implementación actual de `montar.py` puede
entrenar un PCA alternativo con las fotografías inscritas,
lo que cambiaría las características del sistema.

### Regeneración del modelo PCA

No es necesario regenerar el modelo para ejecutar la práctica.

El procedimiento de entrenamiento se encuentra en:

```bash
python scripts/entrenar_pca.py
```

Requiere obtener el conjunto de entrenamiento genérico
descrito en dicho script y las dependencias adicionales
correspondientes, como `pyarrow`.

El modelo genérico está asociado a una huella de integridad
definida en `src/sistema/config.py`.

Si se genera deliberadamente un modelo diferente,
debe actualizarse esa huella.

## 9. Control de calidad

El sistema realiza comprobaciones de calidad durante
las operaciones de verificación e identificación.

Entre las condiciones que pueden provocar un rechazo están:

| Condición | Descripción |
|---|---|
| `varias_caras` | Se detectan varias caras de tamaño comparable. |
| `cara_pequena` | Distancia insuficiente entre los ojos. |
| `perfil` | La cara presenta una orientación demasiado lateral. |
| `ojos_ocultos` | Los ojos aparecen tapados u oscurecidos. |
| `boca_oculta` | La región de nariz y boca presenta características compatibles con una oclusión. |

Cuando no se encuentra una cara válida, se lanza
la excepción `CaraNoEncontrada`.

Si la fotografía no supera los controles de calidad,
puede lanzarse `CalidadInsuficiente`.

Durante la inscripción, el sistema informa de problemas
de calidad, pero permite incorporar las fotografías
proporcionadas para la práctica.

Los métodos `_sd` reciben imágenes previamente recortadas.
En la implementación actual, `verificar_sd` e
`identificar_sd` también realizan una comprobación auxiliar
con YuNet para descartar entradas que no parezcan caras.

## 10. Seguridad

El sistema incorpora mecanismos de protección frente
a determinadas manipulaciones de la base de datos,
los modelos y las entradas.

El supuesto de seguridad es que un atacante puede conocer
el código, el modelo y la base de datos, pero no dispone
de la clave criptográfica secreta.

### Protecciones implementadas

| Defensa | Objetivo |
|---|---|
| AES-256-GCM | Cifrar y autenticar los templates almacenados. |
| HMAC de `bd.csv` | Detectar modificaciones no autorizadas de la base de datos. |
| HMAC de `pca.npz` | Detectar modificaciones del modelo o su umbral. |
| Huella del modelo PCA genérico | Comprobar la identidad del extractor preentrenado. |
| Validación de templates | Rechazar vectores con dimensiones o valores inválidos. |
| Error de reconstrucción PCA | Detectar determinadas entradas alejadas del espacio de caras. |
| Validación de identificadores | Evitar caracteres peligrosos en los IDs. |
| Límite de tamaño de imágenes | Mitigar imágenes excesivamente grandes. |
| Limitación de peticiones web | Reducir consultas automatizadas a la interfaz. |

### Clave criptográfica

Durante el montaje se genera una clave secreta en:

```text
datos/clave.key
```

Este archivo no debe subirse a GitHub.

Alternativamente, es posible proporcionar la clave
mediante la variable de entorno `SISTEMA_CLAVE`.

El sistema utiliza la clave para proteger los templates
y verificar la integridad de la base de datos y del modelo.

Estas defensas dependen de que la clave permanezca protegida.

Los mecanismos implementados no garantizan la ausencia
de ataques, por lo que deben evaluarse sus limitaciones.

## 11. Tests automáticos

El repositorio incluye pruebas automáticas mediante `pytest`.

Para ejecutarlas:

```bash
python -m pytest -q
```

Los tests comprueban diferentes componentes del sistema:

- Procesamiento de imágenes.
- Detección y preprocesado facial.
- Extracción PCA.
- Comparación de templates.
- Base de datos CSV.
- Funcionamiento de la API.
- Control de calidad.
- Mecanismos de seguridad.

Los tests utilizan principalmente datos sintéticos
y no requieren el dataset del profesor.

**Importante:** superar estos tests demuestra que se cumplen
determinadas comprobaciones funcionales, pero no garantiza
una buena precisión biométrica sobre fotografías desconocidas.

## 12. Ejecución mediante Docker

Docker permite ejecutar el sistema sin instalar manualmente
Python ni sus dependencias en el equipo anfitrión.

### 12.1. Construcción de la imagen

Desde la raíz del repositorio:

```bash
docker build -t pca-biometricos .
```

La imagen incluye:

- Código fuente del sistema.
- Dependencias de Python.
- Detector facial YuNet.
- Modelo PCA genérico (`modelos/pca_base.npz`).
- Fotografías adicionales incluidas en el repositorio.

El dataset del profesor no se incorpora a la imagen.

### 12.2. Ejecución del contenedor

Coloca `Dataset.tar.gz` en la raíz del repositorio.

Desde PowerShell:

```powershell
docker run --rm -p 5000:5000 --mount "type=bind,source=${PWD}/Dataset.tar.gz,target=/app/Dataset.tar.gz,readonly" pca-biometricos
```

En Linux/macOS se puede utilizar el mismo comando desde
una terminal Bash.

El contenedor:

1. Recibe el dataset mediante un volumen de solo lectura.
2. Descomprime las fotografías.
3. Monta el sistema biométrico.
4. Inscribe las identidades.
5. Inicia la aplicación web.

Una vez iniciado, accede a:

http://localhost:5000

### 12.3. Consideraciones

- El modelo PCA genérico está incluido en la imagen.
- El dataset permanece fuera de la imagen.
- El puerto 5000 permite acceder a la aplicación desde el navegador.
- Al utilizar `--rm`, los archivos generados dentro del contenedor
  desaparecen cuando se elimina.

Para realizar experimentos y conservar modelos, bases de datos
o resultados, se recomienda utilizar la instalación local.

## 13. Estructura del repositorio

| Ruta | Descripción |
|---|---|
| `src/sistema/` | Implementación principal del sistema biométrico. |
| `src/sistema/api.py` | Los nueve métodos de inscripción, verificación e identificación. |
| `src/sistema/detector.py` | Detector facial y alineamiento. |
| `src/sistema/pca.py` | Entrenamiento, extracción y reconstrucción PCA. |
| `src/sistema/comparador.py` | Comparación de templates. |
| `src/sistema/bd.py` | Gestión de la base de datos CSV. |
| `src/sistema/seguridad.py` | Cifrado, firmas y gestión de claves. |
| `app/web.py` | Interfaz web. |
| `scripts/` | Montaje y operaciones desde terminal. |
| `modelos/face_detection_yunet_2023mar.onnx` | Detector facial YuNet. |
| `modelos/pca_base.npz` | Extractor PCA genérico preentrenado. |
| `datos/extra/` | Fotografías adicionales de inscripción. |
| `datos/ojos_manuales.json` | Coordenadas de ojos para alineamiento manual. |
| `tests/` | Pruebas automáticas. |

### Archivos generados

Al ejecutar `montar.py` se generan archivos que no se
incluyen en GitHub:

```text
datos/fotos/
datos/bd.csv
datos/bd.firma
datos/inscritos.json
datos/clave.key
modelos/pca.npz
```

Estos archivos contienen los datos de inscripción,
la información criptográfica o los resultados del montaje.

## 14. Configuración

El comportamiento del sistema puede modificarse mediante
variables de entorno.

Entre las disponibles se encuentran:

| Variable | Función |
|---|---|
| `SISTEMA_DATASET` | Ruta del dataset comprimido. |
| `SISTEMA_FOTOS` | Carpeta de fotografías de inscripción. |
| `SISTEMA_EXTRA` | Carpeta de fotografías adicionales. |
| `SISTEMA_BD` | Ruta de la base de datos CSV. |
| `SISTEMA_MODELO` | Ruta del modelo PCA utilizado. |
| `SISTEMA_UMBRAL` | Sobrescribe el umbral de reconocimiento. |
| `SISTEMA_CLAVE` | Clave criptográfica proporcionada por variable de entorno. |
| `SISTEMA_CLAVE_FICHERO` | Ruta del archivo de clave. |
| `MAX_ANALISIS` | Límite de análisis por minuto en la interfaz web. |

La configuración predeterminada está definida en:

```text
src/sistema/config.py
```
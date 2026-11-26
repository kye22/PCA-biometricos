# Reconocimiento facial con PCA — Sistemas Biométricos

Sistema de reconocimiento facial basado en **Principal Component Analysis (PCA / eigenfaces)**, desarrollado en Python para la asignatura de Sistemas Biométricos.

Permite inscribir, verificar e identificar personas a partir de fotografías faciales. Incorpora detección facial, control de calidad, extracción de características, comparación biométrica y almacenamiento de templates cifrados.

El proyecto trabaja con **50 identidades**: las 49 presentes en el dataset proporcionado por el profesor y Álvaro Arbeloa, incorporado por nuestro grupo.

El enunciado original puede consultarse en [`Prácticas.md`](Prácticas.md).

El informe completo de evaluación está disponible en [`informe/INFORME.md`](informe/INFORME.md).

## 1. Características principales

El proyecto implementa:

- Detección de rostros mediante YuNet y cascadas Haar.
- Alineamiento facial utilizando las posiciones de los ojos.
- Normalización de las imágenes.
- Extracción de características mediante PCA.
- Templates que combinan la cara completa y una región facial interior.
- Comparación mediante distancia coseno.
- Inscripción de múltiples templates por identidad.
- Verificación biométrica 1:1.
- Identificación biométrica 1:N.
- Control de calidad de fotografías.
- Cifrado y protección de integridad de la base de datos.
- Interfaz web.
- Ejecución mediante Docker.
- Tests automatizados.
- Herramientas de evaluación biométrica.
- Generación de gráficas.
- Demostraciones controladas de ataques.

La implementación está organizada en módulos independientes dentro de `src/sistema/`.

## 2. Arquitectura

La cadena de procesamiento de una fotografía es:

1. **Detección:** localizar el rostro en la imagen.
2. **Alineamiento:** corregir su orientación utilizando referencias faciales.
3. **Normalización:** preparar la imagen para el extractor.
4. **Extracción PCA:** obtener el template biométrico.
5. **Comparación:** calcular las distancias frente a templates inscritos.
6. **Decisión:** aceptar, rechazar o identificar según el umbral.

La base de datos utiliza un archivo CSV con los identificadores y templates biométricos cifrados.

### Operaciones principales

El sistema permite:

- **Inscribir:** registrar una identidad utilizando una fotografía o un template.
- **Verificar:** comprobar si una fotografía corresponde a la identidad declarada.
- **Identificar:** buscar la identidad más cercana dentro de la base de datos.

## 3. Requisitos

Para ejecutar el proyecto se necesita:

- Python 3.10 o superior. Se recomienda Python 3.11.
- OpenCV 4.x.
- Las dependencias definidas en `pyproject.toml`.
- `Dataset.tar.gz` para realizar la inscripción inicial.
- Opcionalmente, Docker para ejecutar el sistema en un contenedor.

Las dependencias están bloqueadas mediante `uv.lock`.

**Importante:** se utiliza OpenCV 4.x para evitar incompatibilidades con las funciones de detección empleadas por el proyecto.

También se ha corregido la carga de los clasificadores Haar para permitir su funcionamiento en rutas de Windows con caracteres Unicode.

## 4. Instalación local

### 4.1. Instalación recomendada con uv

Abre una terminal PowerShell en la raíz del repositorio.

Si no tienes `uv`, instálalo primero (si no, el siguiente paso falla con `No module named uv`):

```powershell
py -m pip install uv
```

Ejecuta:

```powershell
py -m uv sync --locked --extra dev --extra eval
```

Esto prepara el entorno virtual `.venv` e instala las dependencias necesarias para ejecutar el sistema, los tests y las herramientas de evaluación.

Para comprobar la instalación:

```powershell
py -m uv run --locked --extra dev --extra eval python -m pytest -q
```

### 4.2. Instalación alternativa con pip

En Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e ".[eval]"
```

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e ".[eval]"
```

La dependencia adicional `eval` incluye Matplotlib para generar gráficas.

## 5. Preparación del dataset

El archivo `Dataset.tar.gz`, proporcionado por el profesor, no está incluido en GitHub.

Debe colocarse en la raíz del repositorio:

```text
PCA-biometricos/
├── Dataset.tar.gz
├── README.md
├── pyproject.toml
├── uv.lock
├── app/
├── ataques/
├── datos/
├── evaluacion/
├── informe/
├── modelos/
├── scripts/
├── src/
└── tests/
```

El sistema puede extraer automáticamente las fotografías del archivo comprimido cuando sea necesario.

### 5.1. Distribución de fotografías

Para evaluar el reconocimiento utilizando imágenes independientes se ha implementado un sistema de particiones.

Se distinguen cuatro grupos:

| Grupo | Finalidad |
|---|---|
| `inscripcion` | Construir la base de datos biométrica. |
| `calibracion` | Seleccionar y analizar el umbral. |
| `prueba` | Evaluar el rendimiento final. |
| `desconocidos` | Evaluar personas no inscritas, cuando existan fotografías disponibles. |

Las fotografías originales del profesor se reservan para inscripción.

Las fotografías adicionales disponibles se utilizan para calibración o prueba.

### 5.2. Generar las particiones

Con `uv`:

```powershell
py -m uv run --locked --extra dev python evaluacion/particiones.py --semilla 42
```

Con Python y las dependencias instaladas:

```powershell
python evaluacion/particiones.py --semilla 42
```

Esto genera:

```text
evaluacion/particion.json
```

El script comprueba que no se reutilice una misma fotografía entre grupos y utiliza SHA-256 para detectar duplicados exactos de contenido.

La semilla permite reproducir la distribución.

## 6. Montaje del sistema

### 6.1. Montaje recomendado para evaluación

Para inscribir exclusivamente las fotografías del manifiesto:

```powershell
py -m uv run --locked --extra dev python scripts/montar.py --manifiesto evaluacion/particion.json
```

El programa:

1. Comprueba el extractor PCA genérico.
2. Selecciona las fotografías de inscripción.
3. Detecta y alinea los rostros.
4. Valida que se dispone de suficientes identidades.
5. Crea o reutiliza la clave secreta.
6. Genera la base de datos biométrica.
7. Calcula un umbral provisional.
8. Guarda el modelo operativo firmado.

**Las fotografías reservadas para calibración y prueba no participan en la inscripción.**

### 6.2. Montaje sin manifiesto

También se admite:

```powershell
python scripts/montar.py
```

Esta modalidad conserva el comportamiento original del repositorio, incluyendo las fotografías adicionales de `datos/extra/`.

No se recomienda para realizar una evaluación independiente con esas mismas fotografías adicionales.

### 6.3. Protección contra reconstrucciones accidentales

Si ya existen una base de datos o un modelo operativo, el montaje se cancela.

Para reconstruir deliberadamente el sistema:

```powershell
python scripts/montar.py --manifiesto evaluacion/particion.json --recrear
```

**Advertencia:** `--recrear` sustituye la base de datos y el modelo operativo existentes.

Debe utilizarse únicamente cuando se quiera reconstruir el sistema de forma consciente y se hayan preservado los datos necesarios.

La clave secreta existente se conserva.

### 6.4. Validación previa

Antes de reconstruir la base de datos se comprueban:

- Los argumentos introducidos.
- La existencia del PCA genérico.
- La disponibilidad de suficientes identidades.
- La detección y alineamiento iniciales de las fotografías.

Si alguna fotografía falla durante la fase inicial de detección, el montaje se cancela antes de sustituir la base de datos.

Esta protección no convierte todo el procedimiento en una transacción completamente atómica: un fallo inesperado posterior todavía podría provocar escrituras parciales.

## 7. Extractor PCA

El extractor utilizado se encuentra en:

```text
modelos/pca_base.npz
```

Se entrenó previamente utilizando fotografías de FairFace, independientemente de las identidades que deben inscribirse en el sistema.

La representación biométrica contiene:

- 50 componentes PCA correspondientes a la cara completa.
- 50 componentes PCA correspondientes a una región facial interior.

Cada template contiene, por tanto, **100 características**.

Los coeficientes se blanquean y se comparan mediante distancia coseno.

El modelo explica aproximadamente el 81 % de la varianza de su conjunto de entrenamiento.

Este porcentaje no equivale a una tasa de reconocimiento: PCA busca representar variaciones de las imágenes, no necesariamente maximizar la separación entre identidades.

### Extractor obligatorio

El montaje exige que exista `modelos/pca_base.npz`.

Si falta, el proceso se cancela.

Además, se comprueba su huella para evitar sustituirlo accidentalmente por un modelo diferente.

La inscripción no vuelve a entrenar el PCA.

## 8. Interfaz web

Una vez montado el sistema:

```powershell
py -m uv run --locked --extra dev python app/web.py
```

La aplicación estará disponible en:

http://localhost:5000

La interfaz permite:

- Subir fotografías.
- Visualizar la detección facial.
- Consultar el resultado del procesamiento.
- Realizar verificaciones.
- Realizar identificaciones.
- Mostrar las identidades más parecidas y sus distancias.

## 9. Interfaz de línea de comandos

### Identificación

```powershell
python scripts/identificar.py foto.jpg
```

### Verificación

```powershell
python scripts/verificar.py identificador foto.jpg
```

Ambos scripts admiten `--sd`, destinado a utilizar imágenes faciales ya recortadas.

## 10. API del sistema

El sistema implementa las nueve operaciones solicitadas en el enunciado.

| Tipo de entrada | Inscripción | Verificación | Identificación |
|---|---|---|---|
| Fotografía | `inscribir(id, foto)` | `verificar(id, foto)` | `identificar(foto)` |
| Sin detector inicial | `inscribir_sd(id, foto)` | `verificar_sd(id, foto)` | `identificar_sd(foto)` |
| Template | `inscribir_t(id, template)` | `verificar_t(id, template)` | `identificar_t(template)` |

Ejemplo:

```python
import sys
sys.path.insert(0, "src")

from sistema import identificar, verificar

identidad = identificar("foto.jpg")
resultado = verificar("adele", "foto.jpg")
```

La modalidad `_t` trabaja directamente con templates.

**Inscripción de un id ya inscrito.** `inscribir*` sobre un id que ya está en la BD lanza
`IdYaInscrito`: nadie puede añadir su cara a la identidad de otro. Para añadir otra muestra a un
id existente se usa `actualizar=True` (`inscribir(id, foto, actualizar=True)`), y solo se acepta si
la nueva muestra **ya verifica** contra ese id; si no, `InscripcionRechazada`. La carga inicial con
varias fotos por persona la hace `scripts/montar.py` como administrador.

Las modalidades `_sd` omiten la detección y alineamiento iniciales, aunque determinadas operaciones mantienen comprobaciones adicionales mediante YuNet.

## 11. Control de calidad

El sistema incorpora comprobaciones heurísticas sobre las fotografías.

Entre las condiciones contempladas se encuentran:

| Condición | Descripción |
|---|---|
| Varias caras | Hay más de un rostro relevante. |
| Cara pequeña | El rostro tiene una resolución insuficiente. |
| Perfil | La orientación facial se aleja de una posición frontal. |
| Ojos ocultos | Existen indicios de oclusión en los ojos. |
| Boca oculta | Existen indicios de oclusión en la parte inferior del rostro. |

Si no se detecta ninguna cara puede producirse `CaraNoEncontrada`.

Si la fotografía no satisface los criterios de calidad puede producirse `CalidadInsuficiente`.

Estos controles también pueden rechazar fotografías legítimas y deben analizarse como parte del rendimiento global del sistema.

## 12. Seguridad

El sistema incorpora diferentes mecanismos de protección:

| Mecanismo | Objetivo |
|---|---|
| Cifrado AES-256-GCM | Proteger los templates almacenados. |
| Firma HMAC de la BD | Detectar modificaciones no autorizadas del CSV. |
| Firma HMAC del modelo | Detectar cambios en el modelo operativo y su umbral. El umbral solo sale del modelo firmado: no hay variable de entorno que lo cambie. |
| Ids no reutilizables | `inscribir*` no acepta un id ya inscrito salvo con `actualizar=True` y una muestra que verifique contra él. |
| Huella fija del PCA genérico | Comprobar la identidad del extractor. |
| Validación de templates | Rechazar determinadas representaciones anómalas. |
| Validación de identificadores | Limitar los valores admitidos como identificadores. |
| Límites de procesamiento | Reducir riesgos asociados a entradas excesivamente grandes. |
| Limitación de peticiones web | Dificultar determinados ataques repetitivos. |

La clave secreta se almacena por defecto en:

```text
datos/clave.key
```

Este archivo no debe publicarse.

También es posible configurar la clave mediante variables de entorno.

### 12.1. Pruebas de ataques realizadas

Se han ejecutado demostraciones controladas de los escenarios principales solicitados en el enunciado.

Los scripts se encuentran en `ataques/`.

| Ataque | Script | Resultado observado |
|---|---|---|
| Lectura de la BD | `lectura_bd.py` | Templates cifrados; identificadores visibles. |
| Modificación del CSV | `escritura_bd.py --modo alterar` | HMAC detecta la alteración. |
| Eliminación de CSV y firma | `escritura_bd.py --modo borrar-todo` | Se interpreta como una BD vacía. |
| Bypass de componentes | `bypass.py` | Las interfaces alternativas pueden omitir controles de calidad. |

Las pruebas de modificación utilizan copias temporales y no alteran intencionadamente la base de datos original.

### 12.2. Lectura de la BD

Para inspeccionar pasivamente el CSV:

```powershell
python ataques/lectura_bd.py
```

En nuestra ejecución se observaron:

- 50 filas con templates.
- 50 identificadores en claro.
- Campos cifrados de 572 caracteres Base64.
- 428 bytes decodificados por template.

El resultado es coherente con templates de 100 características `float32` protegidos mediante AES-GCM.

El cifrado protege los coeficientes biométricos frente al escenario de lectura sin clave, pero no oculta los identificadores.

### 12.3. Modificación de la BD

Para modificar una copia temporal:

```powershell
python ataques/escritura_bd.py --modo alterar
```

Resultado observado:

```text
Ataque detectado: la copia no supera la firma HMAC
```

La protección de integridad detectó la modificación ensayada.

### 12.4. Borrado completo

Para probar el borrado de una copia temporal de la BD y su firma:

```powershell
python ataques/escritura_bd.py --modo borrar-todo
```

Resultado observado:

```text
LIMITACIÓN DETECTADA: eliminar BD y firma produce una BD vacía, sin alarma de manipulación
```

Esta situación representa una limitación de disponibilidad y de detección de ciertos escenarios de manipulación.

No significa que el sistema acepte automáticamente a un atacante.

### 12.5. Bypass de detector y extractor

Para comparar las tres interfaces:

```powershell
python ataques/bypass.py ID FOTO
```

Se obtuvieron los siguientes resultados:

| Fotografía | `verificar()` | `verificar_sd()` | `verificar_t()` |
|---|---|---|---|
| Brays Efe | `True` | `True` | `True` |
| Adele | `False` | `False` | `False` |
| Stevie Wonder | `CalidadInsuficiente` | `NoPareceCara` | `True` |
| Ellen Page | `CalidadInsuficiente` | `True` | `True` |

Estas pruebas muestran que las interfaces que omiten etapas del procesamiento pueden evitar determinados controles de calidad.

En particular, `verificar_t()` recibe directamente un template y no comprueba la fotografía original.

**Las pruebas no demuestran una suplantación exitosa:** los templates utilizados procedían de fotografías genuinas de personas inscritas.

### 12.6. Limitaciones del modelo de amenaza

Las defensas deben interpretarse teniendo en cuenta que:

- La seguridad del cifrado y las firmas depende de la protección de la clave.
- Los identificadores de la BD se almacenan en claro.
- El borrado simultáneo del CSV y su firma no se detecta como manipulación.
- Las interfaces `_sd` y `_t` tienen superficies de ataque distintas.
- Es necesario controlar quién puede acceder a los métodos de inscripción y a las interfaces que reciben templates directamente: cualquiera puede inscribir ids **nuevos** (no los existentes).
- `actualizar=True` permite que un impostor que consiga verificar una vez añada su muestra a ese id.
- El límite de intentos solo existe en la interfaz web; la librería no limita consultas.
- La validación de `_t` comprueba la longitud, que los valores sean finitos y que la norma sea la de una cara real; no garantiza que el vector proceda de una foto.

Las pruebas realizadas son demostraciones controladas, no una auditoría exhaustiva de seguridad.

El análisis completo está documentado en [`informe/INFORME.md`](informe/INFORME.md).

## 13. Evaluación biométrica

El repositorio incorpora herramientas para evaluar el sistema utilizando fotografías diferentes de las inscritas.

### 13.1. Métricas

Se calculan:

- **FAR/FMR:** proporción de intentos impostores aceptados en verificación 1:1.
- **FRR/FNMR:** proporción de intentos genuinos rechazados.
- **EER aproximada:** medida descriptiva del cruce entre FAR y FRR.
- **Rank-1:** proporción de identificaciones cuya primera candidata es la identidad correcta.
- **CMC:** porcentaje de identificaciones correctas considerando los primeros k candidatos.
- **Identificación correcta con umbral:** proporción de genuinos correctamente identificados y aceptados.

Si existen fotografías de desconocidos, también es posible estimar FPIR.

Los intentos fallidos durante detección o control de calidad se tienen en cuenta en las métricas; no se eliminan silenciosamente.

### 13.2. Calibración

La calibración utiliza exclusivamente las fotografías del grupo `calibracion`.

Para obtener un umbral propuesto con FAR objetivo del 2 %:

```powershell
py -m uv run --locked --extra dev python evaluacion/calibrar_umbral.py --far 0.02
```

El comando anterior es de solo lectura respecto al modelo.

La opción `--aplicar` permite guardar y firmar el umbral propuesto, por lo que modifica el modelo operativo.

No debe utilizarse sin revisar previamente sus consecuencias.

### 13.3. Decisión tomada en nuestra evaluación

Durante el montaje se obtuvo un umbral provisional aproximado de `0,6065`.

La calibración propuso `0,65447`, pero no mejoró la FRR observada:

| Umbral | FAR de calibración | FRR de calibración |
|---|---:|---:|
| 0,6065 | 1,06 % | 91,30 % |
| 0,65447 | 1,95 % | 91,30 % |

Por tanto, se decidió conservar `0,6065` para la evaluación final.

La decisión se tomó antes de utilizar el conjunto de prueba.

### 13.4. Ejecutar la evaluación final

```powershell
py -m uv run --locked --extra dev python evaluacion/evaluar.py --grupo prueba
```

El resultado se guarda en:

```text
evaluacion/resultados/prueba.json
```

**No debe utilizarse el conjunto de prueba final para reajustar posteriormente el umbral y presentar el resultado como una evaluación independiente.**

## 14. Resultados observados

El informe completo está disponible en:

[`informe/INFORME.md`](informe/INFORME.md)

La evaluación inicial se realizó utilizando el código correspondiente al commit `a58e10e`.

Se utilizaron:

| Grupo | Fotografías |
|---|---:|
| Inscripción | 50 |
| Calibración | 23 |
| Prueba | 32 |
| Desconocidos | 0 |

### Resultados de calibración

| Métrica | Resultado |
|---|---:|
| FAR | 1,06 % |
| FRR | 91,30 % |
| Rank-1 | 8,70 % |
| Rank-5 | 26,09 % |
| EER aproximada | 34,78 % |

### Resultados de prueba final

| Métrica | Resultado |
|---|---:|
| FAR | **0,96 %** |
| FRR | **87,50 %** |
| Rank-1 | **15,62 %** |
| EER aproximada | **40,15 %** |
| Identificación correcta con umbral | **12,50 %** |

Estos resultados corresponden al sistema evaluado con umbral aproximado de `0,6065`.

La prueba final contiene 32 fotografías genuinas y 1568 comparaciones impostoras de verificación 1:1.

Las comparaciones impostoras realizadas sobre una misma fotografía no constituyen muestras estadísticamente independientes.

### Interpretación

El sistema presenta una tasa de falsa aceptación relativamente baja para el umbral utilizado.

Sin embargo, la tasa de falso rechazo es muy elevada.

Además, el Rank-1 reducido indica que el sistema tiene dificultades para situar a la identidad correcta como primera candidata.

Por tanto, el problema no depende únicamente de la selección del umbral.

**La versión evaluada no ofrece un rendimiento suficiente para aplicaciones reales que requieran reconocimiento facial fiable.**

El objetivo de la práctica es identificar y analizar estas limitaciones, no ocultarlas.

### Limitación sobre desconocidos

No se dispone actualmente de fotografías de identidades no inscritas.

Por ello, FPIR no es estimable con el conjunto utilizado.

Esto no significa que su valor sea cero.

## 15. Generación de gráficas

Las gráficas pueden regenerarse a partir de los resultados JSON.

Instalación de dependencias:

```powershell
py -m uv sync --locked --extra dev --extra eval
```

Generación:

```powershell
py -m uv run --locked --extra dev --extra eval python evaluacion/graficas.py --resultados evaluacion/resultados/prueba.json
```

Se generan cuatro figuras:

- Histograma de distancias genuinas e impostoras.
- Curva ROC.
- Curva DET.
- Curva CMC.

Las gráficas utilizadas en el informe están incluidas en:

```text
informe/figuras/
```

Los archivos temporales y los resultados de experimentación permanecen en `evaluacion/resultados/`.

## 16. Tests automatizados

Para ejecutar todas las pruebas:

```powershell
py -m uv run --locked --extra dev python -m pytest -q
```

Con la instalación de pip vale también `python -m pytest -q` o `pytest -q`.

Las pruebas utilizan datos preparados para testing y no requieren el dataset original del profesor.

El proyecto incluye tests sobre:

- API biométrica.
- Detección.
- Preprocesamiento.
- Extracción de características.
- Comparación.
- Base de datos.
- Seguridad.
- Control de calidad.
- Particiones de evaluación.
- Métricas.
- Validación de la inscripción utilizada para evaluar.

Existe un workflow de GitHub Actions:

```text
.github/workflows/tests.yml
```

Este permite ejecutar las pruebas automáticamente en GitHub.

## 17. Ejecución con Docker

Docker permite entregar el sistema a otros grupos sin necesidad de instalar manualmente todas las dependencias de Python.

El dataset del profesor debe estar disponible en la raíz del repositorio.

### 17.1. Construir la imagen

```powershell
docker build -t pca-biometricos .
```

### 17.2. Ejecutar el contenedor

En PowerShell:

```powershell
docker run --rm -p 5000:5000 --mount "type=bind,source=${PWD}/Dataset.tar.gz,target=/app/Dataset.tar.gz,readonly" pca-biometricos
```

Si el puerto `5000` del ordenador ya está ocupado, puede utilizarse otro puerto externo:

```powershell
docker run --rm -p 5001:5000 --mount "type=bind,source=${PWD}/Dataset.tar.gz,target=/app/Dataset.tar.gz,readonly" pca-biometricos
```

En ese caso, la interfaz estará disponible en:

http://localhost:5001

### 17.3. Preparación automática

Al arrancar el contenedor se ejecutan automáticamente:

1. La generación de las particiones con semilla `42`.
2. El montaje utilizando exclusivamente las fotos de `inscripcion`.
3. La aplicación web.

El contenedor utiliza el PCA genérico del repositorio y genera un umbral provisional.

La calibración independiente no se ejecuta automáticamente durante este arranque.

### 17.4. Persistencia

El dataset del profesor se monta en modo solo lectura.

La base de datos, el modelo operativo y la clave se generan dentro del contenedor.

Como se utiliza `--rm`, esos archivos se pierden cuando se elimina el contenedor.

Para conservarlos entre ejecuciones sería necesario configurar volúmenes persistentes.

## 18. Estructura del proyecto

| Ruta | Contenido |
|---|---|
| `src/sistema/` | Implementación de la librería biométrica. |
| `app/web.py` | Interfaz web. |
| `scripts/montar.py` | Montaje e inscripción. |
| `scripts/identificar.py` | Identificación por línea de comandos. |
| `scripts/verificar.py` | Verificación por línea de comandos. |
| `scripts/entrenar_pca.py` | Entrenamiento del extractor genérico. |
| `evaluacion/particiones.py` | Generación de particiones. |
| `evaluacion/metricas.py` | Cálculo de métricas biométricas. |
| `evaluacion/evaluar.py` | Evaluación mediante fotografías reservadas. |
| `evaluacion/calibrar_umbral.py` | Calibración del umbral. |
| `evaluacion/graficas.py` | Generación de gráficas. |
| `ataques/lectura_bd.py` | Demostración de lectura del CSV. |
| `ataques/escritura_bd.py` | Pruebas de modificación y borrado sobre copias. |
| `ataques/bypass.py` | Comparación de interfaces de verificación. |
| `ataques/README.md` | Descripción de escenarios y limitaciones de los ataques. |
| `informe/INFORME.md` | Informe de evaluación propia. |
| `informe/figuras/` | Gráficas de la evaluación inicial. |
| `modelos/pca_base.npz` | Extractor PCA genérico. |
| `modelos/face_detection_yunet_2023mar.onnx` | Detector YuNet. |
| `tests/` | Pruebas automatizadas. |
| `Dockerfile` | Configuración de Docker. |
| `pyproject.toml` | Dependencias y configuración del proyecto. |
| `uv.lock` | Versiones bloqueadas de las dependencias. |
| `Prácticas.md` | Enunciado original. |

Durante el montaje se generan archivos que no deben publicarse:

- `datos/fotos/`
- `datos/bd.csv`
- `datos/bd.firma`
- `datos/clave.key`
- `datos/inscritos.json`
- `modelos/pca.npz`
- `evaluacion/particion.json`
- `evaluacion/resultados/`

También se ignoran los entornos virtuales y archivos temporales de Python.

## 19. Estado del proyecto y trabajo futuro

El sistema dispone de:

- Una implementación funcional de las operaciones biométricas solicitadas.
- Una evaluación cuantitativa con separación entre inscripción y prueba.
- Métricas FAR, FRR, EER, Rank-1 y CMC.
- Gráficas reproducibles.
- Un informe de evaluación propia.
- Demostraciones controladas de lectura, modificación y bypass de componentes.

Se han observado limitaciones importantes en la capacidad de identificación y verificación con fotografías independientes.

Las pruebas de seguridad han permitido comprobar algunas defensas implementadas y detectar debilidades concretas, como el borrado simultáneo de la BD y su firma o la posibilidad de omitir controles de calidad mediante interfaces alternativas.

Estas pruebas no constituyen una auditoría de seguridad completa.

Como trabajo futuro se propone:

- Investigar otras estrategias de comparación.
- Evaluar diferentes números de componentes PCA.
- Analizar la influencia del alineamiento.
- Estudiar el uso de múltiples templates por identidad.
- Ampliar las fotografías de evaluación.
- Incorporar identidades desconocidas.
- Analizar posibles diferencias de rendimiento entre grupos demográficos.
- Ampliar las pruebas de seguridad.
- Contrastar el sistema con fotografías externas del grupo rival.

Las mejoras futuras deberán distinguirse de la versión inicial evaluada y utilizar datos independientes para validar su rendimiento.

El objetivo de este proyecto es desarrollar, comprender y evaluar críticamente un sistema biométrico facial, identificando tanto sus fortalezas como sus debilidades.
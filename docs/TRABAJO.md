# Cómo trabajamos — reparto de tareas y flujo en GitHub

> Léelo antes de tu primer commit. Si algo cambia, se cambia aquí (por PR, como todo).
> Las decisiones técnicas y su porqué van en [`decisiones.md`](decisiones.md).

## 1. Qué construimos

Sistema de reconocimiento facial con **PCA (eigenfaces)** en Python, usado como **librería**
(los 9 métodos del enunciado), con BD en **un `.csv`**, 51 inscritos (50 del profe + Álvaro Arbeloa)
y un **Dockerfile** para que el rival lo ejecute sin pelearse con el entorno.

El código será **abierto para el rival**: ninguna defensa puede depender de que no vea el código.
Secretos (claves, sal, etc.) nunca en el repo → variables de entorno / `.env` (ignorado por git).

## 2. Estructura del repo

```
src/sistema/          # la librería (lo que usa el rival)
  config.py           # rutas, TAM_CARA, nº componentes, umbral (sobrescribibles por env)
  imagen.py           # leer foto (ruta o array)
  detector.py         # [1] foto -> recorte de la cara
  preprocesado.py     # [1] recorte -> cara normalizada (gris, 100x100, [0,1])
  pca.py              # [2] ModeloPCA: entrenar / extraer / guardar / cargar
  comparador.py       # [3] distancia entre templates + umbral
  bd.py               # [3] leer/escribir el .csv
  api.py              # [3] los 9 métodos
  dataset.py          # recorrer datos/fotos/<id>/*.jpg
  excepciones.py
scripts/              # uso diario: entrenar_pca, inscribir_todos, verificar, identificar
evaluacion/           # [4] metricas.py + evaluar.py (+ notebooks de gráficas)
ataques/              # [5] red team: un script por ataque + README con la tabla
tests/                # pytest, con caras sintéticas (no necesitan fotos)
modelos/  datos/      # pca.npz, bd.csv y fotos (fotos fuera de git)
Dockerfile  .github/workflows/tests.yml
```

Regla de oro: **la lógica del sistema vive en `src/`**. Los notebooks solo exploran y pintan
gráficas; si algo de un notebook sirve, se pasa a `src/` o `evaluacion/`.

## 3. Reparto (mixto)

Cada módulo tiene un **responsable**: decide su diseño interno, revisa los PR que lo tocan y
responde de que funcione. Pero las tareas son **issues** y cualquiera puede coger cualquiera.

| # | Módulo | Responsable | Qué incluye |
|---|--------|-------------|-------------|
| 1 | Detector y preprocesado | _por asignar_ | detección (Haar/DNN de OpenCV), alineado por ojos, recorte, escala de grises, tamaño fijo, ecualización |
| 2 | PCA | _por asignar_ | entrenar con dataset, nº de componentes (varianza explicada), guardar/cargar modelo, `extraer(cara) -> template` |
| 3 | BD, comparador y API | _por asignar_ | formato del `.csv`, distancia (euclídea/coseno/Mahalanobis), umbral, los 9 métodos |
| 4 | Evaluación | _por asignar_ | protocolo train/test, FAR/FRR, EER, curvas ROC/DET, identificación rank-1/CMC, elección de umbral |
| 5 | Seguridad, red team y Docker | _por asignar_ | ataques (bypass `_sd`/`_t`, lectura y escritura del CSV), defensas, Dockerfile, CI |

Rellenad los nombres en el primer PR.

### Interfaces (ya fijadas en el esqueleto)

Todo funciona ya de punta a punta con versiones provisionales; cada uno mejora lo suyo sin
romper la firma:

```python
detector.detectar(foto) -> recorte              # lanza CaraNoEncontrada
preprocesado.normalizar(recorte) -> cara        # float32 (100, 100) en [0, 1]
ModeloPCA.extraer(cara) -> template             # float32 (K,)
comparador.distancia(t1, t2) -> float           # menor = más parecido
bd.guardar(id, template) / bd.cargar() -> {id: [templates]}
```

Cambiar una interfaz = issue + aviso al grupo + PR que actualice a todos los que la usan.

## 4. Fases

1. **Esqueleto** (todos): interfaces + versiones provisionales + tests mínimos + CI en verde.
2. **Construcción**: cada responsable mejora su módulo; dataset provisional (LFW + Arbeloa)
   hasta que el profe pase las fotos.
3. **Evaluación propia**: métricas sobre nuestro sistema con el dataset real.
4. **Red team interno** (todos): atacamos nuestro propio sistema como si fuéramos el rival.
   Cada hallazgo → issue con etiqueta `red-team` → se arregla o se documenta como
   **limitación conocida** en el informe. Objetivo: que el rival no encuentre nada que no
   tengamos ya escrito.
5. **Evaluación del rival** (todos): mismos ataques + los que se nos ocurran, sobre su repo.
6. **Exposición**.

## 5. Flujo de Git

### Ramas

- `main`: siempre funciona. **Por acuerdo** (no está bloqueada en GitHub): nadie hace push
  directo, todo entra por PR.
- Una rama por tarea/issue, corta (horas o pocos días, no semanas), desde `main` actualizado:

```
<tipo>/<issue>-<descripcion-corta>
feat/12-detector-haar
fix/20-umbral-verificar
eval/31-curva-det
attack/40-escritura-csv
docs/8-reparto
```

Tipos: `feat`, `fix`, `eval`, `attack`, `docs`, `chore` (config, Docker, CI).

### Día a día

```bash
git switch main && git pull                 # partir de lo último
git switch -c feat/12-detector-haar         # rama nueva
# ... trabajar, commits pequeños ...
git add -p && git commit -m "detector: añade detección Haar con fallback"
git push -u origin feat/12-detector-haar    # y abrir PR en GitHub
```

Si `main` avanza mientras trabajas: `git pull origin main` en tu rama (merge) y resuelve conflictos.

### Commits

Mensaje en español, imperativo, prefijado por módulo: `pca: guarda la media junto a las eigenfaces`.
Commits pequeños y con sentido; nada de "cambios" o "arreglos varios".

### Pull requests

- Título claro y `Closes #<issue>` en la descripción (cierra el issue al fusionar).
- **1 aprobación** mínima; si toca un módulo ajeno, debe aprobar su responsable.
- CI en verde (tests) antes de fusionar.
- Se fusiona con **Squash and merge** (elegirlo en el desplegable del botón) y se borra la rama.
- Quien abre el PR es quien lo fusiona tras la aprobación.

### Issues y tablero

- Todo trabajo empieza con un issue (aunque sea de una línea). Asígnatelo al cogerlo.
- Etiquetas: `detector`, `pca`, `bd-api`, `evaluacion`, `red-team`, `docker`, `docs`, `bug`.
- Tablero en GitHub Projects: *Por hacer → En curso → En revisión → Hecho*.

### Qué NO se sube

- Fotos y datasets (`datos/fotos/`, LFW…): pesan y tienen derechos. Se comparten por el
  canal del grupo / Drive y cada uno las coloca en `datos/` en local.
- `.env`, claves, credenciales.
- Salidas pesadas de notebooks (limpiar outputs antes de commitear).

La `bd.csv` final y el modelo PCA entrenado **sí** se suben al final (el rival los necesita);
mientras desarrollamos, cada uno genera los suyos.

## 6. Puesta en marcha (cada compañero)

1. Aceptar la invitación al repo y clonarlo: `git clone <url>`.
2. Crear entorno: `python -m venv .venv`, activarlo y `pip install -r requirements.txt`.
   Comprobar con `pytest`.
3. Pedir las fotos al grupo y dejarlas en `datos/fotos/`.
4. Coger un issue, crear rama, y a trabajar.

## 7. Configuración del repo

No hay reglas técnicas en GitHub: todo lo anterior funciona **por acuerdo**. Lo único a montar
(opcional) son las etiquetas de la sección 5 y el tablero en *Projects*.

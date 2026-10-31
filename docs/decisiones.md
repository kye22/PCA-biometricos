# Práctica Sistemas Biométricos — Decisiones y planteamiento

> Documento vivo. Registra qué pide la práctica, qué hemos decidido y por qué.
> Fuente: `Prácticas.md` (convertido de `Prácticas.pdf` con markitdown) y `Reconocimiento facial.webp`.

## 1. Qué pide el enunciado (resumen)

Sistema de **reconocimiento facial** en Python, por grupos, cada grupo con una aproximación distinta.

Fases:
1. Crear el sistema.
2. Evaluar nuestro sistema.
3. Evaluar el sistema de un grupo "rival".
4. Exponer resultados/conclusiones.

Restricciones duras:
- Python.
- Repositorio fácil de ejecutar, idealmente con **Docker** listo.
- Base de datos = **un .csv**.
- **51 personas inscritas**: 50 famosos comunes (los da el docente, aún no disponibles) + 1 elegido por el grupo → **Álvaro Arbeloa Coca**.
- API obligatoria (9 métodos, 3 niveles × 3 operaciones):

| Entrada            | Inscribir              | Verificar              | Identificar            |
|--------------------|------------------------|------------------------|------------------------|
| foto (pipeline completo) | `inscribir(id, foto)`    | `verificar(id, foto)`    | `identificar(foto)`    |
| foto sin detector (`_sd`) | `inscribir_sd(id, foto)` | `verificar_sd(id, foto)` | `identificar_sd(foto)` |
| template (`_t`)    | `inscribir_t(id, template)` | `verificar_t(id, template)` | `identificar_t(template)` |

  Nota: el PDF dice "foto" en la descripción de `verificar_t`/`identificar_t`, pero por el nombre y
  por coherencia la entrada es un **template** (errata del enunciado).

- Evaluación (propia y del rival) debe incluir **escenarios de ataque**:
  - atacante que se salta partes del sistema (p. ej. inyecta directamente en `_sd` o `_t`),
  - atacante que **lee** la BD (.csv) → privacidad de templates, inversión, etc.,
  - atacante que **escribe** en la BD → suplantación, envenenamiento.
- Objetivo real: que el rival **no encuentre defectos que no conozcamos**. → documentar limitaciones
  propias explícitamente.

## 2. Arquitectura de referencia (imagen)

Cámara → [Detector de caras → Extractor de características faciales] → Comparador ← BD

Aproximaciones posibles (repartidas entre grupos):
- Apariencia general: ICA/PCA, LDA
- Modelado del rostro: Elastic Bunch Graph Matching, Active Appearance Model
- Textura: SIFT, Multiscale LBP, PCA con orientación de gradiente
- Deep Learning: cualquier modelo DL entrenado para reconocimiento facial

Niveles de detalle según distancia interpupilar (IDP): <30 px geometría general, 30–75 px estructura, >75 px micro-detalle.

## 3. Decisiones tomadas

- **2026-09-30 — Diseño agnóstico al approach (propuesto).** Aún no sabemos qué aproximación nos
  toca. El extractor de características será un componente enchufable (interfaz `Extractor.extraer(cara) -> template`);
  todo lo demás (API de 9 métodos, BD .csv, detector, comparador, evaluación, ataques, Docker) es común.
  Mientras tanto se usa un extractor provisional (PCA/eigenfaces) y un dataset público (LFW) + fotos de Arbeloa.
- **2026-09-30 — Formato (propuesto).** Paquete Python (lo que usa el rival / Docker) + notebooks para
  experimentación, evaluación y gráficas. Motivo: un .ipynb solo es incómodo de compartir y dockerizar.

- **2026-10-13 — Aproximación asignada: PCA (eigenfaces).** Confirmado por el profesor. El extractor
  provisional pasa a ser el definitivo; se mantiene la interfaz enchufable por limpieza.
- **2026-10-13 — Equipo de 5, GitHub, reparto mixto.** Un responsable por módulo (detector, PCA,
  BD+comparador+API, evaluación, seguridad+Docker) pero tareas como issues abiertas a todos.
  Ramas por tarea + PR con 1 aprobación + `main` protegida + squash merge. Detalle en `TRABAJO.md`.
- **2026-10-13 — Interfaz para el rival: solo librería Python** (los 9 métodos). Lo más simple;
  el profe no lo ha delimitado. El código será abierto → ninguna defensa puede depender de la
  oscuridad; secretos fuera del repo.
- **2026-10-13 — Un único paquete (`src/sistema/`) con un módulo por responsable.** Notebooks
  solo para explorar/gráficas. Descartados: repo centrado en notebooks (conflictos de merge) y
  varios repos (sobrecoste).
- **2026-10-13 — Red team interno** como fase propia antes de evaluar al rival: cada hallazgo se
  arregla o se documenta como limitación conocida.
- **2026-10-31 — Dataset del profe recibido (`Dataset.tar.gz`): 49 fotos, 1 por persona**, carpeta
  plana `nombre_apellido_año.ext`. Con Arbeloa → **50 inscritos** (el enunciado decía 51; se asume
  que el profe lo dejó en 50). Ids = nombre del archivo sin año ni extensión, sin corregir erratas.
  Trampas detectadas: gemelos, fotos muy antiguas, gafas de sol, un AVIF con extensión .jpg y un
  WebP con .jpg; el detector Haar falla en Idris Elba, Lady Gaga y Samuel L. Jackson.
  Sin segunda foto por persona no hay evaluación genuina → hay que conseguir fotos extra.
- **2026-10-31 — Modelo básico (`scripts/montar.py`, un solo comando).**
  - Lectura con Pillow (formato por contenido + rotación EXIF).
  - Alineado por ojos (ojos fijos en 30%/70% del ancho, 36% del alto) + máscara elíptica +
    estandarización → PCA compara caras, no pelo/fondo/luz.
  - PCA entrenado con las caras inscritas + sus espejos (K=50, ~90% de la varianza). Distancia euclídea.
  - **Umbral provisional** = percentil 2% de las distancias entre personas distintas (FAR≈2%), guardado
    dentro de `pca.npz` (modelo y umbral van juntos). No se calibra con copias aumentadas de las
    fotos inscritas (saldría demasiado estricto).
  - "Confianza" en la UI = relativa (softmax de distancias); el veredicto lo decide el umbral.
  - Interfaz web en Flask (`app/web.py`), fuera de `src/` (no es para el rival). Sin opción "sin detector".
- **2026-10-31 — Detector YuNet** (`modelos/face_detection_yunet_2023mar.onnx`, opencv_zoo) como
  principal, Haar de respaldo. Detecta las 49 con ojos reales. Se carga desde memoria porque OpenCV no
  abre rutas con tildes en Windows. `datos/ojos_manuales.json` queda para casos donde falle.
- **2026-10-31 — Anexo de pruebas** (`scripts/descargar_anexo.py`): Wikimedia Commons, categorías de
  cada persona (no búsqueda libre), 1 cara clara por foto (YuNet), sin la foto inscrita ni duplicados.
  Revisado a ojo (`scripts/hoja_anexo.py`): se quitaron dibujos, carteles, un imitador, otra persona y
  duplicados recortados. ~109 fotos de 44 personas + desconocidos (Oliver Phelps, Ashley Olsen).
  Sin fotos en Commons: twin melody, esty quesada, eva hache, hasbulla, joe batalan, josie totah,
  metrika. Autor y licencia en `datos/pruebas/fuentes.csv`.
- **2026-10-31 — Arbeloa inscrito con la foto que eligió el grupo** (`datos/extra/`). Sus 3 fotos de
  Commons quedan como pruebas. Con la de Commons inscrita, la del grupo sí se reconocía (d=61.5 <
  umbral 62.2); al revés, ninguna de Commons se reconoce: mismo límite de PCA.
- **2026-10-31 — Resultados con el anexo** (1 foto inscrita por persona, 50 inscritos):
  rank-1 11.4% (azar = 2%), EER 41%, FRR 75% con el umbral provisional. Ashley Olsen entra como
  Mary-Kate (ataque del gemelo confirmado). Hay "hubs" que atraen muchas fotos (p. ej. metrika).
  - Variantes (`evaluacion/experimentos.py`: CLAHE, Tan-Triggs, K 30/50/80, quitar 3 primeras
    eigenfaces, blanqueado, coseno): todas entre 11% y 14% → ±3 fotos, ruido. **El cuello de botella
    no es el preprocesado**, es PCA con una sola foto por persona en fotos "del mundo real".
  - Varias fotos inscritas por persona (leave-one-out): rank-1 31–38% (algo optimista: fotos del
    mismo evento).
  - **Decisión: se inscribe UNA foto por persona** (la del profe; la del grupo para Arbeloa), fiel al
    dataset del enunciado. Inscribir más fotos queda como mejora medida, no aplicada.
  - Las cifras con umbral elegido sobre el mismo anexo son algo optimistas.

## 4. Preguntas abiertas

- ¿El enunciado dice 51 inscritos y el dataset trae 49 (+ Arbeloa = 50)? Confirmar con el profe.
- ¿Subimos `modelos/pca.npz` y `datos/bd.csv` al repo para el rival, o que lo genere con `montar.py`?
- ¿Defensas a implementar (firma HMAC del CSV, cifrado / templates cancelables)? Ver `ataques/README.md`.

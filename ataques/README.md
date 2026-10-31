# Red team: ataques y defensas

Un script por ataque. Cada uno documenta en su docstring: **qué se asume del atacante**
(qué parte se salta / si lee o escribe la BD), **qué hace** y **resultado esperado**.
Cada hallazgo → issue con etiqueta `red-team` → se arregla o pasa a "limitaciones conocidas".

Recordatorio: el código es abierto y el rival recibe el modelo (`pca.npz`) y la BD (`bd.csv`).
Ninguna defensa puede depender de que no vea el código; los secretos (claves) van fuera del repo.

## Catálogo (de menos a más acceso del atacante)

| # | Ataque | Necesita | Estado actual | Defensa / mitigación | Script |
|---|---|---|---|---|---|
| 1 | **Impostor sin esfuerzo**: foto de un desconocido | nada | depende del umbral (FAR) | umbral elegido con evaluación | `evaluacion/evaluar.py` |
| 2 | **Parecido / gemelo** (otro Weasley, otra Olsen, Twin Melody) | una foto | muy probable que pase: PCA no distingue gemelos | documentar: límite de PCA | _pendiente_ |
| 3 | **Evasión**: gafas, pose, luz, edad | nada | falso rechazo o sin cara | alineado + normalización (hecho); documentar | _pendiente_ |
| 4 | **Bypass del detector (`_sd`)**: imágenes que no son caras | acceso a `_sd` | se aceptan como caras | rechazar si el error de reconstrucción PCA es alto ("distancia al espacio de caras") | _pendiente_ |
| 5 | **Templates fabricados (`_t`)**: ceros (= cara media), extremos | acceso a `_t` | NaN/tamaño erróneo rechazados; ceros y extremos aceptados | rechazar templates fuera de la distribución (norma, Mahalanobis) | _pendiente_ |
| 6 | **Hill-climbing**: modificar imagen/template hasta que pase | muchos intentos | solo devolvemos sí/no (no la distancia): más difícil, no imposible | no exponer distancias; limitar intentos | _pendiente_ |
| 7 | **Leer BD → replay**: usar el template de la víctima en `verificar_t` | lectura CSV | **pasa siempre** (distancia 0) | inherente a `_t`; templates protegidos (ver 8) | _pendiente_ |
| 8 | **Leer BD → reconstruir la cara** (inversión PCA: `media + t·eigenfaces`) | lectura CSV + modelo | **funciona**: cara reconocible, y pasa `verificar_sd` | cifrar CSV (clave fuera del repo) o templates cancelables (proyección aleatoria secreta) | _pendiente_ |
| 9 | **Escribir BD → suplantación**: mi template con el id de la víctima | escritura CSV | **pasa** | firmar cada fila con HMAC (clave fuera del repo) | `escritura_bd.py` |
| 10 | **Escribir BD → sabotaje**: borrar filas, filas corruptas, ids duplicados | escritura CSV | fallos / comportamiento raro | validar al cargar + firma | _pendiente_ |
| 11 | **Modificar el modelo** (`pca.npz`, incluye el umbral) | escritura disco | lo cambia todo (p. ej. umbral enorme = acepta a cualquiera) | hash/firma del modelo comprobado al cargar | _pendiente_ |

## Limitaciones conocidas (no son ataques, pero el rival las encontrará)

- Una sola foto por persona en la inscripción → PCA con ≤ N-1 componentes y umbral provisional.
- Detector Haar: Samuel L. Jackson no se detecta (se inscribe con ojos marcados a mano y `_sd`);
  en 10 de 49 fotos los ojos no se detectan y su posición se estima (alineado peor).
- Fotos de cuerpo entero (Isabel II 1945): cara muy pequeña → poca resolución.

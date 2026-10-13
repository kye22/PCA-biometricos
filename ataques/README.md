# Red team

Un script por ataque. Cada uno documenta en su docstring: **qué se asume del atacante**
(qué parte se salta / si lee o escribe la BD), **qué hace** y **resultado esperado**.

| Ataque | Supuesto | Script | Estado |
|---|---|---|---|
| Suplantación escribiendo en la BD | escritura en `bd.csv` | `escritura_bd.py` | funciona (BD sin integridad) |
| _bypass_ del detector | acceso a `_sd` | _pendiente_ | |
| Template arbitrario / NaN / tamaño raro | acceso a `_t` | _pendiente_ | |
| Reconstruir caras desde la BD | lectura de `bd.csv` + modelo | _pendiente_ | |

Cada hallazgo → issue con etiqueta `red-team` → se arregla o pasa a "limitaciones conocidas".

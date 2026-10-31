# Reconocimiento facial con PCA — Sistemas Biométricos

Práctica de grupo: sistema de reconocimiento facial basado en **PCA (eigenfaces)** en Python,
con base de datos en `.csv` y 51 personas inscritas.

- Enunciado: [`Prácticas.md`](Prácticas.md) (original en `Prácticas.pdf`)
- **Cómo trabajamos (reparto y ramas):** [`docs/TRABAJO.md`](docs/TRABAJO.md)
- Decisiones y su porqué: [`docs/decisiones.md`](docs/decisiones.md)

## API

| Entrada | Inscribir | Verificar | Identificar |
|---|---|---|---|
| foto | `inscribir(id, foto)` | `verificar(id, foto)` | `identificar(foto)` |
| foto sin detector | `inscribir_sd(id, foto)` | `verificar_sd(id, foto)` | `identificar_sd(foto)` |
| template | `inscribir_t(id, template)` | `verificar_t(id, template)` | `identificar_t(template)` |

`foto` = ruta o array. `verificar*` → `bool`; `identificar*` → id o `None`.

## Puesta en marcha (3 comandos)

Necesitas `Dataset.tar.gz` (el del profe, no está en git) en la raíz del repo.

```bash
pip install -r requirements.txt
python scripts/montar.py      # descomprime, detecta y alinea caras, entrena PCA, inscribe a todos
python app/web.py             # interfaz web en http://localhost:5000
```

`montar.py` lista foto por foto cómo ha ido la detección y termina con el umbral calculado.
Se puede repetir cuando quieras (rehace modelo y BD desde cero).

### Interfaz web

Subes una foto y muestra: la detección dibujada (cara y ojos), la cara alineada y normalizada,
la reconstrucción PCA, el veredicto (identificar o verificar contra un famoso) y el ranking de
los 5 más parecidos con distancia, umbral y confianza relativa.

### Otras formas de usarlo

```bash
python scripts/identificar.py <foto> [--sd]
python scripts/verificar.py <id> <foto> [--sd]
python evaluacion/evaluar.py   # métricas con el anexo de pruebas datos/pruebas/<id>/*.jpg
pytest                         # tests (no necesitan fotos)
```

```python
import sys; sys.path.insert(0, "src")      # o: pip install -e .
from sistema import inscribir, verificar, identificar
identificar("foto.jpg")                     # -> "adele" | None
```

## Datos

| Ruta | Qué es | ¿En git? |
|---|---|---|
| `Dataset.tar.gz` | 49 fotos del profe, 1 por persona | no |
| `datos/fotos/` | se descomprime ahí (`nombre_apellido_AAAA.ext` → id `nombre_apellido`) | no |
| `datos/extra/` | nuestras inscripciones (Álvaro Arbeloa), mismo formato | sí |
| `datos/ojos_manuales.json` | ojos marcados a mano donde el detector falla | sí |
| `datos/pruebas/<id>/` | anexo de fotos distintas para evaluar (no se inscriben) | sí |
| `modelos/pca.npz`, `datos/bd.csv` | modelo (+ umbral) y BD generados por `montar.py` | no (de momento) |

## Docker

```bash
docker build -t pca-biometricos .
docker run --rm -p 5000:5000 pca-biometricos     # monta todo y abre la web en :5000
```

Ataques conocidos y defensas previstas: [`ataques/README.md`](ataques/README.md).

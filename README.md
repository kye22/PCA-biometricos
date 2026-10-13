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

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
pytest                         # debe salir todo en verde
```

## Uso

Fotos en `datos/fotos/<id>/*.jpg` (una carpeta por persona). Luego:

```bash
python scripts/entrenar_pca.py           # -> modelos/pca.npz
python scripts/inscribir_todos.py        # -> datos/bd.csv (1ª foto de cada persona)
python scripts/verificar.py <id> <foto>
python scripts/identificar.py <foto>
python evaluacion/evaluar.py             # EER y rank-1 con el resto de fotos
```

Todos aceptan `--sd` (omitir detector) y `--help`. Rutas y umbral configurables con
`SISTEMA_FOTOS`, `SISTEMA_BD`, `SISTEMA_MODELO`, `SISTEMA_UMBRAL`, `SISTEMA_COMPONENTES`.

Como librería:

```python
from sistema import inscribir, verificar, identificar
verificar("Alvaro_Arbeloa_Coca", "foto.jpg")
```

## Docker

```bash
docker build -t pca-biometricos .
docker run --rm -it -v "$PWD/datos:/app/datos" pca-biometricos
```

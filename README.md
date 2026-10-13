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

Instrucciones de instalación y Docker: _pendiente_.

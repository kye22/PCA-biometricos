# Reconocimiento facial PCA
#
# Construcción:
#   docker build -t pca-biometricos .
#
# Ejecución:
#   El dataset se proporciona mediante un volumen.
#   No se incluye dentro de la imagen Docker.
#
# El modelo PCA genérico (modelos/pca_base.npz)
# sí se incluye en la imagen.

FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[web]"
COPY . .

ENV HOST=0.0.0.0 PORT=5000
EXPOSE 5000
CMD ["sh", "-c", "python scripts/montar.py && python app/web.py"]

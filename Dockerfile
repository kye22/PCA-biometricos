# Uso (con Dataset.tar.gz en la raíz del repo):
#   docker build -t pca-biometricos .
#   docker run --rm -p 5000:5000 pca-biometricos        -> http://localhost:5000
# Monta el sistema (descomprime, entrena, inscribe) y arranca la interfaz web.
# Como librería:  docker run --rm -it pca-biometricos python
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .

ENV HOST=0.0.0.0 PORT=5000
EXPOSE 5000
CMD ["sh", "-c", "python scripts/montar.py && python app/web.py"]

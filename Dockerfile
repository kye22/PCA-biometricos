# Provisional (módulo 5). Uso:
#   docker build -t pca-biometricos .
#   docker run --rm -it -v "$PWD/datos:/app/datos" pca-biometricos
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .

CMD ["python"]

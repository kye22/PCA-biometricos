# El dataset del profesor se monta al ejecutar el contenedor.
# Docker genera una partición reproducible e inscribe solo sus fotos de inscripción.
#
# Construcción:
#   docker build -t pca-biometricos .
#
# Ejecución en PowerShell:
#   docker run --rm -p 5000:5000 --mount "type=bind,source=${PWD}/Dataset.tar.gz,target=/app/Dataset.tar.gz,readonly" pca-biometricos

FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir -e ".[web]"

COPY . .

ENV HOST=0.0.0.0 PORT=5000

EXPOSE 5000

CMD ["sh", "-c", "python evaluacion/particiones.py --semilla 42 && python scripts/montar.py --manifiesto evaluacion/particion.json && python app/web.py"]
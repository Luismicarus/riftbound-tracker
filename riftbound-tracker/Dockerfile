FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot ./bot
COPY data/legends.yaml ./data/legends.yaml

# No ejecutar como root. UID 1000 coincide con el usuario por defecto de la Raspberry,
# así el volumen ./data se puede escribir sin líos de permisos.
RUN useradd --uid 1000 --create-home bot && chown -R bot:bot /app
USER bot

CMD ["python", "-m", "bot"]

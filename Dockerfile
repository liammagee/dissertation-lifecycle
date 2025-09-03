FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY . /app

# Collect static for admin and app
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000
RUN chmod +x bin/entrypoint.sh
CMD ["bash","-lc","./bin/entrypoint.sh"]

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
# CMD ["gunicorn", "dissertation_tracker.wsgi:application", "--bind", "0.0.0.0:8000"]
# CMD ["bash","-lc","gunicorn dissertation_tracker.wsgi:application --workers 1 --threads 2 --timeout 60 --bind 0.0.0.0:${PORT}"]
# Dockerfile (replace <<<ACTUAL_PACKAGE>>>)
CMD ["bash","-lc","gunicorn dissertation_lifecycle.wsgi:application --workers 1 --threads 2 --timeout 60 --access-logfile - --log-level debug --bind 0.0.0.0:${PORT}"]

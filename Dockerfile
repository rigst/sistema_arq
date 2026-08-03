FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 libgdk-pixbuf-2.0-0 libjpeg62-turbo libpango-1.0-0 \
    libpangocairo-1.0-0 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
RUN addgroup --system arq && adduser --system --ingroup arq arq \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R arq:arq /app

USER arq
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--config", "deploy/gunicorn.conf.py"]

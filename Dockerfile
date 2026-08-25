FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install gunicorn uvicorn[standard]

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY . .

RUN mkdir -p /app/logs /app/staticfiles /app/media \
    && chown -R appuser:appgroup /app \
    && chmod +x /app/entrypoint.sh

RUN SECRET_KEY="dummy_key_for_build" python manage.py collectstatic --noinput --clear

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["gunicorn", "Rai_Backend.asgi:application", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker", "--workers", "3"]
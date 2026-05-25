FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV AUTH_DATABASE_PATH=/app/data/auth.db
ENV AUTH_JWT_SECRET=change-me-in-production
ENV AUTH_ACCESS_TOKEN_TTL_MINUTES=15
ENV AUTH_REFRESH_TOKEN_TTL_DAYS=30

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py .

RUN mkdir -p /app/data

EXPOSE 8083

CMD ["gunicorn", "--bind", "0.0.0.0:8083", "--workers", "1", "--threads", "4", "run:app"]

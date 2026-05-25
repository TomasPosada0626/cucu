FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV SUPPORT_DATABASE_PATH=/app/data/support.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py .

RUN mkdir -p /app/data

EXPOSE 8085

CMD ["gunicorn", "--bind", "0.0.0.0:8085", "--workers", "1", "--threads", "4", "run:app"]

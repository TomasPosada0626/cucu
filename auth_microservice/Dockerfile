FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV AUTH_ACCESS_TOKEN_TTL_MINUTES=15
ENV AUTH_REFRESH_TOKEN_TTL_DAYS=30

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py .

RUN useradd -m -u 1000 appuser \
	&& chown -R appuser:appuser /app
USER appuser

EXPOSE 8083

CMD ["gunicorn", "--bind", "0.0.0.0:8083", "--workers", "1", "--threads", "4", "run:app"]

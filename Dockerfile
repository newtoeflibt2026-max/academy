FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# shell form: $PORT ?????? ??? /bin/sh -c
CMD gunicorn -w 1 -k gthread --threads 4 --timeout 120 -b 0.0.0.0:${PORT:-8080} wsgi:app

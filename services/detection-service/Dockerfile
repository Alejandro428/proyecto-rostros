FROM python:3.11-slim

WORKDIR /app

# Actualizamos las librerías para que sean compatibles con Debian Bookworm
RUN apt-get update && apt-get install -y \
    build-essential \
    librdkafka-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
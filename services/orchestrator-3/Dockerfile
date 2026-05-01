FROM python:3.11-slim

WORKDIR /app

# Instalamos dependencias necesarias (libgl1 en lugar de libgl1-mesa-glx)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instalamos las librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
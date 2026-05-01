#!/usr/bin/env bash
# Despliega un modelo ya entrenado en age-service.
# Si el modelo no existe localmente, lo descarga automáticamente de Google Drive.
# Uso: bash scripts/deploy_model.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MODEL_SRC="$ROOT_DIR/training/modelo_menores.h5"
MODEL_DST="$ROOT_DIR/services/age-service/modelo_menores.h5"
GDRIVE_ID="1-S6qiekqWeI4Ja1PI18hHXK9UxXzbgr5"
GDRIVE_URL="https://drive.usercontent.google.com/download?id=${GDRIVE_ID}&export=download&authuser=0&confirm=t"

if [ ! -f "$MODEL_SRC" ]; then
  echo "===== [0/3] Modelo no encontrado — descargando desde Google Drive ====="
  curl -L "$GDRIVE_URL" -o "$MODEL_SRC"
  echo "Modelo descargado → $MODEL_SRC"
fi

echo "===== [1/3] Copiando modelo a age-service ====="
cp "$MODEL_SRC" "$MODEL_DST"
echo "Modelo copiado → $MODEL_DST"

echo "===== [2/3] Reconstruyendo age-detection ====="
docker compose -f "$ROOT_DIR/docker-compose.yml" build age-detection

echo "===== [3/3] Reiniciando age-detection ====="
docker compose -f "$ROOT_DIR/docker-compose.yml" up -d --force-recreate age-detection

echo ""
echo "===== Despliegue completado ====="

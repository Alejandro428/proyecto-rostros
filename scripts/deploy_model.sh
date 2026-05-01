#!/usr/bin/env bash
# Despliega un modelo ya entrenado (ej. desde Google Colab) en age-service.
# Uso:
#   1. Descarga el modelo desde Colab y guárdalo en training/modelo_menores.h5
#   2. bash scripts/deploy_model.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MODEL_SRC="$ROOT_DIR/training/modelo_menores.h5"
MODEL_DST="$ROOT_DIR/services/age-service/modelo_menores.h5"

if [ ! -f "$MODEL_SRC" ]; then
  echo "ERROR: no se encontró $MODEL_SRC"
  echo "Descarga el modelo desde Colab y guárdalo en training/modelo_menores.h5"
  exit 1
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

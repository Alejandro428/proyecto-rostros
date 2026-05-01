#!/usr/bin/env bash
# Entrena la CNN con GPU (RTX 3080) y despliega el modelo en age-service.
# Uso: bash scripts/train.sh
#
# Si has entrenado en Google Colab, usa scripts/deploy_model.sh en su lugar.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WIN_ROOT="$(echo "$ROOT_DIR" | sed 's|^/\([a-zA-Z]\)/|\1:/|')"

MODEL_SRC="$ROOT_DIR/training/modelo_menores.h5"
MODEL_DST="$ROOT_DIR/services/age-service/modelo_menores.h5"

echo "===== [1/4] Construyendo imagen de entrenamiento (GPU) ====="
docker build -t ia_training "$ROOT_DIR/training"

echo "===== [2/4] Entrenando red neuronal en RTX 3080 ====="
# WORKDIR=/project/training → SRC_PATH=../face_age=/project/face_age ✓
MSYS_NO_PATHCONV=1 docker run --rm --gpus all \
  -v "${WIN_ROOT}/training:/project/training" \
  -v "${WIN_ROOT}/face_age:/project/face_age:ro" \
  ia_training

if [ ! -f "$MODEL_SRC" ]; then
  echo "ERROR: no se generó $MODEL_SRC"
  exit 1
fi

echo "===== [3/4] Copiando modelo a age-service ====="
WIN_SRC="$(echo "$MODEL_SRC" | sed 's|^/mnt/\([a-zA-Z]\)/|\1:/|; s|/|\\|g')"
WIN_DST="$(echo "$MODEL_DST" | sed 's|^/mnt/\([a-zA-Z]\)/|\1:/|; s|/|\\|g')"
powershell.exe -Command "Copy-Item '$WIN_SRC' '$WIN_DST' -Force"
echo "Modelo copiado → $MODEL_DST"

echo "===== [4/4] Reconstruyendo y reiniciando age-detection ====="
docker compose -f "$ROOT_DIR/docker-compose.yml" build age-detection
docker compose -f "$ROOT_DIR/docker-compose.yml" up -d --force-recreate age-detection

echo ""
echo "===== Entrenamiento y despliegue completados ====="

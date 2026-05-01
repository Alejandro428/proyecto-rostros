# Sistema de Detección y Pixelado de Rostros de Menores

Sistema distribuido orientado a eventos para detectar rostros en imágenes, clasificar si corresponden a menores de edad mediante una red neuronal convolucional, y pixelar automáticamente las caras de menores.

---

## Índice

1. [Requisitos previos](#requisitos-previos)
2. [Cómo ejecutar el sistema](#cómo-ejecutar-el-sistema)
3. [Estructura del proyecto](#estructura-del-proyecto)
4. [Descripción de cada servicio](#descripción-de-cada-servicio)
5. [Topics y flujo de eventos](#topics-y-flujo-de-eventos)
6. [Documentación funcional](#documentación-funcional)
7. [Gestión de errores](#gestión-de-errores)

---

## Requisitos previos

- Docker Desktop (con WSL2 en Windows)
- Docker Compose v2
- Git
- Archivo `.env` en la raíz del proyecto (ver sección siguiente)

### Archivo `.env`

Crea un fichero `.env` en la raíz con las siguientes variables:

```env
KAFKA_SERVER=kafka:9092

MINIO_ENDPOINT=http://minio:9000
MINIO_PUBLIC_URL=http://localhost:9000
MINIO_USER=minioadmin
MINIO_PASSWORD=minioadmin

DB_HOST=db
DB_NAME=db_rostros
DB_USER=postgres
DB_PASSWORD=postgres

MAX_FILE_SIZE=10485760
PYTHONUNBUFFERED=1
```

---

## Cómo ejecutar el sistema

### 1. Levantar todos los servicios

```bash
docker compose up -d --build
```

### 2. Verificar que todos los contenedores están en marcha

```bash
docker compose ps
```

Todos los servicios deben estar en estado `running`. El contenedor `kafka-init` aparecerá como `exited (0)` — es correcto, su trabajo es crear los topics al arrancar y terminar.

### 3. Probar el sistema

**Subir una imagen:**
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/ruta/a/imagen.jpg"
```

La respuesta incluye el `GUID_Solicitud`:
```json
{"GUID_Solicitud": "abc-123", "Id_Imagen": 1, "status": "INICIADO"}
```

**Consultar el resultado completo** (esperar unos segundos):
```bash
curl http://localhost:8001/resultado/abc-123
```

**Consultar una cara concreta:**
```bash
curl http://localhost:8001/resultado/abc-123/cara/2
```

### 4. Detener el sistema

```bash
docker compose down
```

Para eliminar también los volúmenes (BD, MinIO, Kafka):
```bash
docker compose down -v
```

### 5. Entrenamiento del modelo (opcional)

Si quieres re-entrenar la red neuronal con tu GPU local:
```bash
bash scripts/train.sh
```

Si has entrenado en Google Colab y tienes el `.h5` descargado:
```bash
# Copia el modelo a training/modelo_menores.h5 y ejecuta:
bash scripts/deploy_model.sh
```

---

## Estructura del proyecto

```
proyecto_rostros/
├── docker-compose.yml
├── .env
├── scripts/
│   ├── train.sh              # Entrenamiento local con GPU (RTX 3080)
│   └── deploy_model.sh       # Despliegue de modelo entrenado en Colab
├── training/
│   ├── Dockerfile
│   ├── train_age.py          # Script de entrenamiento local
│   └── red_neuronal_proyecto_imagenes.ipynb  # Notebook para Google Colab
├── infra/
│   └── postgres/
│       └── init.sql          # Schema de la base de datos
├── contracts/
│   ├── comandos/             # Schemas JSON de comandos Kafka
│   └── eventos/              # Schemas JSON de eventos Kafka
└── services/
    ├── api-1/                # Ingesta de imágenes (fusiona Orquestador-1)
    ├── detection-service/    # Detección de rostros con OpenCV
    ├── orchestrator-2/       # Orquestación post-detección
    ├── age-service/          # Clasificación de edad con red neuronal
    ├── orchestrator-3/       # Orquestación post-clasificación
    ├── pixelation-service/   # Pixelado y generación de imágenes (fusiona Orquestador-4)
    └── api-2/                # Consulta de resultados
```

---

## Descripción de cada servicio

### API-1 — Ingesta (puerto 8000)

Punto de entrada del sistema. Fusiona el rol de Orquestador-1.

**Responsabilidades:**
- Valida el fichero recibido (extensión y tamaño máximo)
- Sube la imagen original al bucket `images-raw` de MinIO
- Registra la solicitud en PostgreSQL con estado `INICIADO`
- Publica `images.raw` y `cmd.face_detection` en Kafka
- Devuelve el `GUID_Solicitud` al cliente

**Endpoints:**
- `POST /upload` — sube una imagen e inicia el pipeline
- `GET /health` — comprobación de salud

---

### Detection Service — Detección de rostros

Detecta los rostros presentes en la imagen mediante el clasificador Haar Cascade de OpenCV.

**Responsabilidades:**
- Consume `cmd.face_detection`
- Descarga la imagen de MinIO
- Ejecuta la detección con `haarcascade_frontalface_default.xml`
- Registra en BD el timestamp de fin de detección
- Publica `evt.face_detection.completed` con la lista de bounding boxes

**Parámetros de detección:** `scaleFactor=1.15`, `minNeighbors=5`, `minSize=(50,50)`

---

### Orchestrator-2 — Orquestación post-detección

Procesa el resultado de la detección y decide el siguiente paso.

**Responsabilidades:**
- Consume `evt.face_detection.completed`
- Para cada cara detectada: recorta el crop, lo sube a MinIO e inserta una fila en `Imagenes`
- **Si hay caras:** publica `cmd.age_detection` con los crops
- **Si no hay caras:** publica `cmd.storage` para cerrar el flujo

---

### Age Service — Clasificación de edad

Clasifica si cada cara corresponde a un menor mediante una CNN entrenada.

**Responsabilidades:**
- Consume `cmd.age_detection`
- Descarga cada crop de MinIO
- Aplica el modelo `modelo_menores.h5` con umbral `score >= 0.40 → MENOR`
- Actualiza `Mayor_18` y `Escore` en BD por cada cara
- Publica `evt.age_detection.completed` con `score` y `es_menor` por cara

**Modelo:** CNN personalizada entrenada con el dataset `face_age`. Entrada `256×320×3`, salida sigmoid `[0,1]`.

---

### Orchestrator-3 — Orquestación post-clasificación

Evalúa si existen menores y decide si es necesario pixelar.

**Responsabilidades:**
- Consume `evt.age_detection.completed`
- **Si hay menores:** actualiza `Inicio_Pixelado` en BD y publica `cmd.pixelation`
- **Si no hay menores:** publica `cmd.storage` (no se pixela nada)

---

### Pixelation Service — Pixelado y cierre (fusiona Orquestador-4)

Genera las imágenes de salida y cierra el flujo. Fusiona el rol de Orquestador-4.

**Responsabilidades:**
- Consume `cmd.pixelation` y `cmd.storage`
- Crea automáticamente el bucket `images-processed` si no existe

**Caso `cmd.pixelation` (hay menores):**
- Genera imagen con marcos: rectángulo rojo (MENOR) o verde (ADULTO) con score
- Genera imagen terminada: caras de menores pixeladas (reducción a 12×12 y escalado)
- Sube ambas imágenes a `images-processed`
- Cierra la solicitud con `Estado = COMPLETADO`

**Caso `cmd.storage` con caras (no hay menores):**
- Genera solo la imagen con marcos (todos marcados como ADULTO en verde)
- Cierra la solicitud con `Estado = COMPLETADO`

**Caso `cmd.storage` sin caras:**
- Cierra la solicitud con `Estado = COMPLETADO` sin generar imágenes

En todos los casos publica `evt.pixelation.completed`.

---

### API-2 — Consulta de resultados (puerto 8001)

Sirve los resultados procesados mediante presigned URLs de MinIO (válidas 1 hora).

**Endpoints:**
- `GET /resultado/{guid}` — solicitud completa: estado, tiempos, imagen original, imagen con marcos, imagen terminada, y lista de caras con su clasificación y bounding box
- `GET /resultado/{guid}/cara/{id_cara}` — cara individual: crop de la cara, `es_menor`, `score` y bounding box
- `GET /health` — comprobación de salud

---

## Topics y flujo de eventos

### Topics Kafka

| Topic | Tipo | Productor | Consumidor |
|---|---|---|---|
| `images.raw` | Evento | API-1 | — (auditoría) |
| `cmd.face_detection` | Comando | API-1 | Detection Service |
| `evt.face_detection.completed` | Evento | Detection Service | Orchestrator-2 |
| `cmd.age_detection` | Comando | Orchestrator-2 | Age Service |
| `evt.age_detection.completed` | Evento | Age Service | Orchestrator-3 |
| `cmd.pixelation` | Comando | Orchestrator-3 | Pixelation Service |
| `cmd.storage` | Comando | Orchestrator-2 / Orchestrator-3 | Pixelation Service |
| `evt.pixelation.completed` | Evento | Pixelation Service | — (cierre de flujo) |

---

## Documentación funcional

### Diagrama de arquitectura

```
                        ┌─────────────┐
     Cliente ──────────►│    API-1    │
                        │  (8000)     │
                        └──────┬──────┘
                               │ cmd.face_detection
                               ▼
                     ┌──────────────────┐
                     │Detection Service │
                     │  (Haar Cascade)  │
                     └────────┬─────────┘
                              │ evt.face_detection.completed
                              ▼
                     ┌──────────────────┐
                     │ Orchestrator-2   │──── sin caras ────► cmd.storage ──┐
                     │  (cropea caras)  │                                   │
                     └────────┬─────────┘                                   │
                              │ cmd.age_detection                           │
                              ▼                                             │
                     ┌──────────────────┐                                   │
                     │  Age Service     │                                   │
                     │  (CNN ≥ 0.40)    │                                   │
                     └────────┬─────────┘                                   │
                              │ evt.age_detection.completed                 │
                              ▼                                             │
                     ┌──────────────────┐                                   │
                     │ Orchestrator-3   │── sin menores ──► cmd.storage ────┤
                     │ (decide pixelar) │                                   │
                     └────────┬─────────┘                                   │
                              │ cmd.pixelation                              │
                              ▼                                             ▼
                     ┌────────────────────────────────────────────────────────┐
                     │               Pixelation Service                       │
                     │   marcos + terminada  /  solo marcos  /  sin imágenes  │
                     │                evt.pixelation.completed                │
                     └────────────────────────────────────────────────────────┘
                                          │ PostgreSQL + MinIO
                                          ▼
                        ┌─────────────┐
     Cliente ──────────►│    API-2    │
                        │  (8001)     │
                        └─────────────┘
```

### Infraestructura de soporte

| Componente | Uso |
|---|---|
| **Apache Kafka 4.2** | Bus de eventos entre servicios |
| **MinIO** | Almacenamiento de imágenes (S3-compatible) |
| **PostgreSQL 15** | Estado de solicitudes y clasificaciones |

### Flujo de eventos completo

**Caso 1 — Imagen con menores detectados:**
```
POST /upload
  API-1        → MinIO(images-raw) + BD(INICIADO) + cmd.face_detection
  Detection    → detecta N caras + BD(fin_deteccion) + evt.face_detection.completed
  Orch-2       → N crops a MinIO + N filas en BD(Imagenes) + cmd.age_detection
  Age Service  → clasifica N caras + BD(Mayor_18, Escore) + evt.age_detection.completed
  Orch-3       → hay menores → BD(Inicio_Pixelado) + cmd.pixelation
  Pixelation   → marcos.jpg + terminada.jpg a MinIO + BD(COMPLETADO) + evt.pixelation.completed
GET /resultado/{guid} → presigned URLs + scores por cara
```

**Caso 2 — Imagen sin caras:**
```
  Orch-2 → 0 caras → cmd.storage (faces=[])
  Pixelation → BD(COMPLETADO) sin imágenes
```

**Caso 3 — Caras detectadas pero ningún menor:**
```
  Orch-3 → 0 menores → cmd.storage (faces=[adultos])
  Pixelation → marcos.jpg a MinIO (adultos en verde) + BD(COMPLETADO)
```

### Estructura de mensajes Kafka

Los contratos completos en formato JSON Schema están en el directorio `/contracts/`.

**Ejemplo: `evt.age_detection.completed`**
```json
{
  "version": "1.0",
  "timestamp": "2025-01-01T12:00:00",
  "GUID_Solicitud": "uuid-v4",
  "Id_Imagen": 1,
  "s3_key": "guid/uuid.jpg",
  "faces": [
    {
      "face_id": 2,
      "bbox": {"x": 100, "y": 50, "w": 80, "h": 90},
      "es_menor": true,
      "score": 0.8734
    }
  ]
}
```

---

## Gestión de errores

### Qué ocurre si falla un servicio

| Escenario | Comportamiento |
|---|---|
| **Falla Detection Service** | El mensaje `cmd.face_detection` permanece en Kafka. Al reiniciar, lo relee y reintenta. La solicitud en BD queda en estado `INICIADO`. |
| **Falla Age Service** | El mensaje `cmd.age_detection` permanece en Kafka. Los crops siguen en MinIO. Al reiniciar, reclasifica desde el principio. |
| **Falla Orchestrator-3** | El mensaje `evt.age_detection.completed` permanece en Kafka. Al reiniciar, repite la decisión menores/no menores. |
| **Falla Pixelation Service** | El mensaje `cmd.pixelation` o `cmd.storage` permanece en Kafka. Al reiniciar, regenera las imágenes (la subida a MinIO es idempotente por clave fija). |
| **Falla MinIO** | El servicio captura la excepción en el `try/except` del loop. El offset Kafka no avanza, por lo que el mensaje se reentrega al reiniciar. |
| **Falla PostgreSQL** | Igual que MinIO: excepción capturada, offset no avanzado, reintento automático. |

### Estrategias de manejo implementadas

**Reintentos automáticos por Kafka:**
Todos los consumers usan `auto.offset.reset=earliest` y grupos de consumo dedicados (`face-group`, `orch-2-group`, etc.). Si un servicio falla sin confirmar el mensaje, Kafka lo reentrega al reiniciar. La entrega es *at-least-once*.

**Aislamiento de errores por cara:**
En Age Service y Orchestrator-2, los errores en el procesamiento de una cara individual son capturados y logueados sin interrumpir el procesamiento de las demás caras del mismo mensaje.

**Idempotencia en MinIO:**
Las claves de las imágenes de salida son deterministas (`{guid}/marcos.jpg`, `{guid}/terminada.jpg`). Si se reprocesa una solicitud, las imágenes se sobreescriben sin efectos secundarios.

**Creación automática de buckets:**
`api-1` crea `images-raw` al arrancar. `pixelation-service` crea `images-processed` al arrancar. El sistema no falla si los buckets ya existen.

### Limitaciones conocidas

- **Sin dead-letter queue (DLQ):** Los mensajes sistemáticamente inprocesables (imagen corrupta, formato inesperado) no se apartan a un topic de errores. El consumer podría quedarse atascado en ellos.
- **Sin backoff exponencial:** Un fallo de BD o MinIO provoca reintento inmediato en el siguiente ciclo del loop, sin espera progresiva.
- **Consistencia eventual:** El estado en BD puede quedar parcialmente actualizado si un servicio falla a mitad del procesamiento de un mensaje con múltiples caras.

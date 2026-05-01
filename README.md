# Sistema de Detección y Pixelado de Rostros

Sistema distribuido basado en eventos (Event-Driven Architecture) que procesa imágenes para detectar rostros, clasificar la edad de cada uno y pixelar automáticamente los rostros de menores de 18 años.

---

## Arquitectura general

```
Cliente
  │
  ▼
[API-1] ────────────────────────────────────────────── Puerto 8000
  │  Recibe imagen (multipart/form-data)
  │  Sube original a MinIO (images-raw)
  │  Registra solicitud en PostgreSQL
  │  Publica cmd.face_detection
  │
  ▼ Kafka: cmd.face_detection
[Detection Service]
  │  Descarga imagen de MinIO
  │  Detecta rostros con OpenCV Haar Cascade
  │  Registra Fin_Deteccion_Caras en BD
  │  Publica evt.face_detection.completed
  │
  ▼ Kafka: evt.face_detection.completed
[Orchestrator-2]
  │  Cropea cada cara de la imagen original
  │  Sube cada crop a MinIO (images-raw)
  │  Registra Inicio_Edad en BD
  │  Publica cmd.age_detection  (con s3_key_cara por cara)
  │
  ▼ Kafka: cmd.age_detection
[Age Service]
  │  Descarga cada crop de MinIO
  │  Clasifica menor/mayor con modelo TF (threshold 0.35)
  │  Registra clasificación en Imagenes + Fin_edad en BD
  │  Publica evt.age_detection.completed  (es_menor + score por cara)
  │
  ▼ Kafka: evt.age_detection.completed
[Orchestrator-3]
  │  Registra Inicio_Pixelado en BD
  │  Publica cmd.pixelation
  │
  ▼ Kafka: cmd.pixelation  (o cmd.storage si 0 caras detectadas)
[Pixelation Service]
  │  Descarga imagen original de MinIO
  │  Genera imagen_marcos: bbox + score sobre cada cara (rojo=menor, verde=mayor)
  │  Genera imagen_terminada: caras de menores pixeladas
  │  Sube ambas imágenes a MinIO (images-processed)
  │  Registra URLs + Fin_Solicitud + Estado=COMPLETADO en BD
  │
  ▼
[API-2] ────────────────────────────────────────────── Puerto 8001
     Consulta estado y resultados desde PostgreSQL
     Devuelve presigned URLs de las tres imágenes (original, marcos, terminada)
```

**Nota arquitectónica:** O1 está fusionado en API-1. O4 está fusionado en Pixelation Service. Si no se detectan caras, Orchestrator-2 publica directamente en `cmd.storage` (sin pasar por age ni O3), y Pixelation cierra la solicitud.

---

## Tópicos Kafka

| Tópico                         | Productor         | Consumidor          |
|--------------------------------|-------------------|---------------------|
| `cmd.face_detection`           | API-1             | Detection Service   |
| `evt.face_detection.completed` | Detection Service | Orchestrator-2      |
| `cmd.age_detection`            | Orchestrator-2    | Age Service         |
| `evt.age_detection.completed`  | Age Service       | Orchestrator-3      |
| `cmd.pixelation`               | Orchestrator-3    | Pixelation Service  |
| `cmd.storage`                  | Orchestrator-2    | Pixelation Service  |

Todos los `cmd.*` incluyen: `version`, `timestamp` (ISO 8601), `GUID_Solicitud`, `Id_Imagen`, `s3_key`.

---

## Servicios

### API-1 (Puerto 8000)

**Endpoints:**
- `POST /upload` — recibe imagen, inicia el pipeline
- `GET /health` — estado del servicio

**Responsabilidades:**
- Valida imagen (extensión, tamaño máximo 50 MB)
- Sube imagen original a MinIO (`images-raw`)
- Inserta fila en `Solicitud` e `Imagenes` en PostgreSQL
- Registra `Inicio_Solicitud` e `Inicio_Deteccion_Caras` en BD
- Publica `cmd.face_detection`

**Stack:** FastAPI · boto3 · confluent-kafka · psycopg2

---

### Detection Service

**Consume:** `cmd.face_detection`  
**Produce:** `evt.face_detection.completed`

**Responsabilidades:**
- Descarga imagen original de MinIO
- Detecta rostros con OpenCV Haar Cascade (`haarcascade_frontalface_default.xml`)
- Genera lista de faces con `face_id` y bbox `{x, y, w, h}`
- Registra `Fin_Deteccion_Caras` en BD

**Stack:** OpenCV · boto3 · confluent-kafka · psycopg2

---

### Orchestrator-2

**Consume:** `evt.face_detection.completed`  
**Produce:** `cmd.age_detection` | `cmd.storage` (si 0 caras)

**Responsabilidades:**
- Cropea cada cara de la imagen original
- Sube cada crop a MinIO (`images-raw/{guid}/faces/{id_cara}.jpg`)
- Inserta fila en `Imagenes` por cara detectada (obtiene `Id_Imagen` del SERIAL)
- Registra `Inicio_Edad` en BD
- Si hay caras → publica `cmd.age_detection`
- Si no hay caras → publica `cmd.storage`

**Stack:** OpenCV · boto3 · confluent-kafka · psycopg2

---

### Age Service

**Consume:** `cmd.age_detection`  
**Produce:** `evt.age_detection.completed`

**Responsabilidades:**
- Descarga cada crop de cara de MinIO
- Preprocesa: resize a (224, 224), normaliza `/255.0`
- Clasifica con modelo TensorFlow (`modelo_menores.h5`)
- Threshold: **0.35** — se prioriza no perderse ningún menor (falso positivo preferible a falso negativo)
- Actualiza `Mayor_18` y `Escore` en `Imagenes`
- Registra `Fin_edad` en BD
- Publica resultado con `es_menor`, `score` y `bbox` por cara

**Nota modelo:** El modelo actual es el desplegado en `age-service/modelo_menores.h5`. Para sustituirlo por el CNN básica entrenado con `ia_training/train_age.py`, copiar el `.h5` generado y actualizar `IMG_SIZE_CV2 = (320, 256)` en `age-service/config.py`.

**Stack:** TensorFlow · OpenCV · boto3 · confluent-kafka · psycopg2

---

### Orchestrator-3

**Consume:** `evt.age_detection.completed`  
**Produce:** `cmd.pixelation`

**Responsabilidades:**
- Registra `Inicio_Pixelado` en BD
- Publica `cmd.pixelation` con la lista de caras clasificadas

**Stack:** confluent-kafka · psycopg2

---

### Pixelation Service

**Consume:** `cmd.pixelation` | `cmd.storage`  
**Produce:** —

**Responsabilidades (cmd.pixelation):**
- Descarga imagen original de MinIO (`images-raw`)
- Genera `marcos.jpg`: bbox dibujado sobre cada cara, con etiqueta MENOR/MAYOR y score (rojo = menor, verde = mayor)
- Genera `terminada.jpg`: caras de menores pixeladas (reducción a 12×12 px y ampliación)
- Sube ambas imágenes a MinIO (`images-processed`)
- Registra `URL_Imagen_Marcos`, `URL_Imagen_Terminada`, `Fin_Pixelado`, `Fin_Solicitud`, `Estado = COMPLETADO`

**Responsabilidades (cmd.storage):**
- Sin caras detectadas → cierra la solicitud directamente (`Estado = COMPLETADO`)

**Stack:** OpenCV · boto3 · confluent-kafka · psycopg2

---

### API-2 (Puerto 8001)

**Endpoints:**
- `GET /resultado/{guid}` — estado, tiempos de pipeline y presigned URLs de las imágenes

**Respuesta:**
```json
{
  "guid": "...",
  "estado": "COMPLETADO",
  "tiempos": {
    "inicio_solicitud": "...",
    "fin_solicitud": "...",
    "inicio_deteccion_caras": "...",
    "fin_deteccion_caras": "...",
    "inicio_edad": "...",
    "fin_edad": "...",
    "inicio_pixelado": "...",
    "fin_pixelado": "..."
  },
  "imagenes": {
    "original":  "http://localhost:9000/images-raw/...?...",
    "marcos":    "http://localhost:9000/images-processed/.../marcos.jpg?...",
    "terminada": "http://localhost:9000/images-processed/.../terminada.jpg?..."
  },
  "caras_detectadas": 5,
  "caras": [
    { "id_imagen": 1, "es_menor": true, "score": 0.96, "bbox": {"x":10,"y":20,"w":50,"h":60} }
  ]
}
```

**Stack:** FastAPI · boto3 · psycopg2

---

## Infraestructura

| Servicio   | Imagen                     | Puerto(s)  | Uso                             |
|------------|----------------------------|------------|---------------------------------|
| Kafka      | apache/kafka:4.2.0 (KRaft) | 9092       | Bus de eventos (sin Zookeeper)  |
| MinIO      | minio/minio                | 9000, 9001 | Almacenamiento de imágenes (S3) |
| PostgreSQL | postgres:15                | 5432       | Base de datos relacional        |
| Kafka UI   | provectuslabs/kafka-ui     | 8080       | Monitorización de tópicos       |

**Buckets MinIO:**
- `images-raw` — imágenes originales y crops de caras por cara detectada
- `images-processed` — imágenes finales (marcos y terminada); se crea automáticamente al arrancar Pixelation Service

---

## Base de datos (PostgreSQL)

### Tabla `Solicitud`

| Columna                           | Tipo       | Descripción                              |
|-----------------------------------|------------|------------------------------------------|
| `GUID_Solicitud`                  | VARCHAR PK | Identificador único de la solicitud      |
| `URL_Imagen_Original`             | VARCHAR    | Clave en MinIO de la imagen original     |
| `URL_Imagen_Terminada`            | VARCHAR    | Clave en MinIO de la imagen pixelada     |
| `URL_Imagen_Marcos`               | VARCHAR    | Clave en MinIO de la imagen con marcos   |
| `Inicio_Solicitud`                | TIMESTAMP  | Recepción en API-1                       |
| `Fin_Solicitud`                   | TIMESTAMP  | Cierre en Pixelation Service             |
| `Inicio_Deteccion_Caras`          | TIMESTAMP  | Publicación de cmd.face_detection        |
| `Fin_Deteccion_Caras`             | TIMESTAMP  | Fin de Detection Service                 |
| `Inicio_Edad`                     | TIMESTAMP  | Publicación de cmd.age_detection         |
| `Fin_edad`                        | TIMESTAMP  | Fin de Age Service                       |
| `Inicio_Pixelado`                 | TIMESTAMP  | Publicación de cmd.pixelation            |
| `Fin_Pixelado`                    | TIMESTAMP  | Fin de Pixelation Service                |
| `Inicio_Almacenamiento_Solicitud` | TIMESTAMP  | Inicio de guardado de resultado          |
| `Fin_Almacenamiento_Solicitud`    | TIMESTAMP  | Fin de guardado de resultado             |
| `Estado`                          | VARCHAR    | `INICIADO` → `COMPLETADO`               |

### Tabla `Imagenes`
Una fila por cara detectada (más una fila inicial de la imagen original creada en API-1).

| Columna          | Tipo       | Descripción                        |
|------------------|------------|------------------------------------|
| `GUID_Solicitud` | VARCHAR FK | Referencia a la solicitud          |
| `Id_Imagen`      | SERIAL PK  | Identificador de la cara           |
| `URL_Imagen`     | VARCHAR    | Clave del crop de la cara en MinIO |
| `Mayor_18`       | BOOLEAN    | `true` = mayor, `false` = menor    |
| `Escore`         | DECIMAL    | Score de la red neuronal [0, 1]    |
| `Imagen_X`       | INT        | Coordenada X del bounding box      |
| `Imagen_Y`       | INT        | Coordenada Y del bounding box      |
| `Imagen_Ancho`   | INT        | Ancho del bounding box             |
| `Imagen_Alto`    | INT        | Alto del bounding box              |

---

## Contratos de eventos

Definidos en `contratos_eventos_json/` como JSON Schema draft-07.

```
contratos_eventos_json/
├── comandos/
│   ├── cmd_face_detection.json
│   ├── cmd_age_detection.json
│   ├── cmd_pixelation.json
│   └── cmd_storage.json
└── eventos/
    ├── evt_face_detection_completed.json
    ├── evt_age_detection_completed.json
    ├── evt_pixelation_completed.json
    └── evt_storage_completed.json
```

---

## Entrenamiento del modelo de edad

El script `training/train_age.py` entrena la CNN básica (arquitectura propia, sin pesos externos).

**Opción A — Local con GPU (RTX 3080):**
```bash
bash scripts/train.sh
```
Requiere la carpeta `face_age/` en la raíz con subcarpetas numéricas por edad. El script entrena, copia el modelo a `services/age-service/` y reinicia el contenedor automáticamente.

**Opción B — Google Colab:**
1. Abrir `training/red_neuronal_proyecto_imagenes.ipynb` en Colab
2. Descargar el `.h5` generado y guardarlo en `training/modelo_menores.h5`
3. Ejecutar:
```bash
bash scripts/deploy_model.sh
```

El modelo actual (`val_accuracy ≈ 87.7 %`) fue entrenado con la CNN básica durante 28 epochs con GPU RTX 3080.

---

## Levantar el sistema

```bash
cp .env.example .env   # rellenar credenciales
docker compose up --build
```

> Los tópicos de Kafka se pre-crean al arranque mediante el servicio `kafka-init`. El bucket `images-processed` se crea automáticamente al arrancar Pixelation Service.

**URLs tras el arranque:**
- API-1: http://localhost:8000/docs
- API-2: http://localhost:8001/docs
- Kafka UI: http://localhost:8080
- MinIO Console: http://localhost:9001

**Subir una imagen de prueba:**
```bash
curl -X POST http://localhost:8000/upload -F "file=@prueba.jpg"
# {"GUID_Solicitud": "...", "Id_Imagen": 1, "status": "INICIADO"}
```

**Consultar el resultado:**
```bash
curl http://localhost:8001/resultado/{GUID_Solicitud}
```

---

## Estructura del repositorio

```
proyecto_rostros/
├── services/
│   ├── api-1/                  # Ingesta (fusiona O1)
│   ├── api-2/                  # Consulta de resultados
│   ├── age-service/            # Clasificación menor/mayor con TF
│   ├── detection-service/      # Detección de rostros (Haar Cascade)
│   ├── orchestrator-2/         # Cropea caras y enruta a age detection
│   ├── orchestrator-3/         # Enruta a pixelation
│   └── pixelation-service/     # Genera imágenes finales (fusiona O4)
│       └── (cada uno: main.py, config.py, services/, Dockerfile, requirements.txt)
├── infra/
│   └── postgres/
│       └── init.sql            # DDL de Solicitud e Imagenes
├── training/
│   ├── train_age.py            # Script de entrenamiento CNN
│   ├── Dockerfile              # Imagen de entrenamiento (TF GPU)
│   ├── modelo_menores.h5       # Modelo entrenado (no gitignored aquí)
│   └── red_neuronal_proyecto_imagenes.ipynb  # Experimentos Colab
├── contracts/
│   ├── comandos/               # JSON Schema de comandos Kafka
│   └── eventos/                # JSON Schema de eventos Kafka
├── scripts/
│   ├── train.sh                # Entrena con GPU y despliega
│   └── deploy_model.sh         # Despliega modelo externo (Colab)
├── docker-compose.yml
├── .env                        # Credenciales (no en git)
├── .env.example                # Plantilla de credenciales
├── .gitignore
└── README.md
```

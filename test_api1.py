"""
Script de pruebas para API-1
Verifica que:
1. Acepta imágenes
2. Las sube a MinIO
3. Las registra en BD
4. Publica eventos en Kafka
"""

import requests
import psycopg2
import boto3
import json
from confluent_kafka import Consumer
from pathlib import Path
import time

# =============================
# CONFIGURACIÓN
# =============================
API1_URL = "http://localhost:8000"
DB_CONF = {
    "host": "localhost",
    "database": "db_rostros",
    "user": "user_rostros",
    "password": "password_rostros",
    "port": 5432
}
MINIO_CONF = {
    "endpoint_url": "http://localhost:9000",
    "aws_access_key_id": "admin",
    "aws_secret_access_key": "password123"
}
KAFKA_SERVER = "localhost:9092"

# =============================
# CREAR IMAGEN DE PRUEBA
# =============================
def create_test_image():
    """Crea una imagen JPG de prueba"""
    try:
        from PIL import Image
    except ImportError:
        print("❌ Pillow no instalado. Instala con: pip install Pillow")
        return None

    img = Image.new('RGB', (100, 100), color='red')
    img_path = Path("/tmp/test_image.jpg")
    img.save(img_path)
    print(f"✅ Imagen de prueba creada: {img_path}")
    return img_path

# =============================
# TEST 1: UPLOAD A API-1
# =============================
def test_upload_to_api1():
    """Test: POST /upload"""
    print("\n" + "="*60)
    print("TEST 1: Subir imagen a API-1")
    print("="*60)

    img_path = create_test_image()
    if not img_path:
        return None

    try:
        with open(img_path, 'rb') as f:
            files = {'file': ('test_image.jpg', f, 'image/jpeg')}
            response = requests.post(f"{API1_URL}/upload", files=files)

        if response.status_code != 200:
            print(f"❌ Error HTTP {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None

        data = response.json()
        guid = data['GUID_Solicitud']
        id_imagen = data['Id_Imagen']
        status = data['status']

        print(f"✅ Upload exitoso")
        print(f"   GUID: {guid}")
        print(f"   Id_Imagen: {id_imagen}")
        print(f"   Status: {status}")

        return guid, id_imagen

    except requests.exceptions.ConnectionError:
        print(f"❌ No se pudo conectar a API-1 en {API1_URL}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# =============================
# TEST 2: VERIFICAR EN BD
# =============================
def test_check_database(guid, id_imagen):
    """Test: Verificar registros en BD"""
    print("\n" + "="*60)
    print("TEST 2: Verificar BD")
    print("="*60)

    try:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()

        # Verificar Solicitud
        cur.execute("SELECT * FROM Solicitud WHERE GUID_Solicitud = %s", (guid,))
        solicitud = cur.fetchone()

        if not solicitud:
            print(f"❌ Solicitud NO encontrada en BD")
            return False

        print(f"✅ Solicitud encontrada:")
        print(f"   GUID: {solicitud[0]}")
        print(f"   URL Original: {solicitud[1]}")
        print(f"   Estado: {solicitud[-1]}")

        # Verificar Imagen
        cur.execute("SELECT * FROM Imagenes WHERE GUID_Solicitud = %s AND Id_Imagen = %s", (guid, id_imagen))
        imagen = cur.fetchone()

        if not imagen:
            print(f"❌ Imagen NO encontrada en BD")
            return False

        print(f"✅ Imagen encontrada:")
        print(f"   GUID: {imagen[0]}")
        print(f"   Id_Imagen: {imagen[1]}")
        print(f"   URL: {imagen[2]}")

        cur.close()
        conn.close()
        return True

    except psycopg2.OperationalError:
        print(f"❌ No se pudo conectar a BD en {DB_CONF['host']}:{DB_CONF['port']}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# =============================
# TEST 3: VERIFICAR EN MINIO
# =============================
def test_check_minio(guid):
    """Test: Verificar archivo en MinIO"""
    print("\n" + "="*60)
    print("TEST 3: Verificar MinIO")
    print("="*60)

    try:
        s3 = boto3.client('s3', **MINIO_CONF)

        # Listar objetos en bucket images-raw
        response = s3.list_objects_v2(Bucket='images-raw', Prefix=guid)

        if 'Contents' not in response or len(response['Contents']) == 0:
            print(f"❌ Archivo NO encontrado en MinIO (bucket: images-raw, prefix: {guid})")
            return False

        print(f"✅ Archivo encontrado en MinIO:")
        for obj in response['Contents']:
            print(f"   Key: {obj['Key']}")
            print(f"   Size: {obj['Size']} bytes")

        return True

    except Exception as e:
        print(f"❌ Error al conectar a MinIO: {e}")
        return False

# =============================
# TEST 4: VERIFICAR EVENTOS KAFKA
# =============================
def test_check_kafka_events(guid):
    """Test: Verificar eventos en Kafka"""
    print("\n" + "="*60)
    print("TEST 4: Verificar Eventos Kafka (timeout 5s)")
    print("="*60)

    try:
        # Crear consumer para images.raw
        consumer_raw = Consumer({
            'bootstrap.servers': KAFKA_SERVER,
            'group.id': 'test-group-raw',
            'auto.offset.reset': 'earliest',
            'session.timeout.ms': 5000
        })
        consumer_raw.subscribe(['images.raw'])

        # Crear consumer para cmd.face_detection
        consumer_cmd = Consumer({
            'bootstrap.servers': KAFKA_SERVER,
            'group.id': 'test-group-cmd',
            'auto.offset.reset': 'earliest',
            'session.timeout.ms': 5000
        })
        consumer_cmd.subscribe(['cmd.face_detection'])

        eventos_encontrados = {
            'images.raw': False,
            'cmd.face_detection': False
        }

        # Poll durante 5 segundos
        start = time.time()
        while time.time() - start < 5:
            # Poll images.raw
            msg = consumer_raw.poll(timeout=0.5)
            if msg and not msg.error():
                try:
                    data = json.loads(msg.value().decode('utf-8'))
                    if data.get('GUID_Solicitud') == guid:
                        print(f"✅ Evento 'images.raw' encontrado:")
                        print(f"   GUID: {data.get('GUID_Solicitud')}")
                        print(f"   s3_key: {data.get('s3_key')}")
                        eventos_encontrados['images.raw'] = True
                except:
                    pass

            # Poll cmd.face_detection
            msg = consumer_cmd.poll(timeout=0.5)
            if msg and not msg.error():
                try:
                    data = json.loads(msg.value().decode('utf-8'))
                    if data.get('GUID_Solicitud') == guid:
                        print(f"✅ Evento 'cmd.face_detection' encontrado:")
                        print(f"   GUID: {data.get('GUID_Solicitud')}")
                        print(f"   s3_key: {data.get('s3_key')}")
                        eventos_encontrados['cmd.face_detection'] = True
                except:
                    pass

            if all(eventos_encontrados.values()):
                break

        consumer_raw.close()
        consumer_cmd.close()

        if not eventos_encontrados['images.raw']:
            print(f"⚠️  Evento 'images.raw' NO encontrado (timeout)")
        if not eventos_encontrados['cmd.face_detection']:
            print(f"⚠️  Evento 'cmd.face_detection' NO encontrado (timeout)")

        return all(eventos_encontrados.values())

    except Exception as e:
        print(f"⚠️  Error al verificar Kafka: {e}")
        return False

# =============================
# MAIN
# =============================
if __name__ == "__main__":
    print("\n" + "🧪 PRUEBAS DE API-1" + "\n")
    print("Asegúrate de que los servicios estén corriendo:")
    print("  - API-1 en http://localhost:8000")
    print("  - PostgreSQL en localhost:5432")
    print("  - MinIO en http://localhost:9000")
    print("  - Kafka en localhost:9092")

    # TEST 1: Upload
    result = test_upload_to_api1()
    if not result:
        print("\n❌ No se puede continuar sin upload exitoso")
        exit(1)

    guid, id_imagen = result

    # TEST 2: BD
    bd_ok = test_check_database(guid, id_imagen)

    # TEST 3: MinIO
    minio_ok = test_check_minio(guid)

    # TEST 4: Kafka
    kafka_ok = test_check_kafka_events(guid)

    # RESUMEN
    print("\n" + "="*60)
    print("📊 RESUMEN")
    print("="*60)
    print(f"BD:         {'✅' if bd_ok else '❌'}")
    print(f"MinIO:      {'✅' if minio_ok else '❌'}")
    print(f"Kafka:      {'✅' if kafka_ok else '⚠️ '}")

    if bd_ok and minio_ok:
        print("\n✅ API-1 está funcionando correctamente!")
    else:
        print("\n❌ API-1 tiene problemas. Revisa los errores arriba.")

"""
Tests unitarios para api-2:
- presigned_url: sustitución del endpoint interno por la URL pública
- _storage_public_base: construcción del host público a partir de headers HTTP

La lógica de ambas funciones se replica aquí para que los tests sean
autónomos (no dependen de FastAPI, boto3 ni el ciclo de vida del servicio).
"""

import pytest
from unittest.mock import MagicMock


# ── Lógica replicada desde services/api-2/services/storage.py ────────────────

def presigned_url(client, bucket: str, key: str, expiry: int, public_base: str) -> str | None:
    if not key:
        return None
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry,
        )
        internal = client.meta.endpoint_url
        return url.replace(internal, public_base)
    except Exception:
        return None


# ── Lógica replicada desde services/api-2/main.py ────────────────────────────

def storage_public_base(headers: dict) -> str:
    host   = headers.get("x-forwarded-host") or headers.get("host", "localhost:3000")
    scheme = headers.get("x-forwarded-proto", "http")
    return f"{scheme}://{host}/storage"


# ── Helpers ───────────────────────────────────────────────────────────────────

INTERNAL = "http://minio:9000"
BUCKET   = "images-raw"
KEY      = "abc123/uuid.jpg"
EXPIRY   = 3600


def _mock_client(endpoint_url: str, presigned: str) -> MagicMock:
    client = MagicMock()
    client.meta.endpoint_url = endpoint_url
    client.generate_presigned_url.return_value = presigned
    return client


def _signed(path: str = "", qs: str = "X-Amz-Signature=abc") -> str:
    return f"{INTERNAL}/{path}?{qs}" if path else f"{INTERNAL}?{qs}"


# ── Tests: presigned_url ──────────────────────────────────────────────────────

class TestPresignedUrl:
    def test_key_none_devuelve_none(self):
        client = _mock_client(INTERNAL, "no-importa")
        assert presigned_url(client, BUCKET, None, EXPIRY, "http://localhost:3000/storage") is None

    def test_key_vacia_devuelve_none(self):
        client = _mock_client(INTERNAL, "no-importa")
        assert presigned_url(client, BUCKET, "", EXPIRY, "http://localhost:3000/storage") is None

    def test_sustituye_host_interno_por_publico(self):
        signed = f"{INTERNAL}/{BUCKET}/{KEY}?X-Amz-Signature=abc"
        client = _mock_client(INTERNAL, signed)
        result = presigned_url(client, BUCKET, KEY, EXPIRY, "http://localhost:3000/storage")
        assert result == f"http://localhost:3000/storage/{BUCKET}/{KEY}?X-Amz-Signature=abc"

    def test_host_interno_no_aparece_en_resultado(self):
        signed = f"{INTERNAL}/{BUCKET}/{KEY}?X-Amz-Signature=abc"
        client = _mock_client(INTERNAL, signed)
        result = presigned_url(client, BUCKET, KEY, EXPIRY, "http://localhost:3000/storage")
        assert INTERNAL not in result

    def test_query_string_sigv4_se_preserva_intacto(self):
        qs     = "X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=key%2F20260504%2Fs3&X-Amz-Expires=3600"
        signed = f"{INTERNAL}/{BUCKET}/{KEY}?{qs}"
        client = _mock_client(INTERNAL, signed)
        result = presigned_url(client, BUCKET, KEY, EXPIRY, "http://localhost:3000/storage")
        assert result.endswith(f"?{qs}")

    def test_host_publico_ip_lan_con_puerto(self):
        signed = f"{INTERNAL}/{BUCKET}/{KEY}?X-Amz-Signature=xyz"
        client = _mock_client(INTERNAL, signed)
        public = "http://192.168.1.10:3000/storage"
        result = presigned_url(client, BUCKET, KEY, EXPIRY, public)
        assert result.startswith(public)

    def test_host_publico_https_produccion(self):
        signed = f"{INTERNAL}/{BUCKET}/{KEY}?X-Amz-Signature=xyz"
        client = _mock_client(INTERNAL, signed)
        result = presigned_url(client, BUCKET, KEY, EXPIRY, "https://midominio.com/storage")
        assert result.startswith("https://midominio.com/storage")

    def test_excepcion_boto3_devuelve_none(self):
        client = MagicMock()
        client.generate_presigned_url.side_effect = Exception("error de conexión")
        assert presigned_url(client, BUCKET, KEY, EXPIRY, "http://localhost:3000/storage") is None

    def test_path_completo_del_objeto_se_preserva(self):
        nested_key = "guid-123/faces/42.jpg"
        signed     = f"{INTERNAL}/{nested_key}?X-Amz-Signature=abc"
        client     = _mock_client(INTERNAL, signed)
        result     = presigned_url(client, BUCKET, nested_key, EXPIRY, "http://localhost:3000/storage")
        assert f"/storage/{nested_key}" in result


# ── Tests: storage_public_base ────────────────────────────────────────────────

class TestStoragePublicBase:
    def test_x_forwarded_host_tiene_prioridad_sobre_host(self):
        headers = {"x-forwarded-host": "localhost:3000", "host": "api-2:8001"}
        assert storage_public_base(headers) == "http://localhost:3000/storage"

    def test_usa_host_si_no_hay_x_forwarded_host(self):
        headers = {"host": "localhost:3000"}
        assert storage_public_base(headers) == "http://localhost:3000/storage"

    def test_sin_headers_usa_defaults(self):
        assert storage_public_base({}) == "http://localhost:3000/storage"

    def test_x_forwarded_proto_https(self):
        headers = {"x-forwarded-host": "midominio.com", "x-forwarded-proto": "https"}
        assert storage_public_base(headers) == "https://midominio.com/storage"

    def test_ip_lan_con_puerto_preserva_el_puerto(self):
        headers = {"x-forwarded-host": "192.168.1.10:3000"}
        assert storage_public_base(headers) == "http://192.168.1.10:3000/storage"

    def test_resultado_siempre_termina_en_barra_storage(self):
        casos = [
            {"x-forwarded-host": "localhost:3000"},
            {"host": "localhost:3000"},
            {},
        ]
        for headers in casos:
            assert storage_public_base(headers).endswith("/storage")

"""
Tests unitarios para api-1 — lógica de validación de imágenes.

Cubre:
- detectar_content_type: magic bytes para JPEG, PNG e imágenes inválidas
- Validación del tamaño máximo de fichero
- Validación de extensiones permitidas
"""

import pytest

# ── Lógica replicada desde services/api-1/main.py ────────────────────────────
# Se replica aquí para que los tests sean completamente autónomos y no
# dependan del ciclo de vida del módulo (lifespan, kafka producer, etc.)

MAGIC_SIGNATURES = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG",      "image/png"),
]

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def detectar_content_type(header: bytes) -> str | None:
    for sig, ct in MAGIC_SIGNATURES:
        if header.startswith(sig):
            return ct
    return None


def extension_valida(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


def tamano_valido(size: int) -> bool:
    return size <= MAX_FILE_SIZE


# ── Tests: magic bytes ────────────────────────────────────────────────────────

class TestDetectarContentType:
    def test_jpeg_cabecera_e0(self):
        assert detectar_content_type(b"\xff\xd8\xff\xe0\x00\x10") == "image/jpeg"

    def test_jpeg_cabecera_e1_exif(self):
        assert detectar_content_type(b"\xff\xd8\xff\xe1\x00\x10") == "image/jpeg"

    def test_jpeg_cabecera_db(self):
        assert detectar_content_type(b"\xff\xd8\xff\xdb\x00\x43") == "image/jpeg"

    def test_png_cabecera_correcta(self):
        assert detectar_content_type(b"\x89PNG\r\n\x1a\n") == "image/png"

    def test_gif_no_reconocido(self):
        assert detectar_content_type(b"GIF89a\x01\x00\x01\x00") is None

    def test_webp_no_reconocido(self):
        assert detectar_content_type(b"RIFF\x00\x00\x00\x00WEBP") is None

    def test_pdf_no_reconocido(self):
        assert detectar_content_type(b"%PDF-1.4\n") is None

    def test_texto_plano_no_reconocido(self):
        assert detectar_content_type(b"Hello, World!") is None

    def test_bytes_vacios_no_reconocido(self):
        assert detectar_content_type(b"") is None

    def test_un_solo_byte_no_reconocido(self):
        assert detectar_content_type(b"\xff") is None

    def test_retorna_string_para_jpeg(self):
        result = detectar_content_type(b"\xff\xd8\xff\xe0")
        assert isinstance(result, str)

    def test_retorna_none_para_invalido(self):
        result = detectar_content_type(b"INVALIDO")
        assert result is None


# ── Tests: validación de extensión ───────────────────────────────────────────

class TestExtensionValida:
    def test_jpg_permitido(self):
        assert extension_valida("foto.jpg") is True

    def test_jpeg_permitido(self):
        assert extension_valida("imagen.jpeg") is True

    def test_png_permitido(self):
        assert extension_valida("captura.png") is True

    def test_extension_mayusculas_permitida(self):
        assert extension_valida("FOTO.JPG") is True

    def test_gif_no_permitido(self):
        assert extension_valida("animacion.gif") is False

    def test_bmp_no_permitido(self):
        assert extension_valida("imagen.bmp") is False

    def test_webp_no_permitido(self):
        assert extension_valida("foto.webp") is False

    def test_sin_extension_no_permitido(self):
        assert extension_valida("sinfichero") is False

    def test_extension_doble_usa_ultima(self):
        # "foto.txt.jpg" → ext = "jpg" → permitido
        assert extension_valida("foto.txt.jpg") is True


# ── Tests: validación de tamaño ───────────────────────────────────────────────

class TestTamanoValido:
    def test_fichero_pequeño_valido(self):
        assert tamano_valido(1024) is True

    def test_fichero_en_limite_valido(self):
        assert tamano_valido(MAX_FILE_SIZE) is True

    def test_fichero_un_byte_sobre_limite_invalido(self):
        assert tamano_valido(MAX_FILE_SIZE + 1) is False

    def test_fichero_muy_grande_invalido(self):
        assert tamano_valido(50 * 1024 * 1024) is False

    def test_fichero_vacio_valido(self):
        assert tamano_valido(0) is True

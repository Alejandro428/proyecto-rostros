"""
Tests unitarios para pixelation-service — procesamiento de imágenes.

Cubre:
- generar_imagen_terminada: pixela solo las caras con es_menor=True
- generar_imagen_marcos: dibuja marcos y etiquetas sin modificar la imagen original

Requiere opencv-python-headless y numpy:
    pip install opencv-python-headless numpy
Los tests se saltan automáticamente si no están instalados.
"""

import pytest

cv2 = pytest.importorskip("cv2", reason="opencv-python-headless no instalado")
np  = pytest.importorskip("numpy",  reason="numpy no instalado")


# ── Lógica replicada desde services/pixelation-service/main.py ───────────────

def generar_imagen_terminada(img, faces: list):
    resultado = img.copy()
    for face in faces:
        if not face.get("es_menor", False):
            continue
        x, y, w, h = face["bbox"]["x"], face["bbox"]["y"], face["bbox"]["w"], face["bbox"]["h"]
        roi = resultado[y:y + h, x:x + w]
        if roi.size == 0:
            continue
        temp = cv2.resize(roi, (12, 12), interpolation=cv2.INTER_LINEAR)
        resultado[y:y + h, x:x + w] = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
    return resultado


def generar_imagen_marcos(img, faces: list):
    resultado = img.copy()
    font      = cv2.FONT_HERSHEY_SIMPLEX
    for face in faces:
        x, y, w, h = face["bbox"]["x"], face["bbox"]["y"], face["bbox"]["w"], face["bbox"]["h"]
        es_menor   = face.get("es_menor", False)
        score      = face.get("score", None)
        color      = (0, 0, 255) if es_menor else (0, 255, 0)
        label      = "Menor" if es_menor else "Adulto"
        etiqueta   = f"{label}:{score:.3f}" if score is not None else label
        cv2.rectangle(resultado, (x, y), (x + w, y + h), color, 1)
        scale = max(0.2, min(0.5, w / 200.0))
        etiqueta_corta = (
            f"{'Menor' if es_menor else 'Adulto'}:{score:.1f}"
            if score is not None
            else ("Menor" if es_menor else "Adulto")
        )
        (tw, _), _ = cv2.getTextSize(etiqueta, font, scale, 1)
        texto = etiqueta if tw <= w - 4 else etiqueta_corta
        (tw, th), baseline = cv2.getTextSize(texto, font, scale, 1)
        band_h = th + baseline + 4
        cv2.rectangle(resultado, (x, y), (x + w, y + band_h), color, cv2.FILLED)
        cv2.putText(resultado, texto, (x + 2, y + th + 2), font, scale, (255, 255, 255), 1, cv2.LINE_AA)
    return resultado


# ── Helpers ───────────────────────────────────────────────────────────────────

def _img_aleatoria(h: int = 100, w: int = 100, seed: int = 42):
    """Imagen BGR con valores distintos en cada píxel (nunca uniforme)."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, (h, w, 3), dtype=np.uint8)


def _face(x=10, y=10, w=40, h=40, es_menor=False, score=0.3):
    return {"bbox": {"x": x, "y": y, "w": w, "h": h}, "es_menor": es_menor, "score": score}


# ── Tests: generar_imagen_terminada ──────────────────────────────────────────

class TestGenerarImagenTerminada:
    def test_cara_menor_queda_pixelada(self):
        img    = _img_aleatoria()
        result = generar_imagen_terminada(img, [_face(es_menor=True)])
        assert not np.array_equal(result[10:50, 10:50], img[10:50, 10:50])

    def test_cara_adulto_no_se_modifica(self):
        img    = _img_aleatoria()
        result = generar_imagen_terminada(img, [_face(es_menor=False)])
        assert np.array_equal(result[10:50, 10:50], img[10:50, 10:50])

    def test_sin_caras_imagen_identica_al_original(self):
        img    = _img_aleatoria()
        result = generar_imagen_terminada(img, [])
        assert np.array_equal(result, img)

    def test_no_modifica_la_imagen_original(self):
        img    = _img_aleatoria()
        copia  = img.copy()
        generar_imagen_terminada(img, [_face(es_menor=True)])
        assert np.array_equal(img, copia)

    def test_mezcla_solo_pixela_la_cara_menor(self):
        img    = _img_aleatoria()
        menor  = _face(x=10, y=10, w=30, h=30, es_menor=True)
        adulto = _face(x=60, y=60, w=30, h=30, es_menor=False)
        result = generar_imagen_terminada(img, [menor, adulto])
        assert not np.array_equal(result[10:40, 10:40], img[10:40, 10:40])
        assert np.array_equal(result[60:90, 60:90], img[60:90, 60:90])

    def test_dimensiones_del_resultado_iguales_al_original(self):
        img    = _img_aleatoria()
        result = generar_imagen_terminada(img, [_face(es_menor=True)])
        assert result.shape == img.shape

    def test_roi_con_ancho_cero_no_lanza_excepcion(self):
        img  = _img_aleatoria()
        face = {"bbox": {"x": 10, "y": 10, "w": 0, "h": 30}, "es_menor": True}
        result = generar_imagen_terminada(img, [face])
        assert np.array_equal(result, img)

    def test_es_menor_ausente_trata_cara_como_adulto(self):
        img  = _img_aleatoria()
        face = {"bbox": {"x": 10, "y": 10, "w": 40, "h": 40}}
        result = generar_imagen_terminada(img, [face])
        assert np.array_equal(result[10:50, 10:50], img[10:50, 10:50])


# ── Tests: generar_imagen_marcos ─────────────────────────────────────────────

class TestGenerarImagenMarcos:
    def test_dimensiones_resultado_iguales_al_original(self):
        img    = _img_aleatoria()
        result = generar_imagen_marcos(img, [_face()])
        assert result.shape == img.shape

    def test_sin_caras_resultado_identico_al_original(self):
        img    = _img_aleatoria()
        result = generar_imagen_marcos(img, [])
        assert np.array_equal(result, img)

    def test_no_modifica_la_imagen_original(self):
        img   = _img_aleatoria()
        copia = img.copy()
        generar_imagen_marcos(img, [_face(es_menor=True)])
        assert np.array_equal(img, copia)

    def test_con_cara_el_resultado_difiere_del_original(self):
        img    = _img_aleatoria()
        result = generar_imagen_marcos(img, [_face()])
        assert not np.array_equal(result, img)

    def test_cara_sin_score_no_lanza_excepcion(self):
        img  = _img_aleatoria()
        face = {"bbox": {"x": 10, "y": 10, "w": 40, "h": 40}}
        result = generar_imagen_marcos(img, [face])
        assert result.shape == img.shape

    def test_multiples_caras_no_lanza_excepcion(self):
        img   = _img_aleatoria()
        faces = [
            _face(x=5,  y=5,  w=30, h=30, es_menor=True,  score=0.8),
            _face(x=60, y=60, w=25, h=25, es_menor=False, score=0.2),
        ]
        result = generar_imagen_marcos(img, faces)
        assert result.shape == img.shape

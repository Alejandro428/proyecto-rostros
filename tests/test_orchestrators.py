"""
Tests unitarios para orchestrator-2 y orchestrator-3 — lógica de enrutamiento.

Cubre:
- Orchestrator-2: decisión cmd.age_detection vs cmd.storage según si hay caras
- Orchestrator-3: decisión cmd.pixelation vs cmd.storage según si hay menores
"""

import pytest

# ── Lógica replicada desde services/orchestrator-2/main.py ───────────────────

TOPIC_AGE_DETECTION = "cmd.age_detection"
TOPIC_STORAGE       = "cmd.storage"
TOPIC_PIXELATION    = "cmd.pixelation"


def orch2_siguiente_topic(faces_payload: list) -> str:
    """Decide el topic destino según si el pipeline tiene caras procesadas."""
    return TOPIC_AGE_DETECTION if faces_payload else TOPIC_STORAGE


# ── Lógica replicada desde services/orchestrator-3/main.py ───────────────────

def orch3_hay_menores(faces: list) -> bool:
    """Comprueba si alguna cara en el evento tiene es_menor=True."""
    return any(f.get("es_menor") for f in faces)


def orch3_siguiente_topic(faces: list) -> str:
    """Decide el topic destino según si hay menores en las caras clasificadas."""
    return TOPIC_PIXELATION if orch3_hay_menores(faces) else TOPIC_STORAGE


# ── Tests: Orchestrator-2 ─────────────────────────────────────────────────────

class TestOrchestrator2Routing:
    def test_con_caras_envia_a_age_detection(self):
        faces = [{"face_id": 1, "bbox": {"x": 10, "y": 10, "w": 30, "h": 30}}]
        assert orch2_siguiente_topic(faces) == TOPIC_AGE_DETECTION

    def test_sin_caras_envia_a_storage(self):
        assert orch2_siguiente_topic([]) == TOPIC_STORAGE

    def test_multiples_caras_envia_a_age_detection(self):
        faces = [
            {"face_id": 1, "bbox": {"x": 10, "y": 10, "w": 30, "h": 30}},
            {"face_id": 2, "bbox": {"x": 60, "y": 10, "w": 25, "h": 25}},
        ]
        assert orch2_siguiente_topic(faces) == TOPIC_AGE_DETECTION

    def test_una_cara_envia_a_age_detection(self):
        faces = [{"face_id": 1, "bbox": {"x": 5, "y": 5, "w": 20, "h": 20}}]
        assert orch2_siguiente_topic(faces) == TOPIC_AGE_DETECTION


# ── Tests: Orchestrator-3 — detección de menores ─────────────────────────────

class TestOrchestrator3HayMenores:
    def test_sin_caras_no_hay_menores(self):
        assert orch3_hay_menores([]) is False

    def test_todos_adultos_no_hay_menores(self):
        faces = [
            {"face_id": 1, "es_menor": False, "score": 0.1},
            {"face_id": 2, "es_menor": False, "score": 0.2},
        ]
        assert orch3_hay_menores(faces) is False

    def test_un_menor_hay_menores(self):
        faces = [{"face_id": 1, "es_menor": True, "score": 0.8}]
        assert orch3_hay_menores(faces) is True

    def test_menor_entre_adultos_hay_menores(self):
        faces = [
            {"face_id": 1, "es_menor": False, "score": 0.1},
            {"face_id": 2, "es_menor": True,  "score": 0.9},
            {"face_id": 3, "es_menor": False, "score": 0.2},
        ]
        assert orch3_hay_menores(faces) is True

    def test_todos_menores_hay_menores(self):
        faces = [
            {"face_id": 1, "es_menor": True, "score": 0.7},
            {"face_id": 2, "es_menor": True, "score": 0.8},
        ]
        assert orch3_hay_menores(faces) is True

    def test_es_menor_faltante_trata_como_adulto(self):
        # face sin clave es_menor → get devuelve None → falsy
        faces = [{"face_id": 1, "score": 0.5}]
        assert orch3_hay_menores(faces) is False


# ── Tests: Orchestrator-3 — routing ──────────────────────────────────────────

class TestOrchestrator3Routing:
    def test_hay_menores_envia_a_pixelation(self):
        faces = [{"face_id": 1, "es_menor": True, "score": 0.8}]
        assert orch3_siguiente_topic(faces) == TOPIC_PIXELATION

    def test_sin_menores_envia_a_storage(self):
        faces = [{"face_id": 1, "es_menor": False, "score": 0.1}]
        assert orch3_siguiente_topic(faces) == TOPIC_STORAGE

    def test_sin_caras_envia_a_storage(self):
        assert orch3_siguiente_topic([]) == TOPIC_STORAGE

    def test_un_menor_entre_varios_adultos_envia_a_pixelation(self):
        faces = [
            {"face_id": 1, "es_menor": False, "score": 0.2},
            {"face_id": 2, "es_menor": True,  "score": 0.6},
        ]
        assert orch3_siguiente_topic(faces) == TOPIC_PIXELATION

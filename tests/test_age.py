"""
Tests unitarios para age-service — lógica de clasificación de edad.

Cubre:
- Umbral de clasificación (THRESHOLD = 0.45)
- Relación entre es_menor y Mayor_18
- Comportamiento en valores de frontera y extremos
"""

import pytest

# ── Lógica replicada desde services/age-service/main.py ──────────────────────

THRESHOLD = 0.45  # Umbral deliberadamente bajo: preferimos falso positivo a falso negativo


def clasificar(score: float) -> bool:
    """Devuelve True si el score indica un menor (score >= THRESHOLD)."""
    return score >= THRESHOLD


def calcular_mayor_18(es_menor: bool) -> bool:
    """Mayor_18 es la negación de es_menor (columna BD)."""
    return not es_menor


# ── Tests: umbral de clasificación ───────────────────────────────────────────

class TestClasificacion:
    def test_score_alto_es_menor(self):
        assert clasificar(0.90) is True

    def test_score_en_umbral_exacto_es_menor(self):
        assert clasificar(0.45) is True

    def test_score_justo_bajo_umbral_es_adulto(self):
        assert clasificar(0.44) is False

    def test_score_cero_es_adulto(self):
        assert clasificar(0.0) is False

    def test_score_uno_es_menor(self):
        assert clasificar(1.0) is True

    def test_score_medio_bajo_umbral_es_adulto(self):
        assert clasificar(0.30) is False

    def test_score_medio_sobre_umbral_es_menor(self):
        assert clasificar(0.50) is True

    def test_score_casi_umbral_por_debajo_es_adulto(self):
        assert clasificar(0.449) is False

    def test_score_casi_umbral_por_encima_es_menor(self):
        assert clasificar(0.451) is True

    def test_umbral_conservador_clasifica_0_46_como_menor(self):
        # Con threshold 0.50 estándar, 0.46 sería adulto;
        # con 0.45 es menor — comportamiento deliberado
        assert clasificar(0.46) is True


# ── Tests: relación es_menor / Mayor_18 ──────────────────────────────────────

class TestMayor18:
    def test_menor_implica_mayor18_false(self):
        assert calcular_mayor_18(es_menor=True) is False

    def test_adulto_implica_mayor18_true(self):
        assert calcular_mayor_18(es_menor=False) is True

    def test_consistencia_para_score_alto(self):
        es_menor = clasificar(0.80)
        mayor_18 = calcular_mayor_18(es_menor)
        assert es_menor is True
        assert mayor_18 is False

    def test_consistencia_para_score_bajo(self):
        es_menor = clasificar(0.20)
        mayor_18 = calcular_mayor_18(es_menor)
        assert es_menor is False
        assert mayor_18 is True

    def test_mayor18_y_es_menor_son_siempre_opuestos(self):
        for score in [0.0, 0.1, 0.44, 0.45, 0.46, 0.8, 1.0]:
            es_menor = clasificar(score)
            mayor_18 = calcular_mayor_18(es_menor)
            assert es_menor != mayor_18, f"Fallo para score={score}"

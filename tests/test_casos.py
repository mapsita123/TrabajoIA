"""Suite automática: ejecuta los mismos casos de la página de Validación y comprueba reproducibilidad."""
import numpy as np
import pytest

from core import casos_prueba as cp, evolutivo, teoria_juegos


@pytest.fixture(scope="session")
def resultado_ee():
    return evolutivo.entrenar()


def _fallidos(casos):
    return [f"{c['grupo']} · {c['caso']}: esperado {c['esperado']}, obtenido {c['obtenido']}" for c in casos if not c["ok"]]


def test_logica_difusa():
    assert _fallidos(cp.casos_difuso()) == []


def test_flujo_integrado(resultado_ee):
    assert _fallidos(cp.casos_integracion(resultado_ee["modelo"])) == []


def test_sistema_experto_presets():
    casos = cp.casos_sistema_experto()
    assert _fallidos(casos) == []
    # La única discrepancia conocida del archivo original es el Caso 4.
    assert [c["caso"] for c in casos if c["nota"]] == ["Caso 4 · Revisión manual"]


def test_busqueda():
    assert _fallidos(cp.casos_busqueda()) == []


def test_juego_brecha():
    assert _fallidos(cp.casos_juego()) == []


def test_estrategia_evolutiva_reproduce_notebook(resultado_ee):
    assert _fallidos(cp.casos_evolutivo(resultado_ee, True)) == []


def test_score_ee_no_bloquea_lo_que_el_se_aprueba(resultado_ee):
    tabla = cp.consistencia_ee_vs_se(resultado_ee["modelo"])
    assert tabla.get(("Continúa", "Alerta"), 0) == 0


def test_teoria_juegos_reproduce_notebook_v2():
    defensores, atacantes, historial = teoria_juegos.coevolucionar()
    mejor = max(defensores, key=lambda d: d["fitness"])
    assert round(mejor["umbral"], 3) == 0.193
    assert np.isclose(historial[-1]["pago_atk"], 1.058, atol=5e-4)
    assert np.isclose(historial[-1]["umbral_def"], 0.233, atol=5e-4)

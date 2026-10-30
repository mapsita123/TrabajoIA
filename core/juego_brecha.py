"""
Juego "Brecha Nequi" (última entrega) — lógica exacta portada a Python.

Fuente: assets/brecha_nequi.html (copia sin cambios de "Brecha Nequi.html").
El juego se ejecuta en el navegador; este módulo reproduce sus cálculos
EXACTOS (enumeración de las 2⁸ combinaciones de señales, sin simulación) para
que las explicaciones de la página muestren lo mismo que el juego calcula.

Parámetros del juego (constantes del HTML, tomadas del notebook v3):
  NB = mejor defensor de la sección 7 del notebook v3 (pesos F2–F9 + F10, umbral 0.254)
  A2/B2 = matriz 2×2 de la sección 12 (pago de Nequi ×1000 y pago del ninja)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

RUTA_HTML = Path(__file__).resolve().parent.parent / "assets" / "brecha_nequi.html"

P_LEGIT_CTRL, P_LEGIT_F10, P_F10 = 0.04, 0.05, 0.40
PREV, V0, BEN, CFP = 0.02, 1.0, 0.6, 0.15
NB = {"pesos": [0.433, 0.318, 0.376, 0.356, 0.518, 0.352, 0.421, 0.388, 0.947], "umbral": 0.254}
UMBRAL_ESTRICTO, UMBRAL_LAXO = 0.15, 0.40
ESTILOS = {"Sigiloso": 0.0, "Moderado": 0.15, "Agresivo": 0.30}

PODERES = ["Biometría falsa", "Dispositivo fantasma", "Ráfaga de velocidad", "Clon de dispositivo", "Lista negra",
           "Correo desechable", "Salto de frontera", "Fuerza bruta OTP", "IP envenenada"]
SEÑALES = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9"]

A2 = np.array([[-22.26, -29.82], [-34.89, -26.41]])   # Nequi ×1000 · filas ESTRICTO, LAXO · columnas AGRESIVO, SIGILOSO
B2 = np.array([[0.223, 0.601], [1.432, 1.000]])       # ninja

MISIONES = {
    "m1": "1 · El precio de cada poder",
    "m2": "2 · El umbral de Nequi",
    "m3": "3 · El Guardián aprende",
    "m4": "4 · Duelo simultáneo",
    "m5": "Cuaderno de conceptos",
}


def html_juego(mision_inicial: str = "m1", reinicio: int = 0) -> str:
    """
    Devuelve el HTML original con una única adaptación: la misión inicial
    se puede fijar desde Streamlit (el original la leía de location.hash,
    que no existe dentro del iframe). El contador de reinicio fuerza a
    Streamlit a recrear el iframe con una partida nueva.
    """
    if mision_inicial not in MISIONES:
        raise ValueError("Misión desconocida.")
    html = RUTA_HTML.read_text(encoding="utf-8")
    original = "const h0=(location.hash||'').replace('#','');"
    if original not in html:
        raise RuntimeError("El HTML del juego cambió: no se encontró el punto de inicio de misión.")
    html = html.replace(original, f"const h0=(window.__mision||location.hash||'').replace('#','');")
    return html.replace("<head>", f"<head><script>window.__mision='{mision_inicial}';/*partida {reinicio}*/</script>", 1)


# ---------------------------------------------------------- cálculo exacto ---
def p_exacto(pesos, umbral, pc, pf10, pf1):
    """Probabilidad de bloqueo y botín esperado enumerando las 256 combinaciones de F2–F9 (pExacto del juego)."""
    w = list(pesos)
    thr = umbral * sum(w)
    pasa = botin = 0.0
    for m in range(256):
        k = 0
        s = 0.0
        pr = 1.0
        for b in range(8):
            if (m >> b) & 1:
                pr *= pc
                k += 1
                s += w[b]
            else:
                pr *= 1 - pc
        if pr == 0:
            continue
        for g in (0, 1):
            pg = pf10 if g else 1 - pf10
            if pg == 0:
                continue
            if s + (w[8] if g else 0) <= thr:
                pasa += pr * pg
                botin += pr * pg * (V0 + BEN * k)
    return {"bloqueo": 1 - pasa * (1 - pf1), "robado": botin * (1 - pf1)}


def costo_exacto(umbral, pc, pesos=None):
    """Costo esperado de Nequi por transacción contra un ninja que activa cada señal con probabilidad pc."""
    pesos = pesos or NB["pesos"]
    fr = p_exacto(pesos, umbral, pc, P_F10, 0)
    lg = p_exacto(pesos, umbral, P_LEGIT_CTRL, P_LEGIT_F10, P_LEGIT_CTRL)
    pf = PREV * fr["robado"]
    pp = (1 - PREV) * CFP * lg["bloqueo"]
    return {"recall": fr["bloqueo"], "fpr": lg["bloqueo"], "robado": fr["robado"],
            "costo_fraude": pf, "costo_clientes": pp, "costo": pf + pp}


def curva_costo(pc, desde=0.05, hasta=0.70, paso=0.005):
    us = np.round(np.arange(desde, hasta + 1e-9, paso), 4)
    cs = [costo_exacto(float(u), pc)["costo"] for u in us]
    i = int(np.argmin(cs))
    return us, np.array(cs), {"umbral": float(us[i]), "costo": float(cs[i])}


def combinaciones_ninja(pesos=None, umbral=None):
    """
    Misión 1: botín esperado de cada una de las 256 combinaciones de señales F2–F9
    contra el Guardián (F10 aparece con probabilidad 0.40 y no se controla).
    """
    pesos = pesos or NB["pesos"]
    umbral = NB["umbral"] if umbral is None else umbral
    thr = umbral * sum(pesos)
    filas = []
    for m in range(256):
        idx = [b for b in range(8) if (m >> b) & 1]
        s = sum(pesos[b] for b in idx)
        v = V0 + BEN * len(idx)
        sin_f10 = s <= thr
        con_f10 = s + pesos[8] <= thr
        ev = (1 - P_F10) * (v if sin_f10 else 0) + P_F10 * (v if con_f10 else 0)
        filas.append({"señales": " + ".join(SEÑALES[b + 1] for b in idx) or "ninguna", "n_señales": len(idx),
                      "puntaje_sin_F10": s / sum(pesos), "pasa_sin_F10": sin_f10, "pasa_con_F10": con_f10,
                      "valor_golpe": v, "botin_esperado": ev})
    return filas


def mejor_combinacion(filas=None):
    filas = filas or combinaciones_ninja()
    return max(filas, key=lambda f: f["botin_esperado"])


def equilibrio_inspeccion(A=A2, B=B2):
    """Equilibrio mixto por indiferencia del 2×2 del juego (misión 4)."""
    q = (A[1, 1] - A[0, 1]) / (A[0, 0] - A[0, 1] - A[1, 0] + A[1, 1])
    p = (B[1, 1] - B[1, 0]) / (B[0, 0] - B[1, 0] - B[0, 1] + B[1, 1])
    mejor_def = [int(np.argmax(A[:, j])) for j in range(2)]   # por columna del ninja
    mejor_atk = [int(np.argmax(B[i, :])) for i in range(2)]   # por fila de Nequi
    puros = [(i, j) for i in range(2) for j in range(2) if mejor_def[j] == i and mejor_atk[i] == j]
    pago_ninja = p * B[0, 0] + (1 - p) * B[1, 0]
    pago_nequi = q * A[0, 0] + (1 - q) * A[0, 1]
    return {"p_estricto": float(p), "q_agresivo": float(q), "puros": puros,
            "mejor_def": mejor_def, "mejor_atk": mejor_atk,
            "pago_ninja": float(pago_ninja), "pago_nequi_x1000": float(pago_nequi)}

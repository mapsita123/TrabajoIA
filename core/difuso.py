"""
Sprint 4 · Lógica difusa — capa Mamdani de riesgo crediticio.

Motor: las funciones trimf/trapmf, la inferencia Mamdani (Y = mínimo,
implicación por recorte, agregación por máximo) y la defuzzificación por
centroide son las del notebook de clase "09_Logica_Difusa_Mercado_Libre".
Los conjuntos de SALIDA (bajo/medio/alto en 0–100) también son los del notebook.

Variables de ENTRADA: las tres variables numéricas del motor de crédito del
sistema experto cuyos umbrales rígidos generan el efecto "599 rechaza, 600
aprueba":
  - score_datacredito   (C1 < 600 rechazo, C8 >= 750 favorable)
  - carga de la cuota   = cuota / ingresos (C2 > 0.35 rechazo, C9 <= 0.20 favorable)
  - DTI                 = deuda total / ingresos (C4 > 0.70 rechazo)

Regla de anclaje: cada umbral del sistema experto es el punto de cruce
(μ = 0.5) entre dos conjuntos vecinos, así que la frontera rígida se conserva
como el centro de la transición difusa.

DECISIONES DE MODELADO (no vienen de los archivos y se declaran como tales;
todas son editables desde la UI):
  - Ancho de la transición alrededor de cada umbral: ±50 pts de score,
    ±0.05 de carga de cuota, ±0.10 de DTI.
  - Universo del score: 150–950 (rango de referencia del score de centrales
    de riesgo en Colombia; el sistema experto no fija un rango).
  - Universos de carga y DTI: 0–1; un valor mayor se satura en 1 porque ya
    pertenece por completo al conjunto "excedida"/"excesivo".
"""
from __future__ import annotations

import numpy as np

# --------------------------------------------------- funciones de pertenencia ---
def trimf(x, a, b, c):
    """Función triangular con parámetros ordenados a <= b <= c (notebook de clase)."""
    if not (a <= b <= c):
        raise ValueError("La función triangular requiere a <= b <= c.")
    x = np.asarray(x, dtype=float)
    izq = (x - a) / (b - a) if b != a else np.where(x >= a, 1.0, 0.0)
    der = (c - x) / (c - b) if c != b else np.where(x <= c, 1.0, 0.0)
    return np.clip(np.minimum(izq, der), 0.0, 1.0)


def trapmf(x, a, b, c, d):
    """Función trapezoidal con parámetros ordenados a <= b <= c <= d (notebook de clase)."""
    if not (a <= b <= c <= d):
        raise ValueError("La función trapezoidal requiere a <= b <= c <= d.")
    x = np.asarray(x, dtype=float)
    subida = (x - a) / (b - a) if b != a else np.where(x >= a, 1.0, 0.0)
    bajada = (d - x) / (d - c) if d != c else np.where(x <= d, 1.0, 0.0)
    return np.clip(np.minimum(np.minimum(subida, 1.0), bajada), 0.0, 1.0)


FUNCIONES = {"trimf": trimf, "trapmf": trapmf}

# -------------------------------------------------------------- configuración ---
# Anchos de transición (semiancho alrededor de cada umbral). DECISIÓN DE MODELADO.
ANCHOS_BASE = {"score": 50.0, "carga": 0.05, "dti": 0.10}
UNIVERSO_SCORE = (150.0, 950.0)


def construir_config(umbrales: dict | None = None, anchos: dict | None = None) -> dict:
    """
    Genera los conjuntos difusos a partir de los umbrales del sistema experto.
    Cada umbral queda como punto de cruce μ = 0.5 entre dos conjuntos vecinos.
    umbrales: claves C1, C2, C4, C8, C9 (por defecto, los del Sprint 2).
    """
    from core.sistema_experto import DEFAULT_PARAMS
    u = {k: float(v) for k, v in {**DEFAULT_PARAMS, **(umbrales or {})}.items()}
    w = {**ANCHOS_BASE, **(anchos or {})}
    lo_s, hi_s = UNIVERSO_SCORE
    ws, wc, wd = w["score"], w["carga"], w["dti"]
    return {
        "variables": {
            "score": {
                "nombre": "Score de centrales de riesgo", "unidad": "puntos", "universo": UNIVERSO_SCORE,
                "fuente": f"score_datacredito · reglas C1 ({u['C1']:g}) y C8 ({u['C8']:g})",
                "conjuntos": {"bajo": ("trapmf", (lo_s, lo_s, u["C1"] - ws, u["C1"] + ws)),
                              "medio": ("trapmf", (u["C1"] - ws, u["C1"] + ws, u["C8"] - ws, u["C8"] + ws)),
                              "alto": ("trapmf", (u["C8"] - ws, u["C8"] + ws, hi_s, hi_s))},
            },
            "carga": {
                "nombre": "Carga de la cuota (cuota / ingresos)", "unidad": "proporción", "universo": (0.0, 1.0),
                "fuente": f"monto_cuota_solicitada / ingresos_mensuales · C9 ({u['C9']:g}) y C2 ({u['C2']:g})",
                "conjuntos": {"holgada": ("trapmf", (0.0, 0.0, u["C9"] - wc, u["C9"] + wc)),
                              "moderada": ("trapmf", (u["C9"] - wc, u["C9"] + wc, u["C2"] - wc, u["C2"] + wc)),
                              "excedida": ("trapmf", (u["C2"] - wc, u["C2"] + wc, 1.0, 1.0))},
            },
            "dti": {
                "nombre": "Endeudamiento total (DTI)", "unidad": "proporción", "universo": (0.0, 1.0),
                "fuente": f"deuda_total_mensual / ingresos_mensuales · C4 ({u['C4']:g})",
                "conjuntos": {"aceptable": ("trapmf", (0.0, 0.0, u["C4"] - wd, u["C4"] + wd)),
                              "excesivo": ("trapmf", (u["C4"] - wd, u["C4"] + wd, 1.0, 1.0))},
            },
        },
        # Conjuntos de salida: los mismos del notebook de lógica difusa de clase.
        "salida": {
            "nombre": "Riesgo crediticio", "unidad": "0–100", "universo": (0.0, 100.0),
            "conjuntos": {"bajo": ("trapmf", (0, 0, 20, 40)),
                          "medio": ("trimf", (25, 50, 75)),
                          "alto": ("trapmf", (60, 80, 100, 100))},
        },
    }


CONFIG_BASE = construir_config()

# Base de reglas. Antecedentes como dict {variable: etiqueta}; Y = mínimo.
REGLAS = [
    {"id": "R1", "si": {"score": "bajo"}, "entonces": "alto",
     "origen": "C1 · SCORE_CREDITICIO_BAJO", "texto": "SI el score es bajo ENTONCES el riesgo es alto"},
    {"id": "R2", "si": {"carga": "excedida"}, "entonces": "alto",
     "origen": "C2 · CAPACIDAD_DE_PAGO_EXCEDIDA", "texto": "SI la carga de la cuota es excedida ENTONCES el riesgo es alto"},
    {"id": "R3", "si": {"dti": "excesivo"}, "entonces": "alto",
     "origen": "C4 · ENDEUDAMIENTO_DTI_EXCESIVO", "texto": "SI el DTI es excesivo ENTONCES el riesgo es alto"},
    {"id": "R4", "si": {"score": "alto", "carga": "holgada", "dti": "aceptable"}, "entonces": "bajo",
     "origen": "C8 + C9 (ambas favorables)", "texto": "SI score alto Y carga holgada Y DTI aceptable ENTONCES riesgo bajo"},
    {"id": "R5", "si": {"score": "alto", "carga": "moderada", "dti": "aceptable"}, "entonces": "bajo",
     "origen": "C8 · HISTORIAL_EXCELENTE", "texto": "SI score alto Y carga moderada Y DTI aceptable ENTONCES riesgo bajo"},
    {"id": "R6", "si": {"score": "medio", "carga": "holgada", "dti": "aceptable"}, "entonces": "bajo",
     "origen": "C9 · CAPACIDAD_HOLGADA", "texto": "SI score medio Y carga holgada Y DTI aceptable ENTONCES riesgo bajo"},
    {"id": "R7", "si": {"score": "medio", "carga": "moderada", "dti": "aceptable"}, "entonces": "medio",
     "origen": "Aprobado por el SE sin ninguna regla favorable (zona gris)",
     "texto": "SI score medio Y carga moderada Y DTI aceptable ENTONCES riesgo medio"},
]

# Cómo se traduce la etiqueta de salida en una acción del flujo de crédito.
ACCION_POR_ETIQUETA = {
    "bajo": "APROBADO",
    "medio": "REVISION_MANUAL",
    "alto": "RECHAZADO_POR_RIESGO_FINANCIERO",
}
ORDEN_RIESGO = ["bajo", "medio", "alto"]

N_PUNTOS = 1001


def validar_config(config):
    """Comprueba orden de parámetros y que cada conjunto quede dentro de su universo."""
    for clave, var in list(config["variables"].items()) + [("salida", config["salida"])]:
        lo, hi = var["universo"]
        if not lo < hi:
            raise ValueError(f"Universo inválido en '{clave}'.")
        for etq, (tipo, params) in var["conjuntos"].items():
            if list(params) != sorted(params):
                raise ValueError(f"Los parámetros de '{clave}/{etq}' deben estar en orden no decreciente.")
            if params[0] < lo or params[-1] > hi:
                raise ValueError(f"El conjunto '{clave}/{etq}' se sale del universo [{lo}, {hi}].")
            FUNCIONES[tipo](lo, *params)  # dispara el ValueError de la función si algo está mal


def universo(var):
    lo, hi = var["universo"]
    return np.linspace(lo, hi, N_PUNTOS)


def curvas(var):
    u = universo(var)
    return u, {etq: FUNCIONES[tipo](u, *params) for etq, (tipo, params) in var["conjuntos"].items()}


def fuzzificar(valor, var):
    """Grado de pertenencia de un valor a cada etiqueta (fórmula exacta, sin interpolar)."""
    return {etq: float(FUNCIONES[tipo](valor, *params)) for etq, (tipo, params) in var["conjuntos"].items()}


def centroide(u, curva):
    """Defuzzificación por centroide (notebook de clase)."""
    integrar = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
    area = integrar(curva, u)
    if np.isclose(area, 0.0):
        raise ValueError("No hay área en la salida agregada; ninguna regla se activó.")
    return float(integrar(u * curva, u) / area)


def preparar_entradas(score, cuota, ingresos, deuda_total):
    """Valida los datos crudos de la solicitud y calcula las tres entradas difusas."""
    for nombre, v in (("score", score), ("cuota", cuota), ("ingresos", ingresos), ("deuda total", deuda_total)):
        if v is None or not np.isfinite(float(v)):
            raise ValueError(f"El campo {nombre} debe ser un número.")
        if float(v) < 0:
            raise ValueError(f"El campo {nombre} no puede ser negativo.")
    if float(ingresos) <= 0:
        raise ValueError("Los ingresos mensuales deben ser mayores que cero para calcular las razones.")
    # Mismo denominador que el sistema experto: max(ingresos, 1).
    carga = float(cuota) / max(float(ingresos), 1)
    dti = float(deuda_total) / max(float(ingresos), 1)
    return {"score": float(score), "carga": carga, "dti": dti}


def inferir(entradas: dict, config=None):
    """
    Inferencia Mamdani completa.
    entradas: {"score": .., "carga": .., "dti": ..} en sus unidades naturales.
    Devuelve grados, activación de cada regla, curva agregada, centroide,
    etiqueta dominante y acción recomendada.
    """
    config = config or CONFIG_BASE
    validar_config(config)
    variables = config["variables"]
    salida = config["salida"]

    grados, recortes = {}, {}
    for clave, var in variables.items():
        if clave not in entradas:
            raise ValueError(f"Falta la entrada '{clave}'.")
        valor = float(entradas[clave])
        if not np.isfinite(valor):
            raise ValueError(f"La entrada '{clave}' debe ser un número finito.")
        lo, hi = var["universo"]
        if clave == "score" and not lo <= valor <= hi:
            raise ValueError(f"El score {valor:g} está fuera del rango [{lo:g}, {hi:g}].")
        if valor < lo:
            raise ValueError(f"La entrada '{clave}' no puede ser menor que {lo:g}.")
        recortes[clave] = min(valor, hi)  # razones > 1 se saturan (ver docstring)
        grados[clave] = fuzzificar(recortes[clave], var)

    u_sal, curvas_sal = curvas(salida)
    agregada = np.zeros_like(u_sal)
    detalle = []
    for regla in REGLAS:
        activacion = min(grados[v][etq] for v, etq in regla["si"].items())
        agregada = np.maximum(agregada, np.minimum(activacion, curvas_sal[regla["entonces"]]))
        detalle.append({**regla, "activacion": activacion})

    valor = centroide(u_sal, agregada)
    pert_salida = fuzzificar(valor, salida)
    # Etiqueta con mayor pertenencia en el centroide; en empate gana la más riesgosa.
    etiqueta = max(ORDEN_RIESGO, key=lambda e: (round(pert_salida[e], 9), ORDEN_RIESGO.index(e)))
    return {
        "entradas": dict(entradas), "entradas_usadas": recortes, "grados": grados,
        "reglas": detalle, "universo_salida": u_sal, "agregada": agregada,
        "riesgo": valor, "pertenencia_salida": pert_salida,
        "etiqueta": etiqueta, "accion": ACCION_POR_ETIQUETA[etiqueta],
    }


def cobertura_reglas(config=None, pasos=41):
    """Comprueba que toda combinación del espacio de entradas active al menos una regla."""
    config = config or CONFIG_BASE
    vs = config["variables"]
    peor = 1.0
    for s in np.linspace(*vs["score"]["universo"], pasos):
        for c in np.linspace(*vs["carga"]["universo"], pasos):
            for d in np.linspace(*vs["dti"]["universo"], pasos):
                g = {k: fuzzificar(v, vs[k]) for k, v in (("score", s), ("carga", c), ("dti", d))}
                act = max(min(g[v][e] for v, e in r["si"].items()) for r in REGLAS)
                peor = min(peor, act)
    return peor

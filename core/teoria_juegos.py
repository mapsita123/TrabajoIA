"""
Sprint 3 (integración) · Teoría de juegos + coevolución con pagos económicos.

Fuente: "Teoria_d_ejuegos (1).ipynb" (script teoria_juegos_nequi_v2), que es el
modelo de pagos económicos con F1–F9 + F10 coherente con el sistema experto y
con la estrategia evolutiva del Sprint 3. El código de juego, operadores y
coevolución se conserva; con los supuestos por defecto y semilla 42 reproduce
la corrida del notebook (umbral final del mejor defensor ≈ 0.193).

Supuestos (todos del archivo fuente, editables desde la UI):
  prevalencia 2 %, botín base 1.0, +0.6 por señal F2–F9, costo de falso
  positivo 0.15, F10 en 40 % de los fraudes y 5 % de las legítimas.

Análisis de equilibrio: los de v2 (re-evaluación, matriz de pagos, test de
desviación unilateral, juego de inspección 2×2) más Nash puro y dominancia
(tomados de la versión v4 del notebook) y maximin. La versión v3 descrita en el
contexto del proyecto no está en la carpeta; ver docs/ANALISIS.md.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

N_SEÑALES_CONTROLABLES = 9      # F1..F9
N_PESOS = 9                     # F2..F9 (8) + F10 (1)

NOMBRES_ATK = ["F1 · Biometría", "F2 · Dispositivo+ubicación", "F3 · Velocidad anormal",
               "F4 · Dispositivo reutilizado", "F5 · Lista restrictiva", "F6 · Correo desechable",
               "F7 · País/IP inconsistente", "F8 · Fallos de OTP", "F9 · IP de riesgo"]
NOMBRES_PESOS = NOMBRES_ATK[1:] + ["F10 · Patrón de red (no controlable)"]

UMBRAL_ESTRICTO = 0.15
UMBRAL_LAXO = 0.40
INTENSIDAD_AGRESIVO = 0.30


@dataclass(frozen=True)
class Supuestos:
    n_muestra: int = 300
    p_legit_controlable: float = 0.04
    p_legit_f10: float = 0.05
    p_fraude_f10: float = 0.40
    prevalencia: float = 0.02
    valor_base_fraude: float = 1.0
    beneficio_por_señal: float = 0.6
    costo_falso_positivo: float = 0.15


SUPUESTOS_BASE = Supuestos()


# ------------------------------------------------------------ transacciones ---
def generar_legitimas(n, rng, s: Supuestos):
    controlables = rng.random((n, N_SEÑALES_CONTROLABLES)) < s.p_legit_controlable
    f10 = (rng.random(n) < s.p_legit_f10).reshape(-1, 1)
    return np.hstack([controlables, f10])


def generar_fraude(atacante, n, rng, s: Supuestos):
    controlables = rng.random((n, N_SEÑALES_CONTROLABLES)) < atacante["genes"]
    f10 = (rng.random(n) < s.p_fraude_f10).reshape(-1, 1)
    return np.hstack([controlables, f10])


def valor_fraude(señales, s: Supuestos):
    return s.valor_base_fraude + s.beneficio_por_señal * señales[:, 1:9].sum(axis=1)


# -------------------------------------------------- estrategias y operadores ---
def crear_atacante(rng):
    return {"genes": rng.uniform(0.1, 0.7, N_SEÑALES_CONTROLABLES), "sigma": float(rng.uniform(0.05, 0.2))}


def crear_defensor(rng):
    return {"pesos": rng.uniform(0, 1, N_PESOS), "umbral": float(rng.uniform(0, 1)),
            "sigma": float(rng.uniform(0.05, 0.3))}


def cruzar_atacantes(p1, p2, rng):
    a = rng.random(N_SEÑALES_CONTROLABLES)
    return {"genes": a * p1["genes"] + (1 - a) * p2["genes"], "sigma": float(np.sqrt(p1["sigma"] * p2["sigma"]))}


def cruzar_defensores(p1, p2, rng):
    a = rng.random(N_PESOS + 1)
    return {"pesos": a[:N_PESOS] * p1["pesos"] + (1 - a[:N_PESOS]) * p2["pesos"],
            "umbral": float(a[-1] * p1["umbral"] + (1 - a[-1]) * p2["umbral"]),
            "sigma": float(np.sqrt(p1["sigma"] * p2["sigma"]))}


def mutar_atacante(padre, rng):
    tau = 1 / np.sqrt(2 * np.sqrt(N_SEÑALES_CONTROLABLES))
    sigma = float(np.clip(padre["sigma"] * np.exp(tau * rng.normal()), 0.02, 0.4))
    genes = np.clip(padre["genes"] + rng.normal(0, sigma, N_SEÑALES_CONTROLABLES), 0, 1)
    return {"genes": genes, "sigma": sigma}


def mutar_defensor(padre, rng):
    dims = N_PESOS + 1
    tau = 1 / np.sqrt(2 * np.sqrt(dims))
    sigma = float(np.clip(padre["sigma"] * np.exp(tau * rng.normal()), 0.01, 0.5))
    ruido = rng.normal(0, sigma, dims)
    return {"pesos": np.clip(padre["pesos"] + ruido[:N_PESOS], 0, 1),
            "umbral": float(np.clip(padre["umbral"] + ruido[-1], 0, 1)), "sigma": sigma}


# ------------------------------------------------------ clasificador y pagos ---
def clasificar(defensor, señales):
    biometria_falla = señales[:, 0]                          # F1 = gate obligatorio
    resto = np.hstack([señales[:, 1:9], señales[:, 9:10]])   # F2..F9 + F10
    score = (resto @ defensor["pesos"]) / max(defensor["pesos"].sum(), 1e-9)
    return biometria_falla | (score > defensor["umbral"])


def jugar(defensor, atacante, rng, s: Supuestos = SUPUESTOS_BASE, n=None):
    n = n or s.n_muestra
    legit = generar_legitimas(n, rng, s)
    fraude = generar_fraude(atacante, n, rng, s)
    det_legit = clasificar(defensor, legit)
    det_fraude = clasificar(defensor, fraude)

    robado = (valor_fraude(fraude, s) * ~det_fraude).mean()
    fpr = det_legit.mean()
    recall = det_fraude.mean()
    pago_atacante = robado
    pago_defensor = -(s.prevalencia * robado + (1 - s.prevalencia) * s.costo_falso_positivo * fpr)

    tp = s.prevalencia * recall
    fp = (1 - s.prevalencia) * fpr
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"pago_def": pago_defensor, "pago_atk": pago_atacante, "recall": recall,
            "evasion": 1 - recall, "fpr": fpr, "precision": precision, "f1": f1}


def pago_vs_poblacion(jugador, rivales, rol, rng, s: Supuestos):
    if rol == "def":
        return np.mean([jugar(jugador, a, rng, s)["pago_def"] for a in rivales])
    return np.mean([jugar(d, jugador, rng, s)["pago_atk"] for d in rivales])


# ------------------------------------------------------------- coevolución ---
def generar_hijos(poblacion, lam, cruzar, mutar, rng):
    hijos = []
    for _ in range(lam):
        i, j = rng.integers(len(poblacion), size=2)
        hijos.append(mutar(cruzar(poblacion[i], poblacion[j], rng), rng))
    return hijos


def coevolucionar(rondas=30, mu=10, lam=30, semilla=42, s: Supuestos = SUPUESTOS_BASE, progreso=None):
    rng = np.random.default_rng(semilla)
    defensores = [crear_defensor(rng) for _ in range(mu)]
    atacantes = [crear_atacante(rng) for _ in range(mu)]
    historial = []
    for ronda in range(rondas):
        for d in defensores:
            d["fitness"] = pago_vs_poblacion(d, atacantes, "def", rng, s)
        for a in atacantes:
            a["fitness"] = pago_vs_poblacion(a, defensores, "atk", rng, s)
        historial.append({
            "ronda": ronda,
            "pago_def": max(d["fitness"] for d in defensores),
            "pago_atk": max(a["fitness"] for a in atacantes),
            "intensidad_atk": float(np.mean([a["genes"][1:9].mean() for a in atacantes])),
            "umbral_def": float(np.mean([d["umbral"] for d in defensores])),
        })
        hijos = generar_hijos(defensores, lam, cruzar_defensores, mutar_defensor, rng)
        for h in hijos:
            h["fitness"] = pago_vs_poblacion(h, atacantes, "def", rng, s)
        defensores = sorted(defensores + hijos, key=lambda d: d["fitness"], reverse=True)[:mu]

        hijos = generar_hijos(atacantes, lam, cruzar_atacantes, mutar_atacante, rng)
        for h in hijos:
            h["fitness"] = pago_vs_poblacion(h, defensores, "atk", rng, s)
        atacantes = sorted(atacantes + hijos, key=lambda a: a["fitness"], reverse=True)[:mu]
        if progreso:
            progreso((ronda + 1) / rondas)
    return defensores, atacantes, historial


# ---------------------------------------------------- análisis de equilibrio ---
def reevaluar(defensor, atacante, semilla, s: Supuestos = SUPUESTOS_BASE, repeticiones=50):
    r = np.random.default_rng(semilla)
    res = [jugar(defensor, atacante, r, s) for _ in range(repeticiones)]
    return {k: float(np.mean([x[k] for x in res])) for k in res[0]}


def matriz_de_pagos(defensores, atacantes, semilla, s: Supuestos = SUPUESTOS_BASE, repeticiones=5):
    r = np.random.default_rng(semilla)
    A = np.zeros((len(defensores), len(atacantes)))
    B = np.zeros_like(A)
    for i, d in enumerate(defensores):
        for j, a in enumerate(atacantes):
            res = [jugar(d, a, r, s) for _ in range(repeticiones)]
            A[i, j] = np.mean([x["pago_def"] for x in res])
            B[i, j] = np.mean([x["pago_atk"] for x in res])
    return A, B


def nash_puros(A, B, tol=1e-12):
    """Celdas donde ambos juegan una mejor respuesta al otro (de la versión v4)."""
    return [(i, j) for i in range(A.shape[0]) for j in range(A.shape[1])
            if A[i, j] >= A[:, j].max() - tol and B[i, j] >= B[i, :].max() - tol]


def dominancia_estricta(M):
    """Pares (i, k): la fila i domina estrictamente a la fila k (de la versión v4)."""
    return [(i, k) for i in range(M.shape[0]) for k in range(M.shape[0]) if i != k and np.all(M[i] > M[k])]


def maximin(A, B):
    """Estrategia de seguridad de cada jugador: la que maximiza su peor pago."""
    peor_def = A.min(axis=1)
    peor_atk = B.min(axis=0)
    return {"def_idx": int(np.argmax(peor_def)), "def_valor": float(peor_def.max()),
            "atk_idx": int(np.argmax(peor_atk)), "atk_valor": float(peor_atk.max())}


def test_desviacion(defensor, atacante, defensores, atacantes, semilla, s: Supuestos = SUPUESTOS_BASE,
                    n_mutantes=200, n=1000, tol=0.02):
    """Test de Nash empírico (ε-Nash) con números aleatorios comunes."""
    def pago_def(d):
        return np.mean([jugar(d, a, np.random.default_rng(semilla + k), s, n=n)["pago_def"]
                        for k, a in enumerate(atacantes)])

    def pago_atk(a):
        return np.mean([jugar(d, a, np.random.default_rng(semilla + k), s, n=n)["pago_atk"]
                        for k, d in enumerate(defensores)])

    r = np.random.default_rng(semilla + 10_000)
    base_def, base_atk = pago_def(defensor), pago_atk(atacante)
    mejoras_def = [pago_def(mutar_defensor(defensor, r)) - base_def for _ in range(n_mutantes)]
    mejoras_atk = [pago_atk(mutar_atacante(atacante, r)) - base_atk for _ in range(n_mutantes)]
    return {
        "def_base": float(base_def), "def_max_mejora": float(max(mejoras_def)),
        "def_pct_mejoran": float(np.mean(np.array(mejoras_def) > tol * abs(base_def))),
        "atk_base": float(base_atk), "atk_max_mejora": float(max(mejoras_atk)),
        "atk_pct_mejoran": float(np.mean(np.array(mejoras_atk) > tol * max(abs(base_atk), 1e-9))),
    }


def juego_de_inspeccion(semilla, defensor_evolucionado, s: Supuestos = SUPUESTOS_BASE):
    """Reducción 2×2 (ESTRICTO/LAXO × AGRESIVO/SIGILOSO) resuelta por indiferencia."""
    pesos = defensor_evolucionado["pesos"]
    defs = [{"pesos": pesos, "umbral": UMBRAL_ESTRICTO}, {"pesos": pesos, "umbral": UMBRAL_LAXO}]
    atks = [{"genes": np.r_[0.0, np.full(8, INTENSIDAD_AGRESIVO)]}, {"genes": np.zeros(9)}]
    r = np.random.default_rng(semilla)
    A = np.zeros((2, 2)); B = np.zeros((2, 2))
    for i, d in enumerate(defs):
        for j, a in enumerate(atks):
            res = jugar(d, a, r, s, n=20000)
            A[i, j], B[i, j] = res["pago_def"], res["pago_atk"]
    puros = [(i, j) for i in range(2) for j in range(2) if A[i, j] >= A[1 - i, j] and B[i, j] >= B[i, 1 - j]]
    den_q = A[0, 0] - A[0, 1] - A[1, 0] + A[1, 1]
    den_p = B[0, 0] - B[1, 0] - B[0, 1] + B[1, 1]
    q = (A[1, 1] - A[0, 1]) / den_q if den_q else np.nan
    p = (B[1, 1] - B[1, 0]) / den_p if den_p else np.nan
    valido = bool(0 <= q <= 1 and 0 <= p <= 1)
    return A, B, puros, (float(p), float(q), valido)


def comparar_con_linea_base(mejor_def, atacantes, semilla, s: Supuestos = SUPUESTOS_BASE):
    """Defensor evolucionado vs. regla fija de línea base (pesos iguales, umbral 0.5, como el Sprint 3)."""
    base = {"pesos": np.ones(N_PESOS), "umbral": 0.5}
    filas = []
    for nombre, d in (("Regla fija (pesos iguales, umbral 0.5)", base), ("Defensor coevolucionado", mejor_def)):
        r = np.random.default_rng(semilla)
        res = [jugar(d, a, r, s) for a in atacantes for _ in range(5)]
        filas.append({"defensor": nombre,
                      "costo_por_1000_tx": -1000 * float(np.mean([x["pago_def"] for x in res])),
                      "recall": float(np.mean([x["recall"] for x in res])),
                      "fpr": float(np.mean([x["fpr"] for x in res])),
                      "botin_atacante": float(np.mean([x["pago_atk"] for x in res]))})
    return filas


def corrida_completa(rondas=30, mu=10, lam=30, semilla=42, s: Supuestos = SUPUESTOS_BASE,
                     con_desviacion=True, progreso=None):
    """Ejecuta el pipeline de v2 y devuelve resultados serializables para la UI."""
    defensores, atacantes, historial = coevolucionar(rondas, mu, lam, semilla, s, progreso)
    mejor_atk = max(atacantes, key=lambda a: a["fitness"])
    mejor_def = max(defensores, key=lambda d: d["fitness"])
    top_d = sorted(defensores, key=lambda d: d["fitness"], reverse=True)[:5]
    top_a = sorted(atacantes, key=lambda a: a["fitness"], reverse=True)[:5]
    A, B = matriz_de_pagos(top_d, top_a, semilla=7, s=s)
    A2, B2, puros2, (p, q, valido) = juego_de_inspeccion(11, mejor_def, s)
    out = {
        "supuestos": asdict(s),
        "historial": historial,
        "mejor_atk": {"genes": mejor_atk["genes"].tolist()},
        "mejor_def": {"pesos": mejor_def["pesos"].tolist(), "umbral": mejor_def["umbral"]},
        "reevaluacion": reevaluar(mejor_def, mejor_atk, 2026, s),
        "matriz": {"A": A.tolist(), "B": B.tolist(), "nash_puros": nash_puros(A, B),
                   "dominancia_def": dominancia_estricta(A), "dominancia_atk": dominancia_estricta(B.T),
                   "maximin": maximin(A, B)},
        "inspeccion": {"A": A2.tolist(), "B": B2.tolist(), "puros": puros2, "p": p, "q": q, "valido": valido},
        "intensidad_evo": float(np.mean([a["genes"][1:9].mean() for a in atacantes])),
        "umbral_evo": float(np.mean([d["umbral"] for d in defensores])),
        "linea_base": comparar_con_linea_base(mejor_def, top_a, 303, s),
    }
    if con_desviacion:
        out["desviacion"] = test_desviacion(mejor_def, mejor_atk, defensores, atacantes, 99, s)
    return out

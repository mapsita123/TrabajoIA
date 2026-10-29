"""
Teoría de juegos · versión simplificada v4 ("guardia vs. ladrones").

Fuente: "Teoria_de_juegos_nequi_v4_simple.ipynb". Se conserva como modelo
aparte porque usa supuestos distintos al resto del proyecto (ver
docs/ANALISIS.md, contradicción C2): sus señales F1–F8 son señales de
transacción (dispositivo nuevo, monto alto, ...), no las reglas F1–F9 del
sistema experto; la prevalencia es 4 %, la penalización por falso positivo 0.5
y el botín extra por señal 0.5. El defensor suma puntos contra un umbral.
"""
from __future__ import annotations

import numpy as np

NOMBRES = ["F1 Dispositivo nuevo", "F2 Monto alto", "F3 Ráfaga de transacciones", "F4 Ubicación inusual",
           "F5 Horario inusual", "F6 Destinatario nuevo", "F7 Fallos de OTP", "F8 IP de riesgo"]
N_SEÑALES = len(NOMBRES)

P_LEGIT = np.array([0.10, 0.08, 0.03, 0.10, 0.12, 0.15, 0.04, 0.03])
ATACANTE_INICIAL = np.array([0.7, 0.2, 0.7, 0.2, 0.2, 0.2, 0.7, 0.7])
PESOS_INICIALES = np.ones(N_SEÑALES)
UMBRAL_INICIAL = 2.0

PREVALENCIA = 0.04
MONTO_BASE = 1.0
MONTO_EXTRA_POR_SEÑAL = 0.5
PENALIZACION_FALSO_POSITIVO = 0.5
LOTE = 3000

MU, LAMBDA, RONDAS = 10, 30, 60
UMBRAL_ESTRICTO, UMBRAL_LAXO = 3.0, 5.0

CONFIG = {
    "def": {"base": np.r_[PESOS_INICIALES, UMBRAL_INICIAL],
            "min": np.r_[np.zeros(N_SEÑALES), 0.5], "max": np.r_[np.full(N_SEÑALES, 3.0), 8.0],
            "sigma0": 0.25, "sigma_min": 0.05, "sigma_max": 1.0},
    "atk": {"base": ATACANTE_INICIAL, "min": np.zeros(N_SEÑALES), "max": np.ones(N_SEÑALES),
            "sigma0": 0.08, "sigma_min": 0.02, "sigma_max": 0.30},
}


def jugar(defensor, atacante, rng, n=LOTE):
    pesos, umbral = defensor["x"][:N_SEÑALES], defensor["x"][N_SEÑALES]
    es_fraude = rng.random(n) < PREVALENCIA
    probs = np.where(es_fraude[:, None], atacante["x"], P_LEGIT)
    incumple = rng.random((n, N_SEÑALES)) < probs
    bloquea = (incumple @ pesos) >= umbral
    monto = MONTO_BASE + MONTO_EXTRA_POR_SEÑAL * incumple.sum(axis=1)
    fraude_pasa = es_fraude & ~bloquea
    fraude_bloqueado = es_fraude & bloquea
    falso_positivo = ~es_fraude & bloquea
    robado = monto[fraude_pasa].sum()
    n_fraudes = max(es_fraude.sum(), 1)
    tp, fp = fraude_bloqueado.sum(), falso_positivo.sum()
    recall = tp / n_fraudes
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    return {"pago_def": -(robado + PENALIZACION_FALSO_POSITIVO * fp) / n,
            "pago_atk": robado / n_fraudes, "recall": recall,
            "fpr": fp / max((~es_fraude).sum(), 1), "precision": precision,
            "f1": 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0}


def crear_poblacion(rol, rng):
    c = CONFIG[rol]
    return [{"x": np.clip(c["base"] + rng.normal(0, c["sigma0"], len(c["base"])), c["min"], c["max"]),
             "sigma": c["sigma0"]} for _ in range(MU)]


def cruzar(p1, p2, rng):
    a = rng.random(len(p1["x"]))
    return {"x": a * p1["x"] + (1 - a) * p2["x"], "sigma": float(np.sqrt(p1["sigma"] * p2["sigma"]))}


def mutar(ind, rol, rng):
    c, n = CONFIG[rol], len(ind["x"])
    tau = 1 / np.sqrt(2 * np.sqrt(n))
    sigma = float(np.clip(ind["sigma"] * np.exp(tau * rng.normal()), c["sigma_min"], c["sigma_max"]))
    return {"x": np.clip(ind["x"] + rng.normal(0, sigma, n), c["min"], c["max"]), "sigma": sigma}


def pago_vs(ind, rol, rivales, semilla):
    pagos = []
    for k, rival in enumerate(rivales):
        r = np.random.default_rng(semilla + k)
        pagos.append(jugar(ind, rival, r)["pago_def"] if rol == "def" else jugar(rival, ind, r)["pago_atk"])
    return float(np.mean(pagos))


def evolucionar_un_paso(poblacion, rol, rivales, rng):
    semilla = int(rng.integers(10**9))
    for ind in poblacion:
        ind["fitness"] = pago_vs(ind, rol, rivales, semilla)
    hijos = []
    for _ in range(LAMBDA):
        i, j = rng.integers(len(poblacion), size=2)
        hijo = mutar(cruzar(poblacion[i], poblacion[j], rng), rol, rng)
        hijo["fitness"] = pago_vs(hijo, rol, rivales, semilla)
        hijos.append(hijo)
    return sorted(poblacion + hijos, key=lambda ind: ind["fitness"], reverse=True)[:MU]


def matriz_de_pagos(defs, atks, semilla, repeticiones=10):
    r = np.random.default_rng(semilla)
    A, B = np.zeros((len(defs), len(atks))), np.zeros((len(defs), len(atks)))
    for i, d in enumerate(defs):
        for j, a in enumerate(atks):
            res = [jugar(d, a, r) for _ in range(repeticiones)]
            A[i, j] = np.mean([x["pago_def"] for x in res])
            B[i, j] = np.mean([x["pago_atk"] for x in res])
    return A, B


def barrido_umbral():
    """Sección 3 del notebook: costo del defensor según el umbral (pesos de 1 punto)."""
    atacante = {"x": ATACANTE_INICIAL.copy()}
    filas = []
    for u in [1, 2, 3, 4, 5, 8]:
        d = {"x": np.r_[np.ones(N_SEÑALES), u]}
        res = [jugar(d, atacante, np.random.default_rng(100 + k)) for k in range(20)]
        filas.append({"umbral_puntos": u, "fraude_detectado": float(np.mean([x["recall"] for x in res])),
                      "clientes_bloqueados": float(np.mean([x["fpr"] for x in res])),
                      "costo_defensor": -float(np.mean([x["pago_def"] for x in res]))})
    return filas


def corrida_completa(semilla=42, progreso=None):
    """Secciones 5, 6.2 y 8 del notebook (coevolución, mejores estrategias, inspección 2×2)."""
    rng = np.random.default_rng(semilla)
    defensores = crear_poblacion("def", rng)
    atacantes = crear_poblacion("atk", rng)
    historia = []
    for ronda in range(RONDAS):
        defensores = evolucionar_un_paso(defensores, "def", atacantes, rng)
        atacantes = evolucionar_un_paso(atacantes, "atk", defensores, rng)
        historia.append({"ronda": ronda, "pago_def": defensores[0]["fitness"], "pago_atk": atacantes[0]["fitness"]})
        if progreso:
            progreso((ronda + 1) / RONDAS)

    A_full, B_full = matriz_de_pagos(defensores, atacantes, semilla=2025)
    mejor_def = defensores[int(np.argsort(-A_full.mean(axis=1))[0])]
    mejor_atk = atacantes[int(np.argsort(-B_full.mean(axis=0))[0])]

    defs2 = [{"x": np.r_[np.ones(N_SEÑALES), UMBRAL_ESTRICTO]}, {"x": np.r_[np.ones(N_SEÑALES), UMBRAL_LAXO]}]
    atks2 = [{"x": ATACANTE_INICIAL.copy()}, {"x": P_LEGIT.copy()}]
    A2, B2 = matriz_de_pagos(defs2, atks2, semilla=11, repeticiones=100)
    q = (A2[1, 1] - A2[0, 1]) / (A2[0, 0] - A2[0, 1] - A2[1, 0] + A2[1, 1])
    p = (B2[1, 1] - B2[1, 0]) / (B2[0, 0] - B2[1, 0] - B2[0, 1] + B2[1, 1])
    return {
        "historia": historia,
        "mejor_def": {"pesos": mejor_def["x"][:N_SEÑALES].tolist(), "umbral": float(mejor_def["x"][N_SEÑALES])},
        "mejor_atk": mejor_atk["x"].tolist(),
        "inspeccion": {"A": A2.tolist(), "B": B2.tolist(), "p": float(p), "q": float(q),
                       "valido": bool(0 <= p <= 1 and 0 <= q <= 1)},
    }

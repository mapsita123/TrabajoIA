"""
Sprint 3 · Estrategia evolutiva (μ+λ) — calibración del score de fraude.

Fuente: "Algoritmo_Genético_Nequi (3).ipynb". El código se conserva tal cual
(mismas semillas y mismo orden de llamadas al generador), por lo que con los
parámetros por defecto reproduce los resultados del notebook:
mejor F1 de entrenamiento 0.8947 y umbral aprendido 0.2924.

- F1 (biometría) es un control obligatorio fuera del score.
- El individuo tiene 8 pesos (F2–F9) + umbral + σ autoadaptativo.
- Fitness = F1-score sobre el conjunto de entrenamiento (70 %, estratificado).
"""
from __future__ import annotations

import random

import numpy as np

SEMILLA = 42

NOMBRES_REGLAS = [
    "F1_biometria_baja", "F2_dispositivo_y_ubicacion", "F3_velocidad_anormal",
    "F4_dispositivo_reutilizado", "F5_lista_restrictiva", "F6_correo_desechable",
    "F7_pais_ip_inconsistente", "F8_fallos_otp", "F9_ip_riesgo",
]

CRITERIOS_SCORE = [
    "F2 · Dispositivo y ubicación", "F3 · Velocidad anormal",
    "F4 · Dispositivo reutilizado", "F5 · Lista restrictiva",
    "F6 · Correo desechable", "F7 · País e IP inconsistentes",
    "F8 · Fallos de OTP", "F9 · IP de riesgo",
]
N_PESOS = len(CRITERIOS_SCORE)  # 8

MU = 20
LAMBDA = 100
GENERACIONES = 60
PROPORCION_ENTRENAMIENTO = 0.70

# Línea base del notebook: todos los pesos iguales y umbral 0.5.
PESOS_BASE = np.ones(N_PESOS)
UMBRAL_BASE = 0.5


# ---------------------------------------------------------------- dataset ---
def generar_transaccion(es_fraude, generador):
    frecuentes_en_fraude = {"F1_biometria_baja", "F4_dispositivo_reutilizado",
                            "F5_lista_restrictiva", "F7_pais_ip_inconsistente"}
    señales = []
    for nombre in NOMBRES_REGLAS:
        if es_fraude:
            probabilidad = 0.55 if nombre in frecuentes_en_fraude else 0.25
        else:
            probabilidad = 0.04
        señales.append(int(generador.random() < probabilidad))
    return señales


def generar_dataset(n_legitimas=400, n_fraude=60, semilla=SEMILLA):
    generador = random.Random(semilla)
    datos = []
    for etiqueta, cantidad in ((0, n_legitimas), (1, n_fraude)):
        for _ in range(cantidad):
            señales = generar_transaccion(bool(etiqueta), generador)
            # Simplificación del notebook: F1 ausente = biometría verificada.
            estado = "VERIFICADA" if señales[0] == 0 else "REQUIERE_VERIFICACION"
            datos.append({"reglas": señales, "estado_biometria": estado, "etiqueta": etiqueta})
    generador.shuffle(datos)
    return datos


def supera_control_biometrico(t):
    return t.get("estado_biometria") == "VERIFICADA" and t["reglas"][0] == 0


def dividir_estratificado(datos, proporcion=PROPORCION_ENTRENAMIENTO, semilla=SEMILLA):
    if not 0 < proporcion < 1:
        raise ValueError("La proporción debe estar entre 0 y 1.")
    generador = random.Random(semilla)
    entrenamiento, prueba = [], []
    for etiqueta in (0, 1):
        grupo = [t for t in datos if t["etiqueta"] == etiqueta]
        if len(grupo) < 2:
            raise ValueError(f"No hay suficientes ejemplos de la clase {etiqueta}.")
        generador.shuffle(grupo)
        corte = max(1, min(int(len(grupo) * proporcion), len(grupo) - 1))
        entrenamiento.extend(grupo[:corte])
        prueba.extend(grupo[corte:])
    generador.shuffle(entrenamiento)
    generador.shuffle(prueba)
    return entrenamiento, prueba


def convertir_a_arrays(datos):
    X = np.array([t["reglas"][1:] for t in datos], dtype=float)  # sin F1
    y = np.array([t["etiqueta"] for t in datos], dtype=int)
    return X, y


# ------------------------------------------------------ score y métricas ---
def calcular_scores(pesos, X):
    suma = np.sum(pesos)
    if suma <= 0:
        return np.zeros(len(X), dtype=float)
    return (X @ pesos) / suma


def predecir(pesos, umbral, X):
    return (calcular_scores(pesos, X) > umbral).astype(int)  # score == umbral -> sin alerta


def calcular_metricas(pesos, umbral, X, y):
    pred = predecir(pesos, umbral, X)
    vp = int(np.sum((pred == 1) & (y == 1)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))
    vn = int(np.sum((pred == 0) & (y == 0)))
    precision = vp / (vp + fp) if (vp + fp) else 0.0
    recall = vp / (vp + fn) if (vp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"f1": f1, "precision": precision, "recall": recall, "vp": vp, "fp": fp, "fn": fn, "vn": vn}


def calcular_fitness(pesos, umbral, X, y):
    return calcular_metricas(pesos, umbral, X, y)["f1"]


# ------------------------------------------------- estrategia evolutiva ---
def crear_individuo(rng, X, y):
    pesos = rng.uniform(0, 1, N_PESOS)
    umbral = float(rng.uniform(0, 1))
    sigma = float(rng.uniform(0.05, 0.30))
    return {"pesos": pesos, "umbral": umbral, "sigma": sigma,
            "fitness": calcular_fitness(pesos, umbral, X, y)}


def mutar_individuo(padre, rng, X, y):
    dimensiones = N_PESOS + 1
    tau = 1 / np.sqrt(2 * np.sqrt(dimensiones))
    sigma_hijo = float(np.clip(padre["sigma"] * np.exp(tau * rng.normal()), 0.01, 0.5))
    ruido = rng.normal(loc=0, scale=sigma_hijo, size=dimensiones)
    pesos_hijo = np.clip(padre["pesos"] + ruido[:N_PESOS], 0, 1)
    umbral_hijo = float(np.clip(padre["umbral"] + ruido[-1], 0, 1))
    return {"pesos": pesos_hijo, "umbral": umbral_hijo, "sigma": sigma_hijo,
            "fitness": calcular_fitness(pesos_hijo, umbral_hijo, X, y)}


def estrategia_evolutiva(X, y, mu=MU, lambda_=LAMBDA, generaciones=GENERACIONES, semilla=SEMILLA):
    if mu < 1 or lambda_ < 1 or generaciones < 0:
        raise ValueError("Parámetros evolutivos inválidos.")
    rng = np.random.default_rng(semilla)
    poblacion = sorted((crear_individuo(rng, X, y) for _ in range(mu)),
                       key=lambda i: i["fitness"], reverse=True)
    historial = [{"generacion": 0, "mejor_fitness": poblacion[0]["fitness"],
                  "fitness_promedio": float(np.mean([i["fitness"] for i in poblacion]))}]
    for generacion in range(1, generaciones + 1):
        descendientes = [mutar_individuo(poblacion[int(rng.integers(0, mu))], rng, X, y)
                         for _ in range(lambda_)]
        # Selección (μ + λ): padres e hijos compiten.
        poblacion = sorted(poblacion + descendientes, key=lambda i: i["fitness"], reverse=True)[:mu]
        historial.append({"generacion": generacion, "mejor_fitness": poblacion[0]["fitness"],
                          "fitness_promedio": float(np.mean([i["fitness"] for i in poblacion]))})
    return poblacion[0], historial, poblacion


def entrenar(mu=MU, lambda_=LAMBDA, generaciones=GENERACIONES, semilla=SEMILLA):
    """Ejecuta el experimento completo del notebook y devuelve todo lo necesario para la UI."""
    dataset = generar_dataset(semilla=semilla)
    habilitadas = [t for t in dataset if supera_control_biometrico(t)]
    detenidas = [t for t in dataset if not supera_control_biometrico(t)]
    entrenamiento, prueba = dividir_estratificado(habilitadas, semilla=semilla)
    X_tr, y_tr = convertir_a_arrays(entrenamiento)
    X_te, y_te = convertir_a_arrays(prueba)
    mejor, historial, poblacion = estrategia_evolutiva(X_tr, y_tr, mu, lambda_, generaciones, semilla)
    metricas = {
        conjunto: {"Base": calcular_metricas(PESOS_BASE, UMBRAL_BASE, X, y),
                   "Optimizado": calcular_metricas(mejor["pesos"], mejor["umbral"], X, y)}
        for conjunto, X, y in (("Entrenamiento", X_tr, y_tr), ("Prueba", X_te, y_te))
    }
    return {
        "modelo": {"pesos": mejor["pesos"], "umbral": mejor["umbral"], "sigma": mejor["sigma"],
                   "fitness": mejor["fitness"]},
        "historial": historial,
        "metricas": metricas,
        "conteos": {"total": len(dataset), "detenidas": len(detenidas), "habilitadas": len(habilitadas),
                    "detenidas_fraude": sum(t["etiqueta"] for t in detenidas),
                    "habilitadas_fraude": sum(t["etiqueta"] for t in habilitadas),
                    "train": len(y_tr), "train_fraude": int(y_tr.sum()),
                    "test": len(y_te), "test_fraude": int(y_te.sum())},
    }


# ------------------------------------------------- uso del modelo calibrado ---
def evaluar_solicitud(señales_reglas, estado_biometria, modelo):
    """Simulador del notebook: biometría como gate + score ponderado vs. umbral."""
    señales = np.asarray(señales_reglas, dtype=float)
    if señales.shape != (len(NOMBRES_REGLAS),):
        raise ValueError("Debes proporcionar exactamente 9 señales.")
    if not np.all(np.isin(señales, [0, 1])):
        raise ValueError("Cada señal debe ser 0 o 1.")

    if estado_biometria != "VERIFICADA" or señales[0] == 1:
        return {"decision": "REQUIERE_VERIFICACION_BIOMETRICA",
                "motivo": "No se continúa al análisis automático de riesgo hasta resolver la verificación de identidad.",
                "score": None, "umbral": None, "aportes": []}

    pesos = np.asarray(modelo["pesos"], dtype=float)
    suma = np.sum(pesos)
    relativos = pesos / suma if suma > 0 else np.zeros_like(pesos)
    señales_score = señales[1:]
    contribuciones = relativos * señales_score
    score = float(np.sum(contribuciones))
    umbral = float(modelo["umbral"])
    alerta = score > umbral
    aportes = [{"criterio": CRITERIOS_SCORE[i], "activa": int(señales_score[i]),
                "peso_relativo": float(relativos[i]), "aporte": float(contribuciones[i])}
               for i in np.argsort(-contribuciones)]
    return {"decision": "ALERTA_DE_RIESGO" if alerta else "SIN_ALERTA_DEL_MODELO",
            "motivo": "El score supera el umbral aprendido." if alerta else "El score no supera el umbral aprendido.",
            "score": score, "umbral": umbral, "aportes": aportes}


def señales_desde_hechos(reglas_fraude_disparadas: list[dict]) -> list[int]:
    """Convierte las reglas F1–F9 disparadas por el sistema experto en el vector binario del Sprint 3."""
    ids = {d["id"] for d in reglas_fraude_disparadas}
    return [int(f"F{i}" in ids) for i in range(1, 10)]

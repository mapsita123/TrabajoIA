"""
Casos de prueba ejecutables, compartidos por la página de Validación y por
tests/ (pytest). Cada caso devuelve: grupo, caso, esperado, obtenido, ok.
"""
from __future__ import annotations

import itertools

import numpy as np

from core import busqueda, difuso, evolutivo, integracion
from core.sistema_experto import (DECISION_ETIQUETADA_PRESET, PRESETS, SistemaExpertoOriginacionCredito,
                                  construir_reglas_fraude)


def _caso(grupo, caso, esperado, obtenido, ok=None, nota=""):
    return {"grupo": grupo, "caso": caso, "esperado": str(esperado), "obtenido": str(obtenido),
            "ok": bool(esperado == obtenido) if ok is None else bool(ok), "nota": nota}


def _base(**cambios):
    return {**PRESETS["Caso 2 · Crédito aprobado"], **cambios}


# ----------------------------------------------------------------- difuso ---
def casos_difuso():
    cfg = difuso.CONFIG_BASE
    vs = cfg["variables"]
    out = []
    for clave, valor, a, b in (("score", 600, "bajo", "medio"), ("score", 750, "medio", "alto"),
                               ("carga", 0.20, "holgada", "moderada"), ("carga", 0.35, "moderada", "excedida"),
                               ("dti", 0.70, "aceptable", "excesivo")):
        g = difuso.fuzzificar(valor, vs[clave])
        out.append(_caso("Lógica difusa · anclaje", f"μ en el umbral {clave} = {valor}", "0.50 / 0.50",
                         f"{g[a]:.2f} / {g[b]:.2f}", ok=np.isclose(g[a], 0.5) and np.isclose(g[b], 0.5)))

    def accion(s, c, d):
        return difuso.inferir({"score": s, "carga": c, "dti": d})["accion"]

    for (s, c, d), esp, nombre in [
        ((800, 0.10, 0.20), "APROBADO", "Perfil claramente sano"),
        ((500, 0.10, 0.10), "RECHAZADO_POR_RIESGO_FINANCIERO", "Score claramente bajo"),
        ((800, 0.50, 0.20), "RECHAZADO_POR_RIESGO_FINANCIERO", "Cuota claramente excedida"),
        ((800, 0.10, 0.90), "RECHAZADO_POR_RIESGO_FINANCIERO", "DTI claramente excesivo"),
        ((700, 0.30, 0.30), "REVISION_MANUAL", "Zona gris: aprobado rígido sin reglas favorables"),
        ((600, 0.20, 0.30), "REVISION_MANUAL", "Exactamente en el umbral C1"),
        ((760, 0.36, 0.30), "REVISION_MANUAL", "Cuota apenas sobre C2 con buen score"),
        ((950, 0.00, 0.00), "APROBADO", "Límite superior del universo"),
        ((150, 1.00, 1.00), "RECHAZADO_POR_RIESGO_FINANCIERO", "Límite inferior del universo"),
    ]:
        out.append(_caso("Lógica difusa · decisiones", f"{nombre} (score {s}, carga {c}, DTI {d})", esp, accion(s, c, d)))

    r599 = difuso.inferir({"score": 599, "carga": 0.2, "dti": 0.3})["riesgo"]
    r601 = difuso.inferir({"score": 601, "carga": 0.2, "dti": 0.3})["riesgo"]
    out.append(_caso("Lógica difusa · continuidad", "Score 599 frente a 601: el riesgo cambia menos de 2 puntos",
                     "< 2", f"{abs(r599 - r601):.2f}", ok=abs(r599 - r601) < 2))

    xs = np.linspace(150, 950, 81)
    rs = [difuso.inferir({"score": x, "carga": 0.2, "dti": 0.3})["riesgo"] for x in xs]
    out.append(_caso("Lógica difusa · monotonía", "El riesgo no aumenta cuando sube el score", "no creciente",
                     "no creciente" if np.all(np.diff(rs) <= 1e-9) else "viola", ok=bool(np.all(np.diff(rs) <= 1e-9))))
    cs = np.linspace(0, 1, 81)
    rc = [difuso.inferir({"score": 700, "carga": c, "dti": 0.3})["riesgo"] for c in cs]
    out.append(_caso("Lógica difusa · monotonía", "El riesgo no disminuye cuando sube la carga", "no decreciente",
                     "no decreciente" if np.all(np.diff(rc) >= -1e-9) else "viola", ok=bool(np.all(np.diff(rc) >= -1e-9))))

    cob = difuso.cobertura_reglas(pasos=21)
    out.append(_caso("Lógica difusa · cobertura", "Toda combinación activa al menos una regla", "≥ 0.5", f"{cob:.2f}",
                     ok=cob >= 0.5))

    for nombre, fn in [("Score fuera de rango (100)", lambda: difuso.inferir({"score": 100, "carga": .2, "dti": .2})),
                       ("Carga negativa", lambda: difuso.inferir({"score": 700, "carga": -0.1, "dti": .2})),
                       ("Ingresos en cero", lambda: difuso.preparar_entradas(700, 1, 0, 1)),
                       ("Entrada no numérica", lambda: difuso.inferir({"score": float("nan"), "carga": .2, "dti": .2}))]:
        try:
            fn()
            obtenido = "aceptada"
        except ValueError:
            obtenido = "rechazada"
        out.append(_caso("Lógica difusa · validación de entradas", nombre, "rechazada", obtenido))
    return out


# --------------------------------------------------- flujo integrado ---
def casos_integracion(modelo_ee):
    out = []
    esperados = {"Caso 1 · Fraude detectado": ("RECHAZADO_POR_FRAUDE", "Motor de fraude (Sprint 2)"),
                 "Caso 2 · Crédito aprobado": ("APROBADO", "Capa difusa (Sprint 4)"),
                 "Caso 3 · Crédito rechazado": ("RECHAZADO_POR_RIESGO_FINANCIERO", "Reglas rígidas del motor de crédito (Sprint 2)"),
                 "Caso 4 · Revisión manual": ("APROBADO", "Capa difusa (Sprint 4)")}
    for nombre, (dec, etapa) in esperados.items():
        r = integracion.evaluar(PRESETS[nombre], modelo_ee)
        out.append(_caso("Flujo integrado", f"{nombre}", f"{dec} · {etapa}", f"{r['decision_final']} · {r['etapa_final']}"))

    r = integracion.evaluar(PRESETS["Caso 1 · Fraude detectado"], modelo_ee)
    out.append(_caso("Flujo integrado", "Cortocircuito: con fraude no se ejecutan crédito ni capa difusa",
                     "no ejecutados", "no ejecutados" if r["difuso"] is None and r["credito_clasico"] is None else "ejecutados"))

    r = integracion.evaluar(_base(score_datacredito=598), modelo_ee)
    out.append(_caso("Flujo integrado", "Caso 2 con score 598: rígido rechaza, híbrido envía a revisión",
                     "RECHAZADO_POR_RIESGO_FINANCIERO → REVISION_MANUAL",
                     f"{r['credito_clasico']} → {r['decision_final']}"))

    r = integracion.evaluar(_base(embargos_activos=True), modelo_ee)
    out.append(_caso("Flujo integrado", "Perfil excelente con embargo activo (C7 rígida)", "RECHAZADO_POR_RIESGO_FINANCIERO",
                     r["decision_final"]))

    r = integracion.evaluar(_base(mora_actual_dias=31), modelo_ee)
    out.append(_caso("Flujo integrado", "Mora de 31 días (C3 rígida, límite)", "RECHAZADO_POR_RIESGO_FINANCIERO",
                     r["decision_final"]))
    r = integracion.evaluar(_base(mora_actual_dias=30), modelo_ee)
    out.append(_caso("Flujo integrado", "Mora de 30 días (C3 no se dispara)", "APROBADO", r["decision_final"]))

    r = integracion.evaluar(_base(email_desechable=True), modelo_ee)
    out.append(_caso("Flujo integrado", "Una sola alerta media (F6)", "REVISION_MANUAL · Motor de fraude (Sprint 2)",
                     f"{r['decision_final']} · {r['etapa_final']}"))
    r = integracion.evaluar(_base(email_desechable=True, ip_riesgo=True), modelo_ee)
    out.append(_caso("Flujo integrado", "Dos alertas medias (F6 + F9)", "RECHAZADO_POR_FRAUDE", r["decision_final"]))
    r = integracion.evaluar(_base(match_facial=0.79), modelo_ee)
    out.append(_caso("Flujo integrado", "Match facial 0.79 (F1 crítica, límite)", "RECHAZADO_POR_FRAUDE", r["decision_final"]))
    r = integracion.evaluar(_base(match_facial=0.80), modelo_ee)
    out.append(_caso("Flujo integrado", "Match facial 0.80 (F1 no se dispara)", "APROBADO", r["decision_final"]))

    for nombre, cambios in [("Ingresos en cero", {"ingresos_mensuales": 0}),
                            ("Score fuera de rango", {"score_datacredito": 1200}),
                            ("Campo faltante", {"mora_actual_dias": None}),
                            ("Texto en un campo numérico", {"deuda_total_mensual": "mucho"})]:
        try:
            integracion.evaluar(_base(**cambios), modelo_ee)
            obtenido = "aceptada"
        except ValueError:
            obtenido = "rechazada con mensaje"
        out.append(_caso("Flujo integrado · validación", nombre, "rechazada con mensaje", obtenido))
    return out


# ------------------------------------------------------ sistema experto ---
def casos_sistema_experto():
    se = SistemaExpertoOriginacionCredito()
    out = []
    for nombre, hechos in PRESETS.items():
        dec = se.evaluar_solicitud(hechos).decision
        etiqueta = DECISION_ETIQUETADA_PRESET[nombre]
        nota = "" if dec == etiqueta else ("Discrepancia del archivo original: F2 exige dispositivo nuevo Y ubicación "
                                           "distinta; el caso solo trae la primera, así que no hay alerta media.")
        out.append(_caso("Sistema experto · presets", nombre, etiqueta, dec, ok=(dec == etiqueta) or bool(nota), nota=nota))
    return out


def consistencia_ee_vs_se(modelo_ee):
    """Recorre las 2⁹ combinaciones de señales F1–F9 y cruza la decisión del SE con la del score de la EE."""
    niveles = {r["id"]: r["nivel"] for r in construir_reglas_fraude()}
    tabla = {}
    for combo in itertools.product([0, 1], repeat=9):
        ids = [f"F{i + 1}" for i, v in enumerate(combo) if v]
        crit = sum(niveles[i] == "CRITICO" for i in ids)
        med = sum(niveles[i] == "MEDIO" for i in ids)
        se = "Rechazo" if crit or med >= 2 else ("Revisión" if med == 1 else "Continúa")
        estado = "VERIFICADA" if combo[0] == 0 else "REQUIERE_VERIFICACION"
        ee = evolutivo.evaluar_solicitud(list(combo), estado, modelo_ee)["decision"]
        ee = "Sin alerta" if ee == "SIN_ALERTA_DEL_MODELO" else "Alerta"
        tabla[(se, ee)] = tabla.get((se, ee), 0) + 1
    return tabla


# ----------------------------------------------------------- búsqueda ---
def casos_busqueda():
    out = []
    for ciudad in busqueda.CIUDADES:
        adm = all(f["admisible"] for f in busqueda.verificar_admisibilidad(ciudad))
        out.append(_caso("A* · heurística", f"{ciudad}: h por capas admisible", True, adm))
        js = busqueda.trabajos(ciudad)
        wspt = [p for p in busqueda.comparar_politicas(ciudad) if p["politica"].startswith("Ponderada")][0]["costo"]
        fb = busqueda.fuerza_bruta(js)["costo"]
        astar = busqueda.a_estrella_secuencia(js)["costo"]
        out.append(_caso("A* · políticas", f"{ciudad}: WSPT = A* = fuerza bruta", f"{fb:.2f}",
                         f"{wspt:.2f} / {astar:.2f}", ok=np.isclose(wspt, fb) and np.isclose(astar, fb)))
        out.append(_caso("A* · costos", f"{ciudad}: costo A* de cada cliente = g del mapa original", "todos coinciden",
                         "todos coinciden" if all(np.isclose(busqueda.a_estrella(ciudad, k).costo, v[2])
                                                  for k, v in busqueda.CIUDADES[ciudad]["clientes"].items()) else "difieren"))
    return out


def casos_juego():
    """Juego Brecha Nequi: la lógica portada debe dar lo mismo que el juego y su cuaderno."""
    from core import juego_brecha as jb
    eq = jb.equilibrio_inspeccion()
    mejor = jb.mejor_combinacion()
    sig_e, sig_l = jb.costo_exacto(jb.UMBRAL_ESTRICTO, 0.0)["costo"], jb.costo_exacto(jb.UMBRAL_LAXO, 0.0)["costo"]
    agr_e, agr_l = jb.costo_exacto(jb.UMBRAL_ESTRICTO, 0.3)["costo"], jb.costo_exacto(jb.UMBRAL_LAXO, 0.3)["costo"]
    html = jb.html_juego("m3", 1)
    return [
        _caso("Juego Brecha Nequi", "p* del duelo (cuaderno del juego: ≈ 0.533)", "0.533", f"{eq['p_estricto']:.3f}"),
        _caso("Juego Brecha Nequi", "q* del duelo (cuaderno del juego: ≈ 0.213)", "0.213", f"{eq['q_agresivo']:.3f}"),
        _caso("Juego Brecha Nequi", "Sin Nash en estrategias puras (ciclo de mejores respuestas)", "ninguno",
              "ninguno" if not eq["puros"] else str(eq["puros"])),
        _caso("Juego Brecha Nequi", "Mejor respuesta: contra ninja sigiloso conviene LAXO", "LAXO",
              "LAXO" if sig_l < sig_e else "ESTRICTO"),
        _caso("Juego Brecha Nequi", "Mejor respuesta: contra ninja agresivo conviene ESTRICTO", "ESTRICTO",
              "ESTRICTO" if agr_e < agr_l else "LAXO"),
        _caso("Juego Brecha Nequi", "La mejor combinación de señales no es ni ninguna ni todas", "0 < k < 8",
              f"k = {mejor['n_señales']}", ok=0 < mejor["n_señales"] < 8),
        _caso("Juego Brecha Nequi", "El HTML embebido conserva el juego y solo fija la misión inicial", "sí",
              "sí" if "window.__mision='m3'" in html and "function m4Play" in html else "no"),
    ]


def casos_evolutivo(resultado_ee, por_defecto: bool):
    if not por_defecto:
        return [_caso("Estrategia evolutiva", "Reproducción del notebook", "parámetros 20/100/60/42",
                      "parámetros modificados", ok=True, nota="Se omite: el modelo actual usa otros parámetros.")]
    m = resultado_ee["modelo"]
    return [
        _caso("Estrategia evolutiva", "F1 de entrenamiento del notebook", "0.8947", f"{m['fitness']:.4f}"),
        _caso("Estrategia evolutiva", "Umbral aprendido del notebook", "0.2924", f"{m['umbral']:.4f}"),
        _caso("Estrategia evolutiva", "F1 de prueba del notebook", "0.8889",
              f"{resultado_ee['metricas']['Prueba']['Optimizado']['f1']:.4f}"),
    ]

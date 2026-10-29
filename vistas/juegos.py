from dataclasses import asdict

import numpy as np
import pandas as pd
import streamlit as st

from core import teoria_juegos as tj, teoria_juegos_v4 as v4
from ui import estado
from ui.componentes import COLOR_PRIMARIO, grafico_barras_h, grafico_lineas

st.title("Sprint 3 · Teoría de juegos con coevolución")
st.caption("Defensor (motor antifraude) contra atacante (red de fraude). Cada bando es una población que evoluciona "
           "con (μ+λ), y el fitness de cada individuo es su **pago** contra la población rival. La evolución se usa para "
           "encontrar un equilibrio sin resolverlo con álgebra, y después se verifica con herramientas de teoría de juegos.")
st.markdown("**Clasificación del juego:** no cooperativo, simultáneo y de suma no cero. Se resuelve con Nash y no con "
            "Minimax, porque el atacante maximiza su propia ganancia, no la pérdida del rival.")

tab_v2, tab_v4 = st.tabs(["Modelo integrado · pagos económicos (F1–F10)", "Modelo simplificado v4"])

# ------------------------------------------------------------------ v2 ---
with tab_v2:
    st.caption("Fuente: `Teoria_d_ejuegos (1).ipynb` (teoria_juegos_nequi_v2). Usa las mismas señales F1–F9 del sistema "
               "experto más F10 (patrón de red), que el atacante no controla. Con los valores por defecto reproduce la "
               "corrida del notebook.")
    base = asdict(tj.SUPUESTOS_BASE)
    with st.form("v2"):
        st.markdown("##### Supuestos del modelo")
        c = st.columns(4)
        sup = {
            "prevalencia": c[0].number_input("Prevalencia de fraude", 0.001, 0.5, base["prevalencia"], 0.005, format="%.3f"),
            "beneficio_por_señal": c[1].number_input("Botín extra por señal F2–F9", 0.0, 5.0, base["beneficio_por_señal"], 0.1),
            "costo_falso_positivo": c[2].number_input("Costo de un falso positivo", 0.0, 5.0, base["costo_falso_positivo"], 0.05),
            "p_fraude_f10": c[3].number_input("F10 en fraude", 0.0, 1.0, base["p_fraude_f10"], 0.05),
        }
        c = st.columns(4)
        rondas = c[0].number_input("Rondas", 1, 200, 30)
        mu = c[1].number_input("μ", 2, 50, 10)
        lam = c[2].number_input("λ", 1, 200, 30)
        semilla = c[3].number_input("Semilla", 0, 10_000, 42)
        desv = st.checkbox("Incluir el test de desviación unilateral (ε-Nash, 200 mutantes por jugador; tarda más)", True)
        st.form_submit_button("Ejecutar coevolución", type="primary")
    sup_full = {**base, **sup}
    with st.spinner("Coevolucionando defensores y atacantes…"):
        R = estado.correr_juego_v2(int(rondas), int(mu), int(lam), int(semilla), sup_full, desv)
    if sup_full != base or (rondas, mu, lam, semilla) != (30, 10, 30, 42):
        st.info("Supuestos o parámetros distintos a los del notebook: los resultados no se comparan con la corrida original.")

    h = pd.DataFrame(R["historial"])
    a, b = st.columns(2, gap="large")
    a.plotly_chart(grafico_lineas(h["ronda"], {"Botín del mejor atacante": h["pago_atk"]},
                                  "Pago del atacante por ronda", "Ronda", "Valor robado por intento"), width="stretch")
    b.plotly_chart(grafico_lineas(h["ronda"], {"Umbral medio del defensor": h["umbral_def"],
                                              "Intensidad media del atacante": h["intensidad_atk"]},
                                  "Umbral e intensidad", "Ronda", ""), width="stretch")

    a, b = st.columns(2, gap="large")
    pesos = np.array(R["mejor_def"]["pesos"])
    a.plotly_chart(grafico_barras_h(tj.NOMBRES_PESOS, pesos / pesos.sum(),
                                    f"Defensor final · umbral {R['mejor_def']['umbral']:.3f}"), width="stretch")
    b.plotly_chart(grafico_barras_h(tj.NOMBRES_ATK, R["mejor_atk"]["genes"],
                                    "Atacante final · probabilidad de activar cada señal", "{:.2f}", COLOR_PRIMARIO),
                   width="stretch")

    m = R["reevaluacion"]
    st.markdown("##### Re-evaluación con datos nuevos")
    k = st.columns(5)
    k[0].metric("Fraude detectado", f"{m['recall']:.1%}")
    k[1].metric("Clientes bloqueados", f"{m['fpr']:.1%}")
    k[2].metric("Precisión (prevalencia real)", f"{m['precision']:.3f}")
    k[3].metric("Botín por intento", f"{m['pago_atk']:.3f}")
    k[4].metric("Costo del defensor por 1 000 tx", f"{-1000 * m['pago_def']:.2f}")

    st.markdown("##### Matriz de pagos entre los 5 mejores de cada población")
    A, B = np.array(R["matriz"]["A"]), np.array(R["matriz"]["B"])
    celdas = pd.DataFrame([[f"({A[i, j] * 1000:.2f} ; {B[i, j]:.3f})" for j in range(A.shape[1])] for i in range(A.shape[0])],
                          index=[f"D{i + 1}" for i in range(A.shape[0])], columns=[f"A{j + 1}" for j in range(A.shape[1])])
    st.dataframe(celdas, width="stretch")
    st.caption("Cada celda: (pago del defensor ×1000 ; pago del atacante).")
    mx = R["matriz"]["maximin"]
    puros = R["matriz"]["nash_puros"]
    k = st.columns(3)
    k[0].metric("Nash puros", ", ".join(f"(D{i + 1}, A{j + 1})" for i, j in puros) or "ninguno")
    k[1].metric("Dominancia estricta", f"defensor: {len(R['matriz']['dominancia_def'])} · atacante: {len(R['matriz']['dominancia_atk'])}")
    k[2].metric("Maximin", f"D{mx['def_idx'] + 1} · A{mx['atk_idx'] + 1}")
    st.caption(f"Dispersión entre celdas: defensor {A.std() * 1000:.3f} ‰ · atacante {B.std():.3f}. Con dispersión baja, "
               "las estrategias finales son casi equivalentes y los Nash puros dependen del ruido de la simulación.")

    if "desviacion" in R:
        t = R["desviacion"]
        st.markdown("##### Test de desviación unilateral (ε-Nash)")
        st.dataframe(pd.DataFrame([
            {"Jugador": "Defensor", "Pago base": t["def_base"], "Mejor ganancia de un mutante (ε)": t["def_max_mejora"],
             "% de mutantes que mejoran > 2 %": t["def_pct_mejoran"]},
            {"Jugador": "Atacante", "Pago base": t["atk_base"], "Mejor ganancia de un mutante (ε)": t["atk_max_mejora"],
             "% de mutantes que mejoran > 2 %": t["atk_pct_mejoran"]}]), hide_index=True, width="stretch",
            column_config={"% de mutantes que mejoran > 2 %": st.column_config.NumberColumn(format="percent")})
        if t["def_pct_mejoran"] < 0.05 and t["atk_pct_mejoran"] < 0.05:
            st.success("Ningún jugador gana desviándose solo: hay evidencia de un equilibrio de Nash local (aproximado).")
        else:
            st.warning("Algún jugador todavía puede mejorar si se desvía: es un equilibrio aproximado, no exacto.")

    st.markdown("##### Comparación con una regla fija de línea base")
    st.dataframe(pd.DataFrame(R["linea_base"]), hide_index=True, width="stretch",
                 column_config={"recall": st.column_config.NumberColumn("Fraude detectado", format="percent"),
                                "fpr": st.column_config.NumberColumn("Clientes bloqueados", format="percent"),
                                "costo_por_1000_tx": st.column_config.NumberColumn("Costo por 1 000 tx", format="%.2f"),
                                "botin_atacante": st.column_config.NumberColumn("Botín del atacante", format="%.3f")})

    st.markdown("##### Juego de inspección 2×2 (solución analítica)")
    I = R["inspeccion"]
    A2, B2 = np.array(I["A"]), np.array(I["B"])
    st.dataframe(pd.DataFrame([[f"({A2[i, j] * 1000:.2f} ; {B2[i, j]:.3f})" for j in range(2)] for i in range(2)],
                              index=[f"ESTRICTO (umbral {tj.UMBRAL_ESTRICTO})", f"LAXO (umbral {tj.UMBRAL_LAXO})"],
                              columns=[f"AGRESIVO ({tj.INTENSIDAD_AGRESIVO:.0%} por señal)", "SIGILOSO (sin señales)"]),
                 width="stretch")
    if I["valido"]:
        k = st.columns(4)
        k[0].metric("P(defensor ESTRICTO) = p*", f"{I['p']:.3f}")
        k[1].metric("P(atacante AGRESIVO) = q*", f"{I['q']:.3f}")
        k[2].metric("Umbral esperado (2×2 vs. evolución)",
                    f"{I['p'] * tj.UMBRAL_ESTRICTO + (1 - I['p']) * tj.UMBRAL_LAXO:.3f}", f"evolución {R['umbral_evo']:.3f}",
                    delta_color="off")
        k[3].metric("Intensidad esperada (2×2 vs. evolución)", f"{I['q'] * tj.INTENSIDAD_AGRESIVO:.3f}",
                    f"evolución {R['intensidad_evo']:.3f}", delta_color="off")
        st.caption("Equilibrio mixto por condiciones de indiferencia: q* deja al defensor indiferente entre ESTRICTO y LAXO, y "
                   "p* deja al atacante indiferente entre AGRESIVO y SIGILOSO. El 2×2 solo permite dos estrategias por jugador; "
                   "la coevolución explora un espacio continuo. Si coinciden en dirección, la evolución encuentra el mismo tipo "
                   "de equilibrio que el álgebra.")
    else:
        st.info("Con estos supuestos el juego reducido no tiene un equilibrio mixto interior: se resuelve en estrategias puras.")

# ------------------------------------------------------------------ v4 ---
with tab_v4:
    st.caption("Fuente: `Teoria_de_juegos_nequi_v4_simple.ipynb`. Es un modelo aparte con **supuestos distintos** al resto "
               "del proyecto: sus señales F1–F8 son señales de transacción (dispositivo nuevo, monto alto, …) y no las reglas "
               "del sistema experto. La prevalencia es 4 %, la penalización por falso positivo 0.5 y el botín extra por señal 0.5. "
               "Por eso no alimenta el flujo integrado.")
    st.markdown("##### ¿Por qué no basta con bloquear todo? (barrido del umbral)")
    st.dataframe(pd.DataFrame(estado.barrido_v4()), hide_index=True, width="stretch",
                 column_config={"fraude_detectado": st.column_config.NumberColumn("Fraude detectado", format="%.3f"),
                                "clientes_bloqueados": st.column_config.NumberColumn("Clientes bloqueados", format="%.3f"),
                                "costo_defensor": st.column_config.NumberColumn("Costo del defensor", format="%.3f"),
                                "umbral_puntos": "Umbral (puntos)"})
    if st.button("Ejecutar la coevolución v4 (60 rondas, lotes de 3 000 tx; tarda alrededor de un minuto)"):
        st.session_state["v4_on"] = True
    if st.session_state.get("v4_on"):
        with st.spinner("Ejecutando el modelo v4…"):
            R4 = estado.correr_juego_v4(42)
        h4 = pd.DataFrame(R4["historia"])
        a, b = st.columns(2)
        a.plotly_chart(grafico_lineas(h4["ronda"], {"Atacante": h4["pago_atk"]}, "Ganancia del atacante por intento",
                                      "Ronda", ""), width="stretch")
        b.plotly_chart(grafico_lineas(h4["ronda"], {"Defensor": h4["pago_def"]}, "Pago del defensor por transacción",
                                      "Ronda", ""), width="stretch")
        st.dataframe(pd.DataFrame({"Legítimas incumplen": v4.P_LEGIT, "Atacante inicial": v4.ATACANTE_INICIAL,
                                   "Atacante final (mejor)": R4["mejor_atk"], "Peso final del defensor": R4["mejor_def"]["pesos"]},
                                  index=v4.NOMBRES).round(2), width="stretch")
        st.caption(f"Umbral de bloqueo: inicial {v4.UMBRAL_INICIAL:.1f} puntos → mejor defensor {R4['mejor_def']['umbral']:.2f}.")
        I4 = R4["inspeccion"]
        A4, B4 = np.array(I4["A"]), np.array(I4["B"])
        st.dataframe(pd.DataFrame([[f"({A4[i, j] * 1000:.2f} ; {B4[i, j]:.3f})" for j in range(2)] for i in range(2)],
                                  index=["ESTRICTO (3 puntos)", "LAXO (5 puntos)"], columns=["AGRESIVO", "SIGILOSO"]),
                     width="stretch")
        if I4["valido"]:
            st.success(f"Equilibrio mixto: el defensor es ESTRICTO el {I4['p']:.0%} de las veces y el atacante AGRESIVO el {I4['q']:.0%}.")

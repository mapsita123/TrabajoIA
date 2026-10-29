import numpy as np
import pandas as pd
import streamlit as st

from core import evolutivo as ev
from ui import estado
from ui.componentes import COLOR_PRIMARIO, grafico_barras_h, grafico_lineas, matriz_confusion

st.title("Sprint 3 · Estrategia evolutiva (μ+λ)")
st.caption("Calibra los pesos de las señales F2–F9 y el umbral del score de fraude. La biometría (F1) no es un peso: "
           "es un control obligatorio previo. El fitness es el F1-score sobre el 70 % de entrenamiento, y la evaluación "
           "final se hace sobre el 30 % de prueba, que nunca se usa para seleccionar.")

estado.init()
p = st.session_state["ee_params"]
with st.form("ee"):
    c = st.columns(4)
    mu = c[0].number_input("μ (padres)", 1, 200, p["mu"])
    lam = c[1].number_input("λ (hijos)", 1, 1000, p["lambda_"])
    gens = c[2].number_input("Generaciones", 0, 500, p["generaciones"])
    semilla = c[3].number_input("Semilla", 0, 10_000, p["semilla"])
    b1, b2, _ = st.columns([1, 1, 3])
    if b1.form_submit_button("Entrenar", type="primary"):
        st.session_state["ee_params"] = {"mu": int(mu), "lambda_": int(lam), "generaciones": int(gens), "semilla": int(semilla)}
        st.session_state.pop("resultado_eval", None)
        st.rerun()
    if b2.form_submit_button("Valores del notebook", help="μ = 20, λ = 100, 60 generaciones, semilla 42"):
        st.session_state["ee_params"] = {"mu": ev.MU, "lambda_": ev.LAMBDA, "generaciones": ev.GENERACIONES, "semilla": ev.SEMILLA}
        st.session_state.pop("resultado_eval", None)
        st.rerun()

r = estado.resultado_ee()
mod, cnt, met = r["modelo"], r["conteos"], r["metricas"]
if estado.ee_personalizada():
    st.warning("Modelo entrenado con parámetros distintos a los del notebook. La evaluación integrada usa este modelo.")

k = st.columns(4)
k[0].metric("F1 en entrenamiento", f"{mod['fitness']:.4f}")
k[1].metric("F1 en prueba", f"{met['Prueba']['Optimizado']['f1']:.4f}",
            f"{met['Prueba']['Optimizado']['f1'] - met['Prueba']['Base']['f1']:+.4f} vs. base")
k[2].metric("Umbral aprendido", f"{mod['umbral']:.4f}")
k[3].metric("σ final", f"{mod['sigma']:.4f}")

st.markdown(f"**Control biométrico:** de {cnt['total']} solicitudes simuladas, {cnt['detenidas']} quedan detenidas por F1 "
            f"({cnt['detenidas_fraude']} fraudes) y {cnt['habilitadas']} pasan al score ({cnt['habilitadas_fraude']} fraudes). "
            f"Entrenamiento: {cnt['train']} ({cnt['train_fraude']} fraudes) · prueba: {cnt['test']} ({cnt['test_fraude']} fraudes).")

a, b = st.columns(2, gap="large")
with a:
    rel = mod["pesos"] / mod["pesos"].sum() if mod["pesos"].sum() > 0 else np.zeros_like(mod["pesos"])
    st.plotly_chart(grafico_barras_h(ev.CRITERIOS_SCORE, rel, "Peso relativo de cada señal en el score",
                                     color=COLOR_PRIMARIO), width="stretch")
    st.caption("Los pesos relativos no son probabilidades de fraude.")
with b:
    h = pd.DataFrame(r["historial"])
    st.plotly_chart(grafico_lineas(h["generacion"], {"Mejor F1": h["mejor_fitness"], "F1 promedio": h["fitness_promedio"]},
                                   "Evolución del fitness", "Generación (0 = población inicial)", "F1 en entrenamiento"),
                    width="stretch")

st.subheader("Base frente a optimizado")
st.caption("Base = todos los pesos iguales y umbral 0.5, la línea base del notebook.")
filas = [{"Conjunto": conj, "Modelo": nombre, **{k2.upper() if len(k2) == 2 else k2.capitalize(): v for k2, v in m.items()}}
         for conj, d in met.items() for nombre, m in d.items()]
st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch",
             column_config={c: st.column_config.NumberColumn(format="%.4f") for c in ("F1", "Precision", "Recall")})
c1, c2 = st.columns(2)
c1.plotly_chart(matriz_confusion(met["Prueba"]["Base"], "Prueba · modelo base"), width="stretch")
c2.plotly_chart(matriz_confusion(met["Prueba"]["Optimizado"], "Prueba · modelo optimizado"), width="stretch")

st.subheader("Probar el score con un conjunto de señales")
st.caption("Mismo simulador del notebook. En la página de evaluación estas señales salen de las reglas del sistema experto.")
cols = st.columns(5)
estado_bio = cols[0].selectbox("Estado biométrico", ["VERIFICADA", "REQUIERE_VERIFICACION", "PENDIENTE"])
señales = [int(cols[(i + 1) % 5].checkbox(nombre.split("_", 1)[0] + " · " + nombre.split("_", 1)[1].replace("_", " "),
                                          key=f"sig_{i}")) for i, nombre in enumerate(ev.NOMBRES_REGLAS)]
res = ev.evaluar_solicitud(señales, estado_bio, mod)
if res["score"] is None:
    st.error(f"**{res['decision']}** · {res['motivo']}")
else:
    (st.error if res["decision"] == "ALERTA_DE_RIESGO" else st.success)(
        f"**{res['decision']}** · score {res['score']:.4f} vs. umbral {res['umbral']:.4f}. {res['motivo']}")

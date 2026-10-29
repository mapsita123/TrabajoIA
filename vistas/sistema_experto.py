import pandas as pd
import streamlit as st

from core.sistema_experto import (DEFAULT_PARAMS, GLOSARIO, PRESETS, SistemaExpertoOriginacionCredito,
                                  condiciones_legibles)
from ui import estado
from ui.componentes import texto_decision

st.title("Sprint 2 · Sistema experto de doble motor")
st.caption("Dos motores de encadenamiento hacia adelante e independientes: identidad (F1–F9) y crédito (C1–C9). "
           "El de fraude se evalúa siempre primero, y su cortocircuito evita consultar las centrales de riesgo "
           "cuando el fraude ya es evidente.")

a, b = st.columns(2, gap="large")
with a, st.container(border=True):
    st.markdown("**Motor de fraude (cortocircuito)**")
    st.markdown("- 1 o más reglas **críticas** (F1, F4, F5, F7) → rechazo por fraude\n"
                "- 2 o más reglas **medias** (F2, F3, F6, F8, F9) → rechazo por fraude\n"
                "- Exactamente 1 regla media → revisión manual\n"
                "- 0 reglas → pasa al motor de crédito")
with b, st.container(border=True):
    st.markdown("**Motor de crédito**")
    st.markdown("- 1 o más reglas de **rechazo** (C1–C7) → rechazo por riesgo financiero\n"
                "- 0 reglas de rechazo → aprobado\n"
                "- C8 y C9 son **favorables**: no deciden, solo resaltan al cliente de menor riesgo")

st.subheader("Umbrales de las reglas")
st.caption("Estos son los valores por defecto del archivo del Sprint 2. Si los cambias, se aplican a toda la aplicación "
           "durante esta sesión y la página de evaluación lo indica.")
p = estado.params_se()
ETIQUETAS = {
    "F1": ("F1 · match facial mínimo", 0.0, 1.0, 0.01), "F3": ("F3 · minutos mínimos registro→solicitud", 0.0, 1440.0, 1.0),
    "F4": ("F4 · máximo de solicitudes por dispositivo", 0.0, 100.0, 1.0), "F8": ("F8 · intentos OTP fallidos", 0.0, 20.0, 1.0),
    "C1": ("C1 · score mínimo", 150.0, 950.0, 1.0), "C2": ("C2 · cuota/ingresos máxima", 0.0, 1.0, 0.01),
    "C3": ("C3 · días de mora máximos", 0.0, 365.0, 1.0), "C4": ("C4 · DTI máximo", 0.0, 2.0, 0.01),
    "C5": ("C5 · antigüedad laboral mínima (meses)", 0.0, 120.0, 1.0), "C8": ("C8 · score de historial excelente", 150.0, 950.0, 1.0),
    "C9": ("C9 · cuota/ingresos holgada", 0.0, 1.0, 0.01),
}
with st.form("umbrales"):
    cols = st.columns(4)
    nuevos = {}
    for i, (rid, (etq, lo, hi, paso)) in enumerate(ETIQUETAS.items()):
        nuevos[rid] = cols[i % 4].number_input(etq, lo, hi, float(p[rid]), paso, key=f"umbral_{rid}")
    c1, c2, _ = st.columns([1, 1, 3])
    aplicar = c1.form_submit_button("Aplicar umbrales", type="primary")
    restablecer = c2.form_submit_button("Restablecer valores del Sprint 2")
if aplicar:
    st.session_state["params_se"] = {**DEFAULT_PARAMS, **nuevos}
    st.session_state.pop("resultado_eval", None)
    st.rerun()
if restablecer:
    st.session_state["params_se"] = dict(DEFAULT_PARAMS)
    for rid in ETIQUETAS:
        st.session_state.pop(f"umbral_{rid}", None)
    st.session_state.pop("resultado_eval", None)
    st.rerun()
if estado.se_personalizado():
    cambios = [f"{k}: {DEFAULT_PARAMS[k]:g} → {v:g}" for k, v in p.items() if v != DEFAULT_PARAMS[k]]
    st.warning("Umbrales modificados en esta sesión: " + " · ".join(cambios))

st.subheader("Diccionario de reglas")
cond = condiciones_legibles(p)
filtro = st.segmented_control("Mostrar", ["Todas", "Fraude (F1–F9)", "Crédito (C1–C9)"], default="Todas")
filas = [{"Regla": rid, "Consecuencia": cons, "Nivel": nivel, "Condición vigente": cond[rid], "Por qué existe": porque}
         for rid, (cons, nivel, porque) in GLOSARIO.items()
         if filtro in (None, "Todas") or (filtro.startswith("Fraude") and rid[0] == "F") or (filtro.startswith("Crédito") and rid[0] == "C")]
st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")

st.subheader("Casos predefinidos del simulador original")
se = SistemaExpertoOriginacionCredito(p)
tabla = []
for nombre, hechos in PRESETS.items():
    r = se.evaluar_solicitud(hechos)
    tabla.append({"Caso": nombre, "Decisión del motor": texto_decision(r.decision),
                  "Auditoría fraude": ", ".join(r.auditoria_fraude) or "—",
                  "Auditoría crédito": ", ".join(r.auditoria_credito) or "—"})
st.dataframe(pd.DataFrame(tabla), hide_index=True, width="stretch")
st.caption("El Caso 4 está etiquetado como «revisión manual» en el archivo original, pero con sus propias reglas el motor lo "
           "aprueba: F2 exige dispositivo nuevo **y** ubicación distinta, y el caso solo trae la primera. Se conserva sin "
           "cambios y se reporta en Validación.")
st.page_link("vistas/evaluar.py", label="Evaluar cualquiera de estos casos paso a paso", icon=":material/arrow_forward:")

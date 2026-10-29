import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import difuso
from core.integracion import REGLAS_RIGIDAS_NO_DIFUSAS
from ui import estado
from ui.componentes import COLOR_PRIMARIO, grafico_pertenencia, grafico_salida, tarjeta_decision

st.title("Sprint 4 · Lógica difusa para el riesgo crediticio")
st.caption("Una capa Mamdani sobre las tres variables numéricas del motor de crédito, para que una diferencia mínima "
           "en los datos ya no cambie por completo la decisión.")

p_se = estado.params_se()
cfg = estado.config_difusa()

with st.expander("¿Por qué lógica difusa y por qué Mamdani?", expanded=True):
    st.markdown(f"""
**El problema.** El motor de crédito del Sprint 2 usa fronteras rígidas: con `score < {p_se['C1']:g}` (C1) un score de
{p_se['C1'] - 1:g} se rechaza y uno de {p_se['C1']:g} se aprueba. Lo mismo pasa con la carga de la cuota (C2 > {p_se['C2']:g})
y con el endeudamiento (C4 > {p_se['C4']:g}). El sistema binario no puede expresar que un perfil está *cerca* de un
umbral, ni ofrecer un desenlace intermedio para el crédito.

**Qué aporta.** Cada valor pertenece en parte a varias categorías («score medio en 0.5 y bajo en 0.5»). Las reglas
se combinan en un **riesgo continuo de 0 a 100**, y aparece una **zona de revisión manual** para los perfiles cercanos a las
fronteras.

**Alternativa elegida: Mamdani** (fuzzificación → reglas con mínimo → agregación con máximo → centroide).
- Sus reglas y su salida son conjuntos lingüísticos («riesgo alto»). Eso conserva la **explicabilidad regla por regla** que
  exige el Sprint 2 (KYC/AML, XAI).
- Es el método del notebook de clase, así que el motor (trimf, trapmf, centroide) se reutiliza tal cual.
- Se descartó **Sugeno**: su consecuente es una función numérica. Es eficiente y fácil de optimizar, pero menos legible
  para un analista de crédito. Se descartó **Tsukamoto** porque exige conjuntos de salida monótonos y pierde la etiqueta
  «medio» que define la revisión manual.

**Qué no cambia.** El motor de fraude sigue siendo rígido y va primero: la lista AML/OFAC, la biometría o la granja de
dispositivos no admiten grados por razones regulatorias y de seguridad. En crédito, las reglas
{", ".join(sorted(REGLAS_RIGIDAS_NO_DIFUSAS))} (mora, antigüedad laboral, ingreso mínimo del producto y embargo) siguen
siendo filtros rígidos. La capa difusa reemplaza solo C1, C2 y C4, y usa C8 y C9 como base de las reglas favorables.
""")

st.subheader("Variables y funciones de pertenencia")
st.caption("Regla de anclaje: cada umbral del sistema experto es el punto de cruce μ = 0.5 entre dos conjuntos vecinos. "
           "La frontera rígida queda en el centro de la transición y no se mueve. El **ancho** de la transición es una "
           "decisión de modelado (no viene de los archivos) y se puede ajustar aquí.")

anchos = st.session_state["anchos_difusos"]
with st.form("anchos"):
    c = st.columns(3)
    nuevos = {
        "score": c[0].number_input("Semiancho de la transición del score (pts)", 1.0, 70.0, float(anchos["score"]), 5.0),
        "carga": c[1].number_input("Semiancho de la carga de la cuota", 0.005, 0.07, float(anchos["carga"]), 0.005, format="%.3f"),
        "dti": c[2].number_input("Semiancho del DTI", 0.01, 0.25, float(anchos["dti"]), 0.01),
    }
    b1, b2, _ = st.columns([1, 1, 3])
    aplicar = b1.form_submit_button("Aplicar", type="primary")
    restablecer = b2.form_submit_button("Valores por defecto", help="50 pts · 0.05 · 0.10")
if aplicar or restablecer:
    candidato = dict(difuso.ANCHOS_BASE) if restablecer else nuevos
    try:
        difuso.validar_config(difuso.construir_config(p_se, candidato))
        st.session_state["anchos_difusos"] = candidato
        st.session_state.pop("resultado_eval", None)
        st.rerun()
    except ValueError as e:
        st.error(f"Esos anchos hacen que los conjuntos se crucen o se salgan del universo: {e} "
                 "Usa un semiancho menor que la mitad de la distancia entre umbrales vecinos.")

UMBRALES_VAR = {"score": [(p_se["C1"], f"C1 = {p_se['C1']:g}"), (p_se["C8"], f"C8 = {p_se['C8']:g}")],
                "carga": [(p_se["C9"], f"C9 = {p_se['C9']:g}"), (p_se["C2"], f"C2 = {p_se['C2']:g}")],
                "dti": [(p_se["C4"], f"C4 = {p_se['C4']:g}")]}
cols = st.columns(3)
filas_var = []
for col, (clave, var) in zip(cols, cfg["variables"].items()):
    u, cs = difuso.curvas(var)
    col.plotly_chart(grafico_pertenencia(u, cs, var["nombre"], eje_x=var["unidad"], umbrales=UMBRALES_VAR[clave]),
                     width="stretch")
    for etq, (tipo, params) in var["conjuntos"].items():
        filas_var.append({"Variable": var["nombre"], "Universo": f"{var['universo'][0]:g} – {var['universo'][1]:g}",
                          "Conjunto": etq, "Función": tipo, "Parámetros": ", ".join(f"{x:g}" for x in params),
                          "Procedencia": var["fuente"]})
for etq, (tipo, params) in cfg["salida"]["conjuntos"].items():
    filas_var.append({"Variable": "Riesgo crediticio (salida)", "Universo": "0 – 100", "Conjunto": etq, "Función": tipo,
                      "Parámetros": ", ".join(f"{x:g}" for x in params),
                      "Procedencia": "Conjuntos de salida del notebook de lógica difusa de clase"})
with st.expander("Tabla de conjuntos difusos"):
    st.dataframe(pd.DataFrame(filas_var), hide_index=True, width="stretch")
    st.caption("Se usan trapecios porque cada categoría tiene una meseta de pertenencia total y su frontera viene de un umbral "
               "de política. El triángulo de la salida «medio» viene del notebook de clase. Se descartaron las gaussianas "
               "porque nunca llegan a 0 y harían que todas las reglas se activaran un poco, lo que dificulta la auditoría. "
               "Los universos del score (150–950) y de las razones (0–1, saturando valores mayores) son decisiones declaradas "
               "en `core/difuso.py`.")

st.subheader("Base de reglas")
st.dataframe(pd.DataFrame([{"Regla": r["id"], "Enunciado": r["texto"], "Relación con el sistema experto": r["origen"]}
                           for r in difuso.REGLAS]), hide_index=True, width="stretch")
st.caption(f"Las 7 reglas cubren todo el espacio de entradas: en cualquier combinación, al menos una se activa con grado "
           f"≥ {difuso.cobertura_reglas(cfg, pasos=11):.2f}. R7 es la única regla nueva: corresponde a un perfil que el sistema "
           "rígido aprueba sin ninguna regla favorable (score entre C1 y C8, carga entre C9 y C2) y que aquí se marca para "
           "revisión. Las etiquetas de salida se traducen a acciones así: bajo → aprobar, medio → revisión manual, alto → rechazar.")

st.subheader("Probar la inferencia")
c = st.columns(3)
s = c[0].slider("Score", 150, 950, 640, 1)
cg = c[1].slider("Cuota / ingresos", 0.0, 1.0, 0.28, 0.01)
dt = c[2].slider("Deuda total / ingresos", 0.0, 1.0, 0.40, 0.01)
res = difuso.inferir({"score": s, "carga": cg, "dti": dt}, cfg)
crisp = ("rechazo" if (s < p_se["C1"] or cg > p_se["C2"] or dt > p_se["C4"]) else "aprobación")
a, b = st.columns([1, 1.4], gap="large")
with a:
    tarjeta_decision(res["accion"], f"Riesgo {res['riesgo']:.1f} / 100 · etiqueta dominante «{res['etiqueta']}». "
                                    f"Con las fronteras rígidas de C1, C2 y C4 sería {crisp}.", "Salida difusa")
    st.dataframe(pd.DataFrame([{"Regla": x["id"], "Activación": x["activacion"]} for x in res["reglas"]]),
                 hide_index=True, width="stretch",
                 column_config={"Activación": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
with b:
    for clave, var in cfg["variables"].items():
        g = res["grados"][clave]
        st.caption(f"**{var['nombre']}** → " + " · ".join(f"{k}: {v:.2f}" for k, v in g.items()))
    st.plotly_chart(grafico_salida(res, cfg["salida"]), width="stretch")


@st.cache_data(show_spinner=False)
def superficie(umbrales: tuple, anchos: tuple, dti: float, n=41):
    cfg_local = difuso.construir_config(dict(umbrales), dict(anchos))
    ss = np.linspace(400, 900, n)
    cc = np.linspace(0.0, 0.6, n)
    z = np.array([[difuso.inferir({"score": x, "carga": y, "dti": dti}, cfg_local)["riesgo"] for x in ss] for y in cc])
    return ss, cc, z


st.subheader("Superficie de decisión: rígida frente a difusa")
dti_fijo = st.slider("DTI fijo para la superficie", 0.0, 1.0, 0.30, 0.05)
ss, cc, z = superficie(tuple(sorted(p_se.items())), tuple(sorted(st.session_state["anchos_difusos"].items())), dti_fijo)
fig = go.Figure(go.Heatmap(x=ss, y=cc, z=z, colorscale=[[0, "#16A34A"], [0.5, "#F59E0B"], [1, "#DC2626"]],
                           zmin=0, zmax=100, colorbar=dict(title="Riesgo")))
fig.add_vline(x=p_se["C1"], line_dash="dash", line_color="white", annotation_text=f"C1 rígida ({p_se['C1']:g})")
fig.add_hline(y=p_se["C2"], line_dash="dash", line_color="white", annotation_text=f"C2 rígida ({p_se['C2']:g})")
fig.update_layout(height=420, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Score", yaxis_title="Cuota / ingresos")
st.plotly_chart(fig, width="stretch")
st.caption("Las líneas punteadas son las fronteras rígidas del Sprint 2: el sistema clásico solo aprueba en el rectángulo de "
           "abajo a la derecha. La capa difusa reemplaza esos saltos por una transición gradual, y la franja ámbar es la "
           "zona de revisión manual.")

x = np.linspace(450, 850, 161)
riesgo = [difuso.inferir({"score": v, "carga": 0.20, "dti": 0.30}, cfg)["riesgo"] for v in x]
rigido = [100 if v < p_se["C1"] else 0 for v in x]
fig2 = go.Figure([go.Scatter(x=x, y=riesgo, name="Riesgo difuso", line=dict(color=COLOR_PRIMARIO, width=2.5)),
                  go.Scatter(x=x, y=rigido, name="Sistema rígido (0 = aprueba, 100 = rechaza)", line=dict(color="gray", dash="dot", shape="hv"))])
fig2.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), title="Corte en carga 0.20 y DTI 0.30",
                   xaxis_title="Score", yaxis_title="Riesgo", legend=dict(orientation="h", y=-0.3))
st.plotly_chart(fig2, width="stretch")

with st.expander("Extensión posible: sistema genético-difuso"):
    st.markdown("Los semianchos de transición son la parte del modelo que no viene de los archivos. La estrategia evolutiva "
                "del Sprint 3 podría calibrarlos (individuo = 3 semianchos + σ, fitness = costo de los errores sobre un histórico "
                "etiquetado). **No está implementado**: no hay un histórico etiquetado de crédito en el material del proyecto, "
                "y simularlo sería inventar datos.")

import pandas as pd
import streamlit as st

from core import casos_prueba as cp
from ui import estado

st.title("Validación y pruebas")
st.caption("Casos ejecutados en vivo contra el código de la aplicación. Son los mismos que corre `pytest` en `tests/`. "
           "Se usan los parámetros por defecto de cada sprint, no los que se hayan editado en la sesión.")

with st.spinner("Ejecutando casos…"):
    res_ee = estado.entrenar_ee(20, 100, 60, 42)
    casos = (cp.casos_difuso() + cp.casos_integracion(res_ee["modelo"]) + cp.casos_sistema_experto()
             + cp.casos_busqueda() + cp.casos_juego() + cp.casos_evolutivo(res_ee, True))

df = pd.DataFrame(casos)
ok = int(df["ok"].sum())
k = st.columns(3)
k[0].metric("Casos ejecutados", len(df))
k[1].metric("Superados", ok)
k[2].metric("Con observaciones", int((df["nota"] != "").sum()))
if ok == len(df):
    st.success("Todos los casos se comportan como se espera.")
else:
    st.error("Hay casos que no se comportan como se espera. Revisa la tabla.")

grupo = st.selectbox("Grupo", ["Todos", *dict.fromkeys(df["grupo"])])
vista = df if grupo == "Todos" else df[df["grupo"] == grupo]
st.dataframe(vista.rename(columns={"grupo": "Grupo", "caso": "Caso", "esperado": "Esperado", "obtenido": "Obtenido",
                                   "ok": "OK", "nota": "Observación"}),
             hide_index=True, width="stretch", column_config={"OK": st.column_config.CheckboxColumn()})

st.subheader("Coherencia entre el sistema experto y el score calibrado")
st.caption("Se recorren las 2⁹ = 512 combinaciones posibles de las señales F1–F9 y se cruza la decisión del motor de reglas "
           "(Sprint 2) con la del score de la estrategia evolutiva (Sprint 3).")
tabla = cp.consistencia_ee_vs_se(res_ee["modelo"])
mat = pd.DataFrame(0, index=["Rechazo", "Revisión", "Continúa"], columns=["Alerta", "Sin alerta"])
for (se, ee), n in tabla.items():
    mat.loc[se, ee] = n
mat.index.name = "Sistema experto ↓ / Score EE →"
st.dataframe(mat, width="stretch")
st.markdown(f"- Cuando el sistema experto deja **continuar** la solicitud, el score nunca alerta "
            f"({mat.loc['Continúa', 'Alerta']} casos). Por eso, en el flujo integrado, el score no puede bloquear algo que las reglas aprueban.\n"
            f"- Hay **{mat.loc['Rechazo', 'Sin alerta']}** combinaciones que las reglas rechazan y el score no. Incluyen "
            "**una sola señal crítica aislada** (F4, F5 o F7): el mayor peso relativo aprendido (F7, 25.9 %) no alcanza el "
            "umbral (0.2924). Un score aditivo no puede expresar «esta señal sola basta», y una coincidencia en la lista AML/OFAC "
            "no puede quedar a criterio de un peso. También incluyen pares de alertas medias con poco peso (F2 y F3 terminaron "
            "en 0). Por eso el sistema experto sigue siendo la política que decide, y el score es una segunda opinión.")

st.subheader("Cómo correr las pruebas automáticas")
st.code("pip install -r requirements-dev.txt\npytest -q", language="bash")

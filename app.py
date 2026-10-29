"""Punto de entrada de la aplicación Streamlit: configuración y navegación."""
import streamlit as st

from ui import estado
from ui.componentes import aplicar_estilos

st.set_page_config(page_title="Nequi IA · Fundamentos de IA", page_icon="🛡️", layout="wide")
aplicar_estilos()
estado.init()

paginas = {
    "": [
        st.Page("vistas/inicio.py", title="Inicio", icon=":material/home:", default=True),
        st.Page("vistas/evaluar.py", title="Evaluar una solicitud", icon=":material/fact_check:"),
    ],
    "Componentes por sprint": [
        st.Page("vistas/logistica.py", title="1 · Logística (A*)", icon=":material/route:"),
        st.Page("vistas/sistema_experto.py", title="2 · Sistema experto", icon=":material/rule:"),
        st.Page("vistas/evolutivo.py", title="3 · Estrategia evolutiva", icon=":material/genetics:"),
        st.Page("vistas/juegos.py", title="3 · Teoría de juegos", icon=":material/swords:"),
        st.Page("vistas/difuso.py", title="4 · Lógica difusa", icon=":material/blur_on:"),
    ],
    "Calidad": [
        st.Page("vistas/validacion.py", title="Validación y pruebas", icon=":material/verified:"),
    ],
}

st.navigation(paginas).run()

st.sidebar.caption("Fundamentos de IA · Universidad EIA · 2026-2\n\n"
                   "Caso académico simulado. No usa datos ni sistemas reales de Nequi.")

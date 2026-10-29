import pandas as pd
import streamlit as st

st.title("Sistema inteligente de originación de crédito y antifraude")
st.markdown(
    "Proyecto semestral de **Fundamentos de IA** sobre un caso ficticio de Nequi. "
    "Cada sprint aplicó una técnica del curso al mismo caso; esta aplicación las reúne en un solo flujo, "
    "desde la entrega de la tarjeta hasta la decisión de crédito.")

st.page_link("vistas/evaluar.py", label="Evaluar una solicitud de crédito", icon=":material/arrow_forward:")

st.subheader("Cómo se decide una solicitud")
c1, c2, c3, c4 = st.columns(4)
pasos = [
    (c1, "Paso 1 · Sprint 2", "Motor de fraude", "Nueve reglas de identidad (F1–F9). Si hay una alerta crítica o dos medias, "
                                                 "se rechaza sin consultar el crédito. Con una sola alerta media, va a un analista."),
    (c2, "Paso 2 · Sprint 3", "Score calibrado", "Las mismas señales pasan por el score de fraude cuyos pesos y umbral "
                                                 "calibró la estrategia evolutiva (μ+λ). Es una segunda opinión."),
    (c3, "Paso 3 · Sprint 2", "Motor de crédito", "Nueve reglas financieras (C1–C9). Mora, antigüedad laboral, ingreso mínimo "
                                                  "y embargos siguen siendo filtros rígidos."),
    (c4, "Paso 4 · Sprint 4", "Capa difusa", "Score, carga de la cuota y endeudamiento se evalúan con lógica difusa (Mamdani). "
                                             "El resultado es un riesgo de 0 a 100 con una zona de revisión manual."),
]
for col, paso, titulo, texto in pasos:
    with col, st.container(border=True):
        st.markdown(f'<div class="paso">{paso}</div>', unsafe_allow_html=True)
        st.markdown(f"**{titulo}**")
        st.caption(texto)

st.subheader("Qué aporta cada sprint")
st.dataframe(pd.DataFrame([
    {"Sprint": "1", "Técnica": "Búsqueda informada (A*)",
     "Papel en el sistema": "Ruta y orden de entrega de la tarjeta física desde Bogotá a los hubs y a los clientes.",
     "Página": "1 · Logística (A*)"},
    {"Sprint": "2", "Técnica": "Sistema experto (encadenamiento hacia adelante)",
     "Papel en el sistema": "Política auditable de fraude y crédito: 18 reglas y cortocircuito de seguridad.",
     "Página": "2 · Sistema experto"},
    {"Sprint": "3", "Técnica": "Estrategia evolutiva (μ+λ)",
     "Papel en el sistema": "Calibra los pesos F2–F9 y el umbral del score de fraude (fitness = F1-score).",
     "Página": "3 · Estrategia evolutiva"},
    {"Sprint": "3", "Técnica": "Teoría de juegos + coevolución",
     "Papel en el sistema": "Pone a prueba el defensor contra un atacante que se adapta y busca el equilibrio.",
     "Página": "3 · Teoría de juegos"},
    {"Sprint": "4", "Técnica": "Lógica difusa (Mamdani)",
     "Papel en el sistema": "Sustituye las fronteras rígidas de C1, C2 y C4 por transiciones graduales.",
     "Página": "4 · Lógica difusa"},
]), hide_index=True, width="stretch")

with st.expander("Alcance y limitaciones"):
    st.markdown(
        "- Todos los datos son **simulados** y todos los parámetros son supuestos académicos de los notebooks del curso.\n"
        "- Los umbrales, pesos y reglas son exactamente los de los archivos de cada sprint. Donde faltó información, "
        "la decisión se declara en la página correspondiente y en `docs/ANALISIS.md`.\n"
        "- La numeración de los sprints (A* = 1, sistema experto = 2, evolutivos y teoría de juegos = 3, "
        "lógica difusa = 4) es una reconstrucción a partir del material entregado.")

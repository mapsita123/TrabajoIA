"""
Estado compartido entre páginas y cálculos en caché.

Los umbrales del sistema experto y los parámetros difusos viven en
st.session_state: si el usuario los edita en su página, la evaluación
integrada los usa y lo avisa. Por defecto son siempre los de los archivos.
"""
from __future__ import annotations

import streamlit as st

from core import difuso, evolutivo, teoria_juegos, teoria_juegos_v4
from core.sistema_experto import DEFAULT_PARAMS


def init():
    st.session_state.setdefault("params_se", dict(DEFAULT_PARAMS))
    st.session_state.setdefault("anchos_difusos", dict(difuso.ANCHOS_BASE))
    st.session_state.setdefault("ee_params", {"mu": evolutivo.MU, "lambda_": evolutivo.LAMBDA,
                                              "generaciones": evolutivo.GENERACIONES,
                                              "semilla": evolutivo.SEMILLA})


def params_se() -> dict:
    init()
    return st.session_state["params_se"]


def config_difusa() -> dict:
    """Conjuntos difusos construidos con los umbrales VIGENTES del sistema experto."""
    init()
    return difuso.construir_config(params_se(), st.session_state["anchos_difusos"])


def se_personalizado() -> bool:
    return params_se() != DEFAULT_PARAMS


def difuso_personalizado() -> bool:
    init()
    return st.session_state["anchos_difusos"] != difuso.ANCHOS_BASE


def ee_personalizada() -> bool:
    p = st.session_state.get("ee_params", {})
    return p != {"mu": evolutivo.MU, "lambda_": evolutivo.LAMBDA,
                 "generaciones": evolutivo.GENERACIONES, "semilla": evolutivo.SEMILLA}


@st.cache_resource(show_spinner="Calibrando el score de fraude con la estrategia evolutiva…")
def entrenar_ee(mu: int, lambda_: int, generaciones: int, semilla: int):
    return evolutivo.entrenar(mu, lambda_, generaciones, semilla)


def resultado_ee():
    init()
    return entrenar_ee(**st.session_state["ee_params"])


def modelo_ee():
    return resultado_ee()["modelo"]


@st.cache_data(show_spinner=False)
def correr_juego_v2(rondas, mu, lam, semilla, supuestos: dict, con_desviacion: bool):
    return teoria_juegos.corrida_completa(rondas, mu, lam, semilla,
                                          teoria_juegos.Supuestos(**supuestos), con_desviacion)


@st.cache_data(show_spinner=False)
def correr_juego_v4(semilla):
    return teoria_juegos_v4.corrida_completa(semilla)


@st.cache_data(show_spinner=False)
def barrido_v4():
    return teoria_juegos_v4.barrido_umbral()


def avisos_parametros():
    """Muestra qué partes del sistema están usando parámetros distintos a los de los archivos."""
    avisos = []
    if se_personalizado():
        avisos.append("umbrales del sistema experto")
    if difuso_personalizado():
        avisos.append("anchos de transición difusos")
    if ee_personalizada():
        avisos.append("parámetros de la estrategia evolutiva")
    if avisos:
        st.info("Esta evaluación usa valores modificados en: " + ", ".join(avisos)
                + ". Puedes restablecerlos en la página correspondiente.", icon="⚙️")

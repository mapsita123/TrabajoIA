"""Piezas de interfaz compartidas: estilos, etiquetas de decisión y gráficos."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

COLOR_PRIMARIO = "#D91074"   # magenta usado en las gráficas del notebook de la EE
COLOR_SECUNDARIO = "#167D9A"  # azul usado en las mismas gráficas
COLORES_ETIQUETA = {"bajo": "#16A34A", "medio": "#F59E0B", "alto": "#DC2626",
                    "holgada": "#16A34A", "moderada": "#F59E0B", "excedida": "#DC2626",
                    "aceptable": "#16A34A", "excesivo": "#DC2626"}

DECISIONES = {
    "APROBADO": ("Aprobado", "ok"),
    "REVISION_MANUAL": ("Revisión manual", "warn"),
    "RECHAZADO_POR_FRAUDE": ("Rechazado por fraude", "bad"),
    "RECHAZADO_POR_RIESGO_FINANCIERO": ("Rechazado por riesgo financiero", "bad"),
    "ALERTA_DE_RIESGO": ("Alerta de riesgo", "bad"),
    "SIN_ALERTA_DEL_MODELO": ("Sin alerta", "ok"),
    "REQUIERE_VERIFICACION_BIOMETRICA": ("Requiere verificación biométrica", "bad"),
}

CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1180px;}
.dec {border-radius: 10px; padding: 14px 18px; margin: 4px 0 12px 0; border: 1px solid transparent;}
.dec .lbl {font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; opacity: .75;}
.dec .val {font-size: 1.45rem; font-weight: 650; margin-top: 2px;}
.dec .why {font-size: .92rem; margin-top: 4px; opacity: .9;}
.dec.ok   {background: rgba(22,163,74,.10);  border-color: rgba(22,163,74,.35);}
.dec.warn {background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.45);}
.dec.bad  {background: rgba(220,38,38,.10);  border-color: rgba(220,38,38,.35);}
.chip {display:inline-block; padding: 1px 8px; border-radius: 999px; font-size: .78rem;
       font-weight: 600; margin-right: 4px; border: 1px solid rgba(128,128,128,.35);}
.chip.CRITICO, .chip.RECHAZO {color:#DC2626; border-color: rgba(220,38,38,.45);}
.chip.MEDIO {color:#B45309; border-color: rgba(245,158,11,.55);}
.chip.FAVORABLE {color:#16A34A; border-color: rgba(22,163,74,.45);}
.paso {font-size:.8rem; color: #888; text-transform: uppercase; letter-spacing:.05em;}
</style>
"""


def aplicar_estilos():
    st.markdown(CSS, unsafe_allow_html=True)


def tarjeta_decision(codigo: str, motivo: str = "", titulo: str = "Decisión"):
    texto, clase = DECISIONES.get(codigo, (codigo.replace("_", " ").capitalize(), "warn"))
    st.markdown(
        f'<div class="dec {clase}"><div class="lbl">{titulo}</div>'
        f'<div class="val">{texto}</div><div class="why">{motivo}</div></div>',
        unsafe_allow_html=True)


def texto_decision(codigo: str) -> str:
    return DECISIONES.get(codigo, (codigo, ""))[0]


def chip(nivel: str) -> str:
    return f'<span class="chip {nivel}">{nivel.capitalize()}</span>'


def lista_reglas(deducciones: list[dict], vacio: str):
    if not deducciones:
        st.caption(vacio)
        return
    filas = "".join(f"<div style='margin:3px 0'><b>{d['id']}</b> {chip(d['nivel'])} "
                    f"<code>{d['consecuencia']}</code></div>" for d in deducciones)
    st.markdown(filas, unsafe_allow_html=True)


def pesos(v: float) -> str:
    return f"$ {v:,.0f}".replace(",", ".")


def _layout(fig, alto=280, titulo=None):
    fig.update_layout(height=alto, margin=dict(l=10, r=10, t=40 if titulo else 10, b=10),
                      title=titulo, legend=dict(orientation="h", y=-0.25),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,.18)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,.18)")
    return fig


def grafico_pertenencia(u, curvas: dict, titulo: str, marcador: float | None = None,
                        eje_x: str = "", umbrales: list[tuple[float, str]] | None = None):
    fig = go.Figure()
    for etq, curva in curvas.items():
        fig.add_trace(go.Scatter(x=u, y=curva, name=etq.capitalize(), mode="lines",
                                 line=dict(width=2.5, color=COLORES_ETIQUETA.get(etq))))
    for x, txt in umbrales or []:
        fig.add_vline(x=x, line_dash="dot", line_color="gray", annotation_text=txt,
                      annotation_position="top", annotation_font_size=10)
    if marcador is not None:
        fig.add_vline(x=marcador, line_color=COLOR_PRIMARIO, line_width=2,
                      annotation_text=f"valor = {marcador:g}", annotation_position="bottom right")
    fig.update_yaxes(range=[-0.03, 1.08], title="μ")
    fig.update_xaxes(title=eje_x)
    return _layout(fig, titulo=titulo)


def grafico_salida(res, config_salida):
    u = res["universo_salida"]
    fig = go.Figure()
    from core.difuso import curvas
    _, cs = curvas(config_salida)
    for etq, curva in cs.items():
        fig.add_trace(go.Scatter(x=u, y=curva, name=f"Riesgo {etq}", mode="lines",
                                 line=dict(width=1.5, dash="dot", color=COLORES_ETIQUETA[etq])))
    fig.add_trace(go.Scatter(x=u, y=res["agregada"], name="Salida agregada", fill="tozeroy",
                             line=dict(color=COLOR_SECUNDARIO, width=2), fillcolor="rgba(22,125,154,.35)"))
    fig.add_vline(x=res["riesgo"], line_color=COLOR_PRIMARIO, line_width=2.5,
                  annotation_text=f"centroide = {res['riesgo']:.1f}", annotation_position="top")
    fig.update_yaxes(range=[-0.03, 1.08], title="μ")
    fig.update_xaxes(title="Riesgo crediticio (0–100)")
    return _layout(fig, alto=300, titulo="Agregación (máximo) y defuzzificación (centroide)")


def grafico_lineas(x, series: dict, titulo: str, eje_x: str, eje_y: str, alto=300):
    fig = go.Figure()
    paleta = [COLOR_PRIMARIO, COLOR_SECUNDARIO, "#F59E0B", "#16A34A", "#6B7280"]
    for k, (nombre, y) in enumerate(series.items()):
        fig.add_trace(go.Scatter(x=x, y=y, name=nombre, mode="lines",
                                 line=dict(width=2.2, color=paleta[k % len(paleta)])))
    fig.update_xaxes(title=eje_x)
    fig.update_yaxes(title=eje_y)
    return _layout(fig, alto=alto, titulo=titulo)


def grafico_barras_h(etiquetas, valores, titulo, formato="{:.1%}", color=COLOR_SECUNDARIO, alto=None):
    orden = np.argsort(valores)
    fig = go.Figure(go.Bar(x=np.asarray(valores)[orden], y=np.asarray(etiquetas)[orden], orientation="h",
                           marker_color=color, text=[formato.format(v) for v in np.asarray(valores)[orden]],
                           textposition="outside", cliponaxis=False))
    return _layout(fig, alto=alto or 40 + 30 * len(etiquetas), titulo=titulo)


def matriz_confusion(m: dict, titulo: str):
    z = [[m["vn"], m["fp"]], [m["fn"], m["vp"]]]
    txt = [[f"VN<br>{m['vn']}", f"FP<br>{m['fp']}"], [f"FN<br>{m['fn']}", f"VP<br>{m['vp']}"]]
    fig = go.Figure(go.Heatmap(z=z, x=["Sin alerta", "Alerta"], y=["Legítima", "Fraude"], text=txt,
                               texttemplate="%{text}", colorscale="Blues", showscale=False))
    fig.update_yaxes(autorange="reversed", title="Real")
    fig.update_xaxes(title="Predicción")
    return _layout(fig, alto=260, titulo=titulo)

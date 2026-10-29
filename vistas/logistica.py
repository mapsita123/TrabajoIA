import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import busqueda as bq
from ui.componentes import COLOR_PRIMARIO

st.title("Sprint 1 · Logística de tarjetas con A*")
st.caption("La tarjeta física sale de Bogotá hacia un hub regional y de ahí al barrio y al cliente. "
           "A* encuentra la ruta local más corta y luego se decide en qué orden entregar.")

with st.expander("Fuente de los datos y vacíos declarados"):
    st.markdown(
        "- Red, costos, coordenadas, heurística por capas (h = 0.45 en el hub, 0.15 en barrios, 0 en clientes) y "
        "pesos Premium 3.0 / Regular 1.0: `mapas-reales-ciudades (1).html`.\n"
        "- **El script Python original de A* no está en la carpeta.** El costo barrio→cliente se deriva como "
        "g(cliente) − g(barrio) a partir del mismo archivo. El tronco Bogotá→hub se usa como un único tramo con su total.\n"
        "- El orden de entrega se modela como el problema 1‖Σ wᵢCᵢ con pᵢ = tiempo A* desde el hub. Con ese modelo la "
        "regla de Smith es óptima, como afirma el proyecto. Los tiempos son supuestos didácticos, no tiempos medidos.")

ciudad = st.segmented_control("Ciudad", list(bq.CIUDADES), default="Medellín")
if not ciudad:
    st.stop()
c = bq.CIUDADES[ciudad]
grafo = bq.construir_grafo(ciudad)
clientes = list(c["clientes"])

col_mapa, col_busq = st.columns([1.25, 1], gap="large")
with col_busq:
    st.markdown(f"**Tronco:** {c['tronco'][0]} · {c['tronco'][1]} h")
    destino = st.selectbox("Cliente destino", clientes,
                           format_func=lambda k: f"{k} · {c['clientes'][k][1]}")
    res = bq.a_estrella(ciudad, destino)
    st.markdown(f"**Ruta óptima local:** {' → '.join(res.camino)}")
    st.markdown(f"**Costo local:** {res.costo:.2f} h · **Total desde Bogotá:** {c['tronco'][1] + res.costo:.2f} h · "
                f"**Nodos expandidos:** {len(res.expandidos)}")
    st.markdown("##### Traza de A* (f = g + h)")
    st.dataframe(pd.DataFrame(res.traza), hide_index=True, width="stretch")

with col_mapa:
    pos = {"HUB": c["hub"], **c["barrios"], **{k: v[3] for k, v in c["clientes"].items()}}
    en_ruta = set(zip(res.camino, res.camino[1:])) | set(zip(res.camino[1:], res.camino))
    fig = go.Figure()
    vistos = set()
    for u, vecinos in grafo.items():
        for v, costo in vecinos.items():
            if (v, u) in vistos:
                continue
            vistos.add((u, v))
            usa = (u, v) in en_ruta
            fig.add_trace(go.Scattermap(
                lat=[pos[u][0], pos[v][0]], lon=[pos[u][1], pos[v][1]], mode="lines",
                line=dict(width=5 if usa else 2, color=COLOR_PRIMARIO if usa else "#8A8A82"),
                hoverinfo="text", text=f"{u} → {v}: {costo:.2f} h", showlegend=False))
    tipos = {"HUB": ("Hub", "#17191E", 16)}
    tipos.update({b: ("Barrio", "#167D9A", 12) for b in c["barrios"]})
    tipos.update({k: (v[1], "#B8471F" if v[1] == "Premium" else "#8A8A82", 9) for k, v in c["clientes"].items()})
    for grupo in ("Hub", "Barrio", "Premium", "Regular"):
        nodos = [n for n, t in tipos.items() if t[0] == grupo]
        fig.add_trace(go.Scattermap(
            lat=[pos[n][0] for n in nodos], lon=[pos[n][1] for n in nodos], mode="markers+text",
            marker=dict(size=tipos[nodos[0]][2], color=tipos[nodos[0]][1]), text=nodos,
            textposition="top right", name=grupo, hovertext=[f"{n} · h = {bq.heuristica(n, ciudad)}" for n in nodos]))
    lat = [p[0] for p in pos.values()]
    lon = [p[1] for p in pos.values()]
    fig.update_layout(map=dict(style="open-street-map", center=dict(lat=sum(lat) / len(lat), lon=sum(lon) / len(lon)),
                               zoom=11 if ciudad != "Cartagena" else 10.3),
                      height=470, margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=-0.05))
    st.plotly_chart(fig, width="stretch")

st.subheader("Heurística por capas: comprobación de admisibilidad")
st.caption("h(n) es admisible si nunca supera el costo real mínimo h*(n) hasta un cliente.")
adm = pd.DataFrame(bq.verificar_admisibilidad(ciudad))
st.dataframe(adm, hide_index=True, width="stretch")
if adm["admisible"].all():
    st.success("La heurística es admisible en todos los nodos de esta red.")
else:
    st.error("Hay nodos donde la heurística sobreestima el costo real.")

st.subheader("Orden de entrega: comparación de políticas")
js = bq.trabajos(ciudad)
st.dataframe(pd.DataFrame(js).rename(columns={"cliente": "Cliente", "tipo": "Tipo", "w": "Peso w",
                                              "p": "Tiempo p (h)"}).assign(**{"w / p": lambda d: d["Peso w"] / d["Tiempo p (h)"]}),
             hide_index=True, width="stretch")
pol = pd.DataFrame(bq.comparar_politicas(ciudad))
opt_astar = bq.a_estrella_secuencia(js)
opt_fb = bq.fuerza_bruta(js)
pol = pd.concat([pol, pd.DataFrame([
    {"politica": "A* sobre permutaciones", "secuencia": " → ".join(opt_astar["secuencia"]), "costo": opt_astar["costo"]},
    {"politica": f"Fuerza bruta ({opt_fb['permutaciones']} permutaciones)", "secuencia": " → ".join(opt_fb["secuencia"]),
     "costo": opt_fb["costo"]}])])
st.dataframe(pol.rename(columns={"politica": "Política", "secuencia": "Secuencia", "costo": "Σ wᵢCᵢ"}),
             hide_index=True, width="stretch")
wspt = pol.iloc[2]["costo"]
if abs(wspt - opt_fb["costo"]) < 1e-9:
    st.success(f"La política ponderada (WSPT, ordenar por w/p de mayor a menor) alcanza el óptimo global "
               f"Σ wᵢCᵢ = {wspt:.2f}, igual que A* ({opt_astar['expandidos']} estados expandidos) y que la fuerza bruta.")

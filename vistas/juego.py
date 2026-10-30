import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import juego_brecha as jb
from ui.componentes import COLOR_PRIMARIO, COLOR_SECUNDARIO, _layout

st.title("Brecha Nequi · el juego del proyecto")
st.caption("Juego de la última entrega. Un ninja intenta robar y el Guardián de Nequi lo detiene. Cada misión convierte en "
           "jugada un concepto del proyecto: el costo de cada señal, el umbral de decisión, la estrategia evolutiva y el "
           "equilibrio de Nash.")

# ============================================================ A. INTRODUCCIÓN ===
ESCENA = """
<svg viewBox="0 0 760 230" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Escena del juego: el ninja recoge señales y cruza el arco de revisión del Guardián" style="width:100%;height:auto;max-height:260px">
  <defs><linearGradient id="cielo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c1430"/><stop offset="1" stop-color="#0a0c14"/></linearGradient></defs>
  <rect width="760" height="230" rx="14" fill="url(#cielo)"/>
  <g fill="#12111c" opacity=".9"><rect x="40" y="70" width="60" height="110"/><rect x="120" y="100" width="45" height="80"/><rect x="520" y="60" width="70" height="120"/><rect x="610" y="95" width="50" height="85"/></g>
  <rect y="180" width="760" height="50" fill="#1a1730"/><rect y="180" width="760" height="2" fill="#2a2640"/>
  <text x="70" y="178" font-size="54">🥷</text>
  <g font-size="26"><text x="175" y="150">📱</text><text x="235" y="110">⚡</text><text x="295" y="150">🌐</text><text x="355" y="110">🔑</text></g>
  <g font-family="sans-serif" font-size="11" fill="#ffcc4d" text-anchor="middle"><text x="190" y="172">+0.6</text><text x="250" y="132">+0.6</text><text x="310" y="172">+0.6</text><text x="370" y="132">+0.6</text></g>
  <text x="430" y="66" font-size="26">👁</text><rect x="434" y="72" width="14" height="108" fill="#ff5a6e" opacity=".25"/>
  <text x="441" y="44" font-family="sans-serif" font-size="11" fill="#aaa3c8" text-anchor="middle">F10 · no la controlas</text>
  <g fill="#35e2a0"><rect x="505" y="30" width="6" height="150"/><rect x="551" y="30" width="6" height="150"/><rect x="505" y="24" width="52" height="8"/></g>
  <text x="531" y="16" font-family="sans-serif" font-size="11" fill="#35e2a0" text-anchor="middle">revisión: puntaje vs umbral</text>
  <text x="640" y="178" font-size="60" transform="translate(1280,0) scale(-1,1)">🛡️</text>
  <text x="670" y="112" font-family="sans-serif" font-size="11" fill="#aaa3c8" text-anchor="middle">Guardián Nequi</text>
</svg>
"""

intro_izq, intro_der = st.columns([1.15, 1], gap="large")
with intro_izq:
    st.markdown(ESCENA, unsafe_allow_html=True)
with intro_der:
    st.markdown("##### Objetivo")
    st.markdown("Ver, jugando, por qué un sistema antifraude no puede bloquearlo todo, por qué el atacante tampoco puede "
                "activar todas las señales, y por qué el equilibrio entre ambos es **mixto**.")
    st.markdown("##### Reglas fundamentales")
    st.markdown(
        "- Cada señal F2–F9 que recoge el ninja **suma +0.6 al botín**, pero también **sube su puntaje de riesgo**.\n"
        "- El Guardián **bloquea si el puntaje supera su umbral**. La biometría falsa (🎭) bloquea siempre.\n"
        "- **F10** (👁) aparece en el 40 % de los fraudes y el ninja no la controla.\n"
        "- Nequi paga por el fraude que deja pasar (× 2 %) **y** por cada cliente legítimo que bloquea (× 98 % × 0.15).")

st.markdown("##### Las cuatro misiones")
cols = st.columns(4)
for col, (icono, titulo, juegas, concepto) in zip(cols, [
    ("🥷", "1 · El precio de cada poder", "Juegas de ninja", "Trade-off botín/riesgo y pagos de cada bando"),
    ("🛡️", "2 · El umbral de Nequi", "Juegas de Guardián", "Costo por falsos positivos, suma no cero y mejor respuesta"),
    ("🧬", "3 · El Guardián aprende", "Juegas de ninja", "Estrategia evolutiva (μ+λ), coevolución y convergencia"),
    ("🎲", "4 · Duelo simultáneo", "Eliges personaje", "Ciclo sin Nash puro, equilibrio mixto e indiferencia"),
]):
    with col, st.container(border=True):
        st.markdown(f"### {icono}")
        st.markdown(f"**{titulo}**")
        st.caption(f"{juegas} · {concepto}")

with st.expander("Cómo empezar a jugar", expanded=False):
    st.markdown(
        "1. Haz **clic sobre el escenario** del juego para que reciba el teclado.\n"
        "2. **Teclado:** ← → avanzar · ↑ saltar · Espacio atacar · Enter siguiente · R reiniciar · 1–4 cambiar de misión · "
        "N abrir el cuaderno. En la misión 2, ↑ ↓ mueven el umbral. En la 4, A/S o E/L eligen la jugada y D lanza un dado con tu mezcla.\n"
        "3. **Celular o tableta:** usa los botones táctiles que aparecen debajo del escenario.\n"
        "4. Cada concepto que vives se desbloquea en el **cuaderno** (12 en total).")

# ================================================================ B. JUEGO ===
st.divider()
st.subheader("Jugar")
st.session_state.setdefault("partida_brecha", 0)
c1, c2, c3 = st.columns([1.4, 1, 2])
mision = c1.selectbox("Empezar en", list(jb.MISIONES), format_func=jb.MISIONES.get, key="mision_brecha")
c2.markdown("<div style='height:1.75rem'></div>", unsafe_allow_html=True)
if c2.button("Reiniciar juego", icon=":material/restart_alt:", help="Empieza una partida nueva desde la misión elegida."):
    st.session_state["partida_brecha"] += 1
c3.caption("El juego es el de la entrega, sin cambios en sus mecánicas. Su progreso (botín, oleadas, cuaderno) vive en la "
           "partida: al reiniciar o cambiar la misión inicial empieza de cero. Dentro del juego, R reinicia solo la misión actual.")
st.iframe(jb.html_juego(mision, st.session_state["partida_brecha"]), height="content")

# ========================================================== C. EXPLICACIÓN ===
st.divider()
st.subheader("Qué pasa por dentro y por qué")
st.caption("Todos los números de esta sección se calculan con la misma lógica del juego (enumeración exacta de las 256 "
           "combinaciones de señales), portada a Python en `core/juego_brecha.py`.")

t_flujo, t_m1, t_m2, t_m3, t_m4 = st.tabs(["Flujo de una jugada", "Misión 1", "Misión 2", "Misión 3", "Misión 4"])

with t_flujo:
    st.graphviz_chart("""
digraph G {
  rankdir=TB; nodesep=0.5; bgcolor="transparent"; node [shape=box, style="rounded,filled", fontname="sans-serif", fontsize=12, color="#999999"];
  edge [fontname="sans-serif", fontsize=10, color="#888888"];
  {rank=same; a; f10;}
  a [label="Ninja elige señales\\nF2–F9 (+0.6 c/u)", fillcolor="#fde2ef"];
  f10 [label="F10 aparece\\n(40 %, no controlable)", fillcolor="#fde2ef"];
  bio [label="¿Biometría falsa\\n(F1)?", shape=diamond, fillcolor="#eef2f7"];
  s [label="Puntaje = Σ pesos activos\\n÷ Σ todos los pesos", fillcolor="#eef2f7"];
  u [label="¿Puntaje > umbral\\ndel Guardián?", shape=diamond, fillcolor="#eef2f7"];
  b [label="Bloqueado\\nbotín 0", fillcolor="#dcfce7"];
  p [label="Pasa\\nbotín 1 + 0.6·k", fillcolor="#fee2e2"];
  c [label="Costo de Nequi =\\n0.02·botín + 0.98·0.15·FPR", fillcolor="#fef3c7"];
  a -> bio; f10 -> s; bio -> b [label="sí"]; bio -> s [label="no"]; s -> u; u -> b [label="sí"]; u -> p [label="no"];
  p -> c; b -> c [label="clientes legítimos\\nbloqueados también cuestan"];
}""", width="stretch")
    st.markdown("Es el mismo esquema del flujo integrado: **F1 es un control obligatorio** y las demás señales forman un "
                "**score ponderado contra un umbral**, como el que calibra la estrategia evolutiva del Sprint 3. El pago "
                "de Nequi incluye los falsos positivos, así que **no es un juego de suma cero**.")

with t_m1:
    filas = jb.combinaciones_ninja()
    mejor = jb.mejor_combinacion(filas)
    df = pd.DataFrame(filas)
    st.markdown(f"**Pregunta del ninja:** ¿qué señales conviene recoger contra el Guardián (umbral {jb.NB['umbral']})? "
                f"Recorriendo las 256 combinaciones, la **mejor respuesta** es **{mejor['señales']}**, con un botín esperado de "
                f"**{mejor['botin_esperado']:.2f}** por intento (golpe de {mejor['valor_golpe']:.1f}). Pasa sin F10, pero si F10 "
                "aparece lo bloquean.")
    por_k = df.groupby("n_señales")["botin_esperado"].max()
    fig = go.Figure(go.Bar(x=por_k.index, y=por_k.values, marker_color=[COLOR_PRIMARIO if k == mejor["n_señales"] else COLOR_SECUNDARIO for k in por_k.index],
                           text=[f"{v:.2f}" for v in por_k.values], textposition="outside"))
    fig.update_xaxes(title="Número de señales F2–F9 encendidas", dtick=1)
    fig.update_yaxes(title="Mejor botín esperado por intento")
    st.plotly_chart(_layout(fig, 300, "Más señales no siempre es mejor"), width="stretch")
    st.caption("Con 0 señales el ninja solo se lleva el valor base. Con muchas, cada golpe vale más, pero el puntaje supera "
               "el umbral y lo bloquean siempre (barras en 0). El óptimo está en el medio: es el **trade-off** que la versión con pagos económicos introdujo frente "
               "al «ataque invisible» de las primeras versiones.")
    st.markdown("##### Prueba tu propia combinación")
    elegidas = st.multiselect("Señales que recoge el ninja", [f"{s} · {jb.PODERES[i]}" for i, s in enumerate(jb.SEÑALES) if i > 0],
                              default=[f"{s} · {jb.PODERES[i]}" for i, s in enumerate(jb.SEÑALES) if s in mejor["señales"].split(" + ")])
    idx = sorted(jb.SEÑALES.index(e.split(" · ")[0]) - 1 for e in elegidas)
    fila = df[df["señales"] == (" + ".join(jb.SEÑALES[i + 1] for i in idx) or "ninguna")].iloc[0]
    k = st.columns(4)
    k[0].metric("Valor del golpe", f"{fila['valor_golpe']:.1f}")
    k[1].metric("Puntaje sin F10", f"{fila['puntaje_sin_F10']:.3f}", f"umbral {jb.NB['umbral']}", delta_color="off")
    k[2].metric("¿Pasa?", ("sí" if fila["pasa_sin_F10"] else "no") + " sin F10 · " + ("sí" if fila["pasa_con_F10"] else "no") + " con F10")
    k[3].metric("Botín esperado", f"{fila['botin_esperado']:.2f}", f"{fila['botin_esperado'] - mejor['botin_esperado']:+.2f} vs. óptimo")

with t_m2:
    st.markdown("**Pregunta de Nequi:** ¿qué umbral cuesta menos? Depende del ninja. La curva es el costo exacto por transacción "
                "para cada umbral (fraude que pasa + clientes legítimos bloqueados).")
    fig = go.Figure()
    resumen = []
    for (nombre, pc), color in zip(jb.ESTILOS.items(), ["#16A34A", "#F59E0B", "#DC2626"]):
        us, cs, best = jb.curva_costo(pc)
        fig.add_trace(go.Scatter(x=us, y=cs, name=f"Ninja {nombre.lower()} ({pc:.0%})", line=dict(color=color, width=2.3, shape="hv")))
        fig.add_trace(go.Scatter(x=[best["umbral"]], y=[best["costo"]], mode="markers", marker=dict(size=10, color=color, symbol="star"),
                                 showlegend=False, hovertext=f"óptimo {best['umbral']:.3f}"))
        e, l = jb.costo_exacto(jb.UMBRAL_ESTRICTO, pc), jb.costo_exacto(jb.UMBRAL_LAXO, pc)
        resumen.append({"Ninja": nombre, "Umbral óptimo": best["umbral"], "Costo óptimo": best["costo"],
                        "Costo ESTRICTO (0.15)": e["costo"], "Costo LAXO (0.40)": l["costo"],
                        "Conviene": "ESTRICTO" if e["costo"] <= l["costo"] else "LAXO"})
    fig.add_vline(x=jb.UMBRAL_ESTRICTO, line_dash="dash", line_color="gray", annotation_text="ESTRICTO")
    fig.add_vline(x=jb.UMBRAL_LAXO, line_dash="dash", line_color="gray", annotation_text="LAXO")
    fig.update_xaxes(title="Umbral del Guardián")
    fig.update_yaxes(title="Costo esperado por transacción")
    st.plotly_chart(_layout(fig, 340), width="stretch")
    st.dataframe(pd.DataFrame(resumen), hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="%.4f") for c in
                                ("Costo óptimo", "Costo ESTRICTO (0.15)", "Costo LAXO (0.40)")})
    st.caption("Las curvas tienen escalones porque los pesos son discretos: cada señal extra cruza el umbral de golpe. Contra el "
               "sigiloso conviene ser laxo (bloquear más solo genera falsos positivos); contra el agresivo, estricto. Esa dependencia "
               "es la **mejor respuesta**, y como ninguna jugada sirve contra todo, el equilibrio no está en un extremo.")

with t_m3:
    st.markdown("**El Guardián evoluciona entre oleadas** con la misma estrategia evolutiva del proyecto: μ = 6 padres, λ = 16 "
                "hijos, cruce intermedio, mutación gaussiana con σ autoadaptativo y selección (μ+λ). Su fitness es el costo "
                "contra tus últimos 4 ataques. Desde la oleada 3 aparece F10.")
    st.graphviz_chart("""
digraph G {
  rankdir=LR; bgcolor="transparent"; node [shape=box, style="rounded,filled", fontname="sans-serif", fontsize=11, color="#999999", fillcolor="#eef2f7"];
  edge [fontname="sans-serif", fontsize=10, color="#888888"];
  o [label="Oleada: tus 60 fraudes\\ncon las señales que elegiste", fillcolor="#fde2ef"];
  e [label="1 · Evaluar\\n6 Guardianes vs. tus\\núltimos 4 ataques"];
  x [label="2 · Cruce intermedio\\nhijo entre dos padres"];
  m [label="3 · Mutación\\nσ' = σ·e^(τN), genes + N(0,σ')"];
  h [label="4 · 16 hijos evaluados"];
  s [label="5 · Selección (μ+λ)\\nsobreviven los 6 de menor costo"];
  g [label="Nuevo Guardián\\n(más pesos donde atacas)", fillcolor="#dcfce7"];
  o -> e -> x -> m -> h -> s -> g; g -> o [label="siguiente oleada", style=dashed];
}""", width="stretch")
    st.markdown("- **Si repites la ruta**, el Guardián sube el peso de esas señales y tu botín cae: eso es la **convergencia**.\n"
                "- **Si cambias**, tiene que volver a aprender: la **coevolución** no tiene un ganador fijo.\n"
                "- En el juego solo evoluciona el Guardián (tú eres el atacante). En la página "
                "**3 · Teoría de juegos** evolucionan ambas poblaciones a la vez.")

with t_m4:
    eq = jb.equilibrio_inspeccion()
    filas_n, cols_n = ["ESTRICTO", "LAXO"], ["AGRESIVO", "SIGILOSO"]
    tabla = pd.DataFrame([[f"Nequi {jb.A2[i, j]:.2f} · ninja {jb.B2[i, j]:.3f}"
                           + (" ◀ MR Nequi" if eq["mejor_def"][j] == i else "") + (" ▲ MR ninja" if eq["mejor_atk"][i] == j else "")
                           for j in range(2)] for i in range(2)], index=filas_n, columns=cols_n)
    st.markdown("**Matriz de pagos del duelo** (Nequi ×1000, ninja por intento). MR = mejor respuesta.")
    st.dataframe(tabla, width="stretch")
    st.graphviz_chart("""
digraph G {
  rankdir=LR; bgcolor="transparent"; node [shape=box, style="rounded,filled", fontname="sans-serif", fontsize=11, color="#999999"];
  edge [fontname="sans-serif", fontsize=10, color="#888888"];
  e [label="Nequi ESTRICTO", fillcolor="#dbeafe"]; s [label="Ninja SIGILOSO", fillcolor="#fde2ef"];
  l [label="Nequi LAXO", fillcolor="#dbeafe"]; a [label="Ninja AGRESIVO", fillcolor="#fde2ef"];
  e -> s [label="al ninja le conviene"]; s -> l [label="a Nequi le conviene"]; l -> a [label="al ninja le conviene"]; a -> e [label="a Nequi le conviene"];
}""", width="stretch")
    st.markdown("El ciclo nunca se cierra en una celda: **no hay equilibrio en estrategias puras**. Cada bando debe mezclar "
                "en la proporción que deja **indiferente** al otro.")
    p = np.linspace(0, 1, 101)
    ag = p * jb.B2[0, 0] + (1 - p) * jb.B2[1, 0]
    si = p * jb.B2[0, 1] + (1 - p) * jb.B2[1, 1]
    fig = go.Figure([go.Scatter(x=p, y=ag, name="Ninja AGRESIVO", line=dict(color="#DC2626", width=2.3)),
                     go.Scatter(x=p, y=si, name="Ninja SIGILOSO", line=dict(color=COLOR_SECUNDARIO, width=2.3))])
    fig.add_vline(x=eq["p_estricto"], line_dash="dash", line_color=COLOR_PRIMARIO,
                  annotation_text=f"p* = {eq['p_estricto']:.3f}")
    fig.update_xaxes(title="Probabilidad de que Nequi sea ESTRICTO (p)")
    fig.update_yaxes(title="Pago esperado del ninja")
    st.plotly_chart(_layout(fig, 300, "Condición de indiferencia del ninja"), width="stretch")
    k = st.columns(4)
    k[0].metric("P(Nequi ESTRICTO) = p*", f"{eq['p_estricto']:.3f}")
    k[1].metric("P(ninja AGRESIVO) = q*", f"{eq['q_agresivo']:.3f}")
    k[2].metric("Pago del ninja en equilibrio", f"{eq['pago_ninja']:.3f}")
    k[3].metric("Pago de Nequi en equilibrio (×1000)", f"{eq['pago_nequi_x1000']:.2f}")
    st.caption("Si Nequi es estricto más del p* de las veces, al ninja le conviene ser siempre sigiloso; si lo es menos, siempre "
               "agresivo. Solo en p* le da igual, y por eso no puede explotar a Nequi. En el duelo, el rival lee tus últimas 8 "
               "jugadas: si dejas un patrón, te explota.")
    st.info("Esta matriz es la del notebook v3 que usa el juego (p* ≈ 0.533, q* ≈ 0.213). La página **3 · Teoría de juegos** "
            "calcula en vivo la versión v2 (p* ≈ 0.559, q* ≈ 0.214). Las dos coinciden en la dirección: Nequi mezcla cerca "
            "de mitad y mitad, y el ninja ataca de forma agresiva solo cerca de 1 de cada 5 veces.", icon="ℹ️")

import pandas as pd
import streamlit as st

from core import integracion
from core.sistema_experto import PRESETS, condiciones_legibles
from ui import estado
from ui.componentes import grafico_salida, lista_reglas, pesos, tarjeta_decision, texto_decision

st.title("Evaluar una solicitud de crédito")
st.caption("Ingresa los datos de la solicitud o carga un caso de ejemplo. Al evaluar, la solicitud pasa en orden por "
           "el motor de fraude, el score calibrado, el motor de crédito y la capa difusa.")

NUMERICOS = {
    # campo: (etiqueta, mínimo, máximo, paso, ayuda)
    "minutos_registro_a_solicitud": ("Minutos entre registro y solicitud", 0.0, 100000.0, 1.0, "Regla F3"),
    "solicitudes_mismo_dispositivo": ("Solicitudes desde este dispositivo", 0, 1000, 1, "Regla F4"),
    "intentos_fallidos_otp": ("Intentos fallidos de OTP/SMS", 0, 100, 1, "Regla F8"),
    "score_datacredito": ("Score de centrales de riesgo", 150.0, 950.0, 1.0, "Reglas C1 y C8 · capa difusa"),
    "mora_actual_dias": ("Mora actual (días)", 0, 3650, 1, "Regla C3"),
    "ingresos_mensuales": ("Ingresos mensuales (COP)", 1.0, 1e10, 50000.0, "Denominador de C2, C4 y C9"),
    "monto_cuota_solicitada": ("Cuota solicitada (COP)", 0.0, 1e10, 50000.0, "Reglas C2 y C9 · capa difusa"),
    "deuda_total_mensual": ("Deuda total mensual (COP)", 0.0, 1e10, 50000.0, "Regla C4 · capa difusa"),
    "antiguedad_laboral_meses": ("Antigüedad laboral (meses)", 0, 600, 1, "Regla C5"),
    "ingreso_minimo_requerido": ("Ingreso mínimo del producto (COP)", 0.0, 1e10, 50000.0, "Regla C6"),
}
BOOLEANOS_ID = {
    "dispositivo_nuevo": "Dispositivo nunca usado por el usuario",
    "ubicacion_distinta": "Ubicación distinta al historial",
    "lista_restrictiva": "Coincidencia en lista restrictiva AML/OFAC",
    "email_desechable": "Correo de dominio temporal o desechable",
    "inconsistencia_pais_ip": "País del documento distinto al de la IP",
    "ip_riesgo": "IP con VPN/proxy o zona de alto riesgo",
}
BOOLEANOS_FIN = {
    "embargos_activos": "Embargos o procesos judiciales activos",
    "ingresos_estables": "Ingresos estables y verificables",
}


def cargar(hechos: dict):
    for k, v in hechos.items():
        st.session_state[f"f_{k}"] = v


def al_cambiar_preset():
    nombre = st.session_state["preset_sel"]
    if nombre in PRESETS:
        cargar(PRESETS[nombre])
        st.session_state.pop("resultado_eval", None)


if "f_match_facial" not in st.session_state:
    cargar(PRESETS["Caso 2 · Crédito aprobado"])

estado.avisos_parametros()

st.selectbox("Cargar un caso de ejemplo (opcional)", ["Ingreso manual", *PRESETS], key="preset_sel",
             on_change=al_cambiar_preset,
             help="Los cuatro casos del simulador del Sprint 2, con sus valores exactos.")


def numero(campo):
    etq, lo, hi, paso, ayuda = NUMERICOS[campo]
    entero = isinstance(paso, int)
    st.session_state[f"f_{campo}"] = (int if entero else float)(st.session_state[f"f_{campo}"])
    st.number_input(etq, min_value=lo, max_value=hi, step=paso, key=f"f_{campo}", help=ayuda,
                    format="%d" if entero else ("%.0f" if paso >= 1 else "%.2f"))


with st.form("solicitud"):
    col_id, col_fin = st.columns(2, gap="large")
    with col_id:
        st.markdown("##### Identidad y seguridad")
        st.slider("Coincidencia biométrica (match facial)", 0.0, 1.0, step=0.01, key="f_match_facial",
                  help="Regla F1: por debajo del umbral se rechaza por biometría inválida.")
        for c in ("minutos_registro_a_solicitud", "solicitudes_mismo_dispositivo", "intentos_fallidos_otp"):
            numero(c)
        for k, etq in BOOLEANOS_ID.items():
            st.checkbox(etq, key=f"f_{k}")
    with col_fin:
        st.markdown("##### Datos financieros")
        for c in ("score_datacredito", "mora_actual_dias", "ingresos_mensuales", "monto_cuota_solicitada",
                  "deuda_total_mensual", "antiguedad_laboral_meses", "ingreso_minimo_requerido"):
            numero(c)
        for k, etq in BOOLEANOS_FIN.items():
            st.checkbox(etq, key=f"f_{k}")
    enviado = st.form_submit_button("Evaluar solicitud", type="primary")

CAMPOS = ["match_facial", *NUMERICOS, *BOOLEANOS_ID, *BOOLEANOS_FIN]

if enviado:
    hechos = {c: st.session_state[f"f_{c}"] for c in CAMPOS}
    try:
        st.session_state["resultado_eval"] = (hechos, integracion.evaluar(
            hechos, estado.modelo_ee(), estado.params_se(), estado.config_difusa()))
    except ValueError as e:
        st.session_state.pop("resultado_eval", None)
        st.error(f"No se pudo evaluar la solicitud. {e} Corrige el dato y vuelve a evaluar.")

if "resultado_eval" not in st.session_state:
    st.stop()

hechos, r = st.session_state["resultado_eval"]
se, ee, fz = r["sistema_experto"], r["evolutivo"], r["difuso"]

st.divider()
st.subheader("Resultado")
tarjeta_decision(r["decision_final"], r["motivo_final"], titulo=f"Decisión final · {r['etapa_final']}")

m1, m2, m3 = st.columns(3)
m1.metric("Sistema experto clásico", texto_decision(se.decision), help="Decisión con las 18 reglas rígidas del Sprint 2.")
m2.metric("Score de fraude (EE) / umbral", "No se calculó" if ee["score"] is None else f"{ee['score']:.3f} / {ee['umbral']:.3f}",
          help="Score calibrado por la estrategia evolutiva del Sprint 3; alerta si supera el umbral aprendido.")
m3.metric("Riesgo crediticio difuso", "No se calculó" if fz is None else f"{fz['riesgo']:.1f} / 100 · {fz['etiqueta']}",
          help="Salida de la capa Mamdani del Sprint 4.")

if r["discrepancia_fraude"]:
    st.warning("El score calibrado y el motor de reglas no coinciden sobre el riesgo de fraude. "
               "La decisión sigue la política del sistema experto, pero conviene que la revise un analista.")

tab_exp, tab_fraude, tab_cred, tab_fz, tab_datos = st.tabs(
    ["Explicación", "Fraude", "Crédito", "Lógica difusa", "Datos evaluados"])

with tab_exp:
    criticas = [d for d in se.fraude if d["nivel"] == "CRITICO"]
    medias = [d for d in se.fraude if d["nivel"] == "MEDIO"]
    lineas = [f"**1. Motor de fraude.** {len(criticas)} alerta(s) crítica(s) y {len(medias)} media(s)"
              + (": " + ", ".join(f"{d['id']} {d['consecuencia']}" for d in se.fraude) if se.fraude else "")
              + f". Resultado: *{texto_decision(se.decision) if se.decision in ('RECHAZADO_POR_FRAUDE', 'REVISION_MANUAL') else 'identidad limpia, continúa'}*."]
    if ee["score"] is None:
        lineas.append("**2. Score calibrado (EE).** No se calcula: la biometría (F1) es un control obligatorio y no se superó.")
    else:
        lineas.append(f"**2. Score calibrado (EE).** Score {ee['score']:.3f} frente al umbral aprendido {ee['umbral']:.3f}: "
                      f"*{texto_decision(ee['decision']).lower()}*.")
    if r["credito_clasico"] is None:
        lineas.append("**3–4. Crédito y capa difusa.** No se ejecutan: el cortocircuito de seguridad detiene el flujo "
                      "antes de consultar las centrales de riesgo.")
    else:
        rech = [d for d in se.credito if d["nivel"] == "RECHAZO"]
        fav = [d for d in se.credito if d["nivel"] == "FAVORABLE"]
        lineas.append(f"**3. Motor de crédito clásico.** Reglas de rechazo: "
                      f"{', '.join(d['id'] for d in rech) or 'ninguna'}; favorables: {', '.join(d['id'] for d in fav) or 'ninguna'}. "
                      f"Decisión clásica: *{texto_decision(se.decision)}*.")
        top = sorted((x for x in fz["reglas"] if x["activacion"] > 0), key=lambda x: -x["activacion"])
        lineas.append(f"**4. Capa difusa.** Riesgo {fz['riesgo']:.1f}/100, etiqueta dominante *{fz['etiqueta']}*. "
                      f"Reglas con más peso: " + "; ".join(f"{x['id']} ({x['activacion']:.2f})" for x in top[:3]) + ".")
        if r["rigidas_disparadas"]:
            lineas.append("**Decisión.** Una regla rígida que la capa difusa no flexibiliza se impone: "
                          + ", ".join(d["id"] for d in r["rigidas_disparadas"]) + ".")
        elif se.decision != r["decision_final"]:
            lineas.append(f"**Diferencia con el sistema clásico.** Con las fronteras rígidas la decisión habría sido "
                          f"*{texto_decision(se.decision)}*; la capa difusa la cambia a *{texto_decision(r['decision_final'])}* "
                          "porque el perfil está cerca de los umbrales.")
    st.markdown("\n\n".join(lineas))

with tab_fraude:
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("##### Reglas F1–F9 disparadas (Sprint 2)")
        lista_reglas(se.fraude, "Ninguna regla de fraude se disparó.")
        st.caption("Matriz de decisión: 1 crítica o ≥ 2 medias → rechazo · exactamente 1 media → revisión manual.")
    with b:
        st.markdown("##### Score calibrado por la EE (Sprint 3)")
        if ee["score"] is None:
            st.info(ee["motivo"])
        else:
            st.progress(min(ee["score"], 1.0), text=f"Score {ee['score']:.3f} · umbral {ee['umbral']:.3f}")
            st.dataframe(pd.DataFrame(ee["aportes"]).rename(columns={
                "criterio": "Señal", "activa": "Activa", "peso_relativo": "Peso relativo", "aporte": "Aporte"}),
                hide_index=True, width="stretch",
                column_config={"Peso relativo": st.column_config.NumberColumn(format="percent"),
                               "Aporte": st.column_config.NumberColumn(format="%.4f")})

with tab_cred:
    if r["credito_clasico"] is None:
        st.info("La evaluación crediticia se omitió por el resultado del motor de fraude.")
    else:
        cond = condiciones_legibles(estado.params_se())
        st.markdown("##### Reglas C1–C9 disparadas")
        lista_reglas(se.credito, "Ninguna regla de crédito se disparó.")
        filas = []
        for d in se.credito:
            papel = ("Rígida (bloquea siempre)" if d["id"] in integracion.REGLAS_RIGIDAS_NO_DIFUSAS
                     else "Reemplazada por la capa difusa" if d["id"] in integracion.REGLAS_REEMPLAZADAS_POR_DIFUSA
                     else "Informativa")
            filas.append({"Regla": d["id"], "Condición": cond[d["id"]], "Nivel": d["nivel"], "Papel en el flujo integrado": papel})
        if filas:
            st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
        ing = hechos["ingresos_mensuales"]
        st.caption(f"Cuota / ingresos = {pesos(hechos['monto_cuota_solicitada'])} / {pesos(ing)} = "
                   f"{hechos['monto_cuota_solicitada'] / max(ing, 1):.3f} · Deuda / ingresos = "
                   f"{hechos['deuda_total_mensual'] / max(ing, 1):.3f}")

with tab_fz:
    if fz is None:
        st.info("La capa difusa no se ejecuta cuando el motor de fraude detiene la solicitud.")
    else:
        cfg = estado.config_difusa()
        cols = st.columns(3)
        for col, (clave, var) in zip(cols, cfg["variables"].items()):
            with col, st.container(border=True):
                st.markdown(f"**{var['nombre']}**")
                st.caption(f"Valor: {fz['entradas'][clave]:.3f}" if clave != "score" else f"Valor: {fz['entradas'][clave]:.0f}")
                for etq, mu in fz["grados"][clave].items():
                    st.progress(mu, text=f"{etq}: μ = {mu:.2f}")
        st.plotly_chart(grafico_salida(fz, cfg["salida"]), width="stretch")
        st.markdown("##### Reglas evaluadas (Y = mínimo)")
        st.dataframe(pd.DataFrame([{"Regla": x["id"], "Enunciado": x["texto"], "Origen": x["origen"],
                                    "Activación": x["activacion"]} for x in fz["reglas"]]),
                     hide_index=True, width="stretch",
                     column_config={"Activación": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})

with tab_datos:
    st.caption("Diccionario de hechos exacto que recibieron los motores.")
    st.json(hechos, expanded=True)

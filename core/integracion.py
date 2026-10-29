"""
Flujo integrado de una solicitud de crédito (Sprints 2, 3 y 4).

Orden de ejecución (el cortocircuito del Sprint 2 se conserva intacto):

  1. Motor de fraude del sistema experto (F1–F9).
       crítica o ≥2 medias  -> RECHAZADO_POR_FRAUDE      (fin)
       exactamente 1 media  -> REVISION_MANUAL           (fin)
  2. Score de fraude calibrado con la estrategia evolutiva (Sprint 3) sobre
     las mismas señales F1–F9. Es una SEGUNDA OPINIÓN: se reporta, y si
     contradice al sistema experto se marca para el analista, pero no cambia
     la decisión (el sistema experto es la política auditable vigente).
  3. Motor de crédito del sistema experto (C1–C9) -> decisión clásica.
  4. Capa difusa (Sprint 4) sobre score, carga de cuota y DTI -> riesgo 0–100.
     Las reglas que la capa difusa NO modela (C3 mora, C5 antigüedad,
     C6 ingreso mínimo, C7 embargo) siguen siendo bloqueantes y rígidas.
     Si ninguna de ellas se dispara, la acción la da la etiqueta difusa:
     bajo -> APROBADO · medio -> REVISION_MANUAL · alto -> RECHAZO.
"""
from __future__ import annotations

from core import difuso
from core.evolutivo import evaluar_solicitud as evaluar_ee, señales_desde_hechos
from core.sistema_experto import SistemaExpertoOriginacionCredito

REGLAS_RIGIDAS_NO_DIFUSAS = {"C3", "C5", "C6", "C7"}
REGLAS_REEMPLAZADAS_POR_DIFUSA = {"C1", "C2", "C4"}

CAMPOS = {
    # campo: (tipo, mínimo, máximo o None)
    "match_facial": (float, 0.0, 1.0),
    "minutos_registro_a_solicitud": (float, 0.0, None),
    "solicitudes_mismo_dispositivo": (int, 0, None),
    "intentos_fallidos_otp": (int, 0, None),
    "score_datacredito": (float, 150.0, 950.0),
    "mora_actual_dias": (int, 0, None),
    "ingresos_mensuales": (float, 1.0, None),
    "monto_cuota_solicitada": (float, 0.0, None),
    "deuda_total_mensual": (float, 0.0, None),
    "antiguedad_laboral_meses": (int, 0, None),
    "ingreso_minimo_requerido": (float, 0.0, None),
}
BOOLEANOS = ["dispositivo_nuevo", "ubicacion_distinta", "lista_restrictiva", "email_desechable",
             "inconsistencia_pais_ip", "ip_riesgo", "embargos_activos", "ingresos_estables"]


def validar_solicitud(hechos: dict) -> list[str]:
    """Devuelve una lista de errores legibles (vacía si la solicitud es válida)."""
    errores = []
    for campo, (tipo, lo, hi) in CAMPOS.items():
        v = hechos.get(campo)
        if v is None or v == "":
            errores.append(f"Falta el campo «{campo}».")
            continue
        try:
            v = tipo(v)
        except (TypeError, ValueError):
            errores.append(f"«{campo}» debe ser numérico.")
            continue
        if v != v:  # NaN
            errores.append(f"«{campo}» no es un número válido.")
        elif lo is not None and v < lo:
            errores.append(f"«{campo}» no puede ser menor que {lo:g}.")
        elif hi is not None and v > hi:
            errores.append(f"«{campo}» no puede ser mayor que {hi:g}.")
    for campo in BOOLEANOS:
        if not isinstance(hechos.get(campo), bool):
            errores.append(f"«{campo}» debe ser verdadero o falso.")
    return errores


def evaluar(hechos: dict, modelo_ee: dict, params_se: dict | None = None, config_difusa=None) -> dict:
    errores = validar_solicitud(hechos)
    if errores:
        raise ValueError(" ".join(errores))

    se = SistemaExpertoOriginacionCredito(params_se)
    res_se = se.evaluar_solicitud(hechos)

    # Sprint 3: misma evidencia de fraude, score calibrado por la EE.
    señales = señales_desde_hechos(res_se.fraude)
    estado_bio = "VERIFICADA" if señales[0] == 0 else "REQUIERE_VERIFICACION"
    res_ee = evaluar_ee(señales, estado_bio, modelo_ee)

    salida = {"sistema_experto": res_se, "evolutivo": res_ee, "señales": señales,
              "difuso": None, "credito_clasico": None, "rigidas_disparadas": []}

    fraude_bloquea = res_se.decision in ("RECHAZADO_POR_FRAUDE", "REVISION_MANUAL")
    ee_alerta = res_ee["decision"] != "SIN_ALERTA_DEL_MODELO"
    salida["discrepancia_fraude"] = (ee_alerta and not fraude_bloquea) or (not ee_alerta and res_se.decision == "RECHAZADO_POR_FRAUDE")

    if fraude_bloquea:
        salida.update(decision_final=res_se.decision, etapa_final="Motor de fraude (Sprint 2)",
                      motivo_final=res_se.motivo)
        return salida

    credito = res_se.credito
    salida["credito_clasico"] = res_se.decision
    rigidas = [d for d in credito if d["id"] in REGLAS_RIGIDAS_NO_DIFUSAS]
    salida["rigidas_disparadas"] = rigidas

    entradas = difuso.preparar_entradas(hechos["score_datacredito"], hechos["monto_cuota_solicitada"],
                                        hechos["ingresos_mensuales"], hechos["deuda_total_mensual"])
    res_fz = difuso.inferir(entradas, config_difusa)
    salida["difuso"] = res_fz

    if rigidas:
        salida.update(decision_final="RECHAZADO_POR_RIESGO_FINANCIERO",
                      etapa_final="Reglas rígidas del motor de crédito (Sprint 2)",
                      motivo_final="Se disparó una regla que no se flexibiliza: "
                                   + ", ".join(f"{d['id']} {d['consecuencia']}" for d in rigidas) + ".")
    else:
        motivos = {
            "APROBADO": "Riesgo crediticio difuso bajo.",
            "REVISION_MANUAL": "Riesgo crediticio difuso medio: el perfil está en la zona de transición y lo debe revisar un analista.",
            "RECHAZADO_POR_RIESGO_FINANCIERO": "Riesgo crediticio difuso alto.",
        }
        salida.update(decision_final=res_fz["accion"], etapa_final="Capa difusa (Sprint 4)",
                      motivo_final=motivos[res_fz["accion"]])
    return salida

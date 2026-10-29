"""
Sprint 2 · Representación del conocimiento — Sistema experto de doble motor.

Fuente: "Sistema Experto_ Nequi-....html" (código Python del panel 2 y su espejo
JavaScript, que es la versión completa de las condiciones).

- Motor de fraude (F1–F9) y motor de crédito (C1–C9), ambos con encadenamiento
  hacia adelante sobre un diccionario de hechos.
- Cortocircuito de seguridad: el fraude se evalúa SIEMPRE primero.
- Umbrales por defecto = DEFAULT_PARAMS del archivo original. Son editables,
  pero la aplicación nunca los cambia por su cuenta.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Umbrales editables del archivo original (Editor Live de Reglas).
DEFAULT_PARAMS: dict[str, float] = {
    "F1": 0.80, "F3": 2, "F4": 3, "F8": 3,
    "C1": 600, "C2": 0.35, "C3": 30, "C4": 0.70, "C5": 6, "C8": 750, "C9": 0.20,
}


class MotorInferencia:
    """Motor genérico de encadenamiento hacia adelante (forward chaining)."""

    def __init__(self, reglas):
        self.reglas = reglas

    def ejecutar(self, hechos: dict) -> list[dict]:
        deducciones = []
        for regla in self.reglas:
            try:
                if regla["condicion"](hechos):
                    deducciones.append({
                        "id": regla["id"],
                        "consecuencia": regla["consecuencia"],
                        "nivel": regla.get("nivel", "INFO"),
                    })
            except KeyError:
                # Igual que el original: una llave faltante no detiene el motor.
                continue
        return deducciones


def _ratio(h, numerador):
    return h.get(numerador, 0) / max(h.get("ingresos_mensuales", 1), 1)


def construir_reglas_fraude(p: dict | None = None) -> list[dict]:
    p = {**DEFAULT_PARAMS, **(p or {})}
    return [
        {"id": "F1", "nivel": "CRITICO", "consecuencia": "BIOMETRIA_INVALIDA",
         "condicion": lambda h: h.get("match_facial", 1.0) < p["F1"]},
        {"id": "F2", "nivel": "MEDIO", "consecuencia": "CAMBIO_DISPOSITIVO_UBICACION",
         "condicion": lambda h: h.get("dispositivo_nuevo", False) and h.get("ubicacion_distinta", False)},
        {"id": "F3", "nivel": "MEDIO", "consecuencia": "VELOCIDAD_ANORMAL",
         "condicion": lambda h: h.get("minutos_registro_a_solicitud", 99) < p["F3"]},
        {"id": "F4", "nivel": "CRITICO", "consecuencia": "GRANJA_DE_DISPOSITIVOS",
         "condicion": lambda h: h.get("solicitudes_mismo_dispositivo", 0) > p["F4"]},
        {"id": "F5", "nivel": "CRITICO", "consecuencia": "COINCIDENCIA_LISTA_AML_OFAC",
         "condicion": lambda h: h.get("lista_restrictiva", False)},
        {"id": "F6", "nivel": "MEDIO", "consecuencia": "DOMINIO_CORREO_TEMPORAL",
         "condicion": lambda h: h.get("email_desechable", False)},
        {"id": "F7", "nivel": "CRITICO", "consecuencia": "PAIS_DOCUMENTO_VS_IP_INCONSISTENTE",
         "condicion": lambda h: h.get("inconsistencia_pais_ip", False)},
        {"id": "F8", "nivel": "MEDIO", "consecuencia": "FALLOS_VERIFICACION_OTP",
         "condicion": lambda h: h.get("intentos_fallidos_otp", 0) >= p["F8"]},
        {"id": "F9", "nivel": "MEDIO", "consecuencia": "IP_VPN_O_ZONA_ALTO_RIESGO",
         "condicion": lambda h: h.get("ip_riesgo", False)},
    ]


def construir_reglas_credito(p: dict | None = None) -> list[dict]:
    p = {**DEFAULT_PARAMS, **(p or {})}
    return [
        {"id": "C1", "nivel": "RECHAZO", "consecuencia": "SCORE_CREDITICIO_BAJO",
         "condicion": lambda h: h.get("score_datacredito", 0) < p["C1"]},
        {"id": "C2", "nivel": "RECHAZO", "consecuencia": "CAPACIDAD_DE_PAGO_EXCEDIDA",
         "condicion": lambda h: _ratio(h, "monto_cuota_solicitada") > p["C2"]},
        {"id": "C3", "nivel": "RECHAZO", "consecuencia": "CLIENTE_EN_MORA",
         "condicion": lambda h: h.get("mora_actual_dias", 0) > p["C3"]},
        {"id": "C4", "nivel": "RECHAZO", "consecuencia": "ENDEUDAMIENTO_DTI_EXCESIVO",
         "condicion": lambda h: _ratio(h, "deuda_total_mensual") > p["C4"]},
        {"id": "C5", "nivel": "RECHAZO", "consecuencia": "ANTIGUEDAD_LABORAL_INSUFICIENTE",
         "condicion": lambda h: h.get("antiguedad_laboral_meses", 99) < p["C5"]},
        {"id": "C6", "nivel": "RECHAZO", "consecuencia": "INGRESOS_BAJO_UMBRAL_PRODUCTO",
         "condicion": lambda h: h.get("ingresos_mensuales", 0) < h.get("ingreso_minimo_requerido", 0)},
        {"id": "C7", "nivel": "RECHAZO", "consecuencia": "EMBARGO_O_PROCESO_JUDICIAL",
         "condicion": lambda h: h.get("embargos_activos", False)},
        {"id": "C8", "nivel": "FAVORABLE", "consecuencia": "HISTORIAL_EXCELENTE",
         "condicion": lambda h: h.get("score_datacredito", 0) >= p["C8"] and h.get("mora_actual_dias", 0) == 0},
        {"id": "C9", "nivel": "FAVORABLE", "consecuencia": "CAPACIDAD_HOLGADA",
         "condicion": lambda h: _ratio(h, "monto_cuota_solicitada") <= p["C9"] and h.get("ingresos_estables", False)},
    ]


@dataclass
class ResultadoSE:
    decision: str
    motivo: str
    fraude: list[dict]
    credito: list[dict]
    credito_evaluado: bool = field(default=True)

    @property
    def auditoria_fraude(self):
        return [d["consecuencia"] for d in self.fraude]

    @property
    def auditoria_credito(self):
        if not self.credito_evaluado:
            return ["EVALUACION_CREDITICIA_OMITIDA" if self.decision == "RECHAZADO_POR_FRAUDE"
                    else "EVALUACION_CREDITICIA_PENDIENTE"]
        return [d["consecuencia"] for d in self.credito]


class SistemaExpertoOriginacionCredito:
    def __init__(self, params: dict | None = None):
        self.params = {**DEFAULT_PARAMS, **(params or {})}
        self.motor_fraude = MotorInferencia(construir_reglas_fraude(self.params))
        self.motor_credito = MotorInferencia(construir_reglas_credito(self.params))

    def evaluar_fraude(self, solicitud: dict) -> list[dict]:
        return self.motor_fraude.ejecutar(solicitud)

    def evaluar_credito(self, solicitud: dict) -> list[dict]:
        return self.motor_credito.ejecutar(solicitud)

    def evaluar_solicitud(self, solicitud: dict) -> ResultadoSE:
        # 1. Motor de fraude — SIEMPRE va primero
        ded_fraude = self.evaluar_fraude(solicitud)
        criticas = [d for d in ded_fraude if d["nivel"] == "CRITICO"]
        medias = [d for d in ded_fraude if d["nivel"] == "MEDIO"]

        # Cortocircuito de seguridad
        if criticas or len(medias) >= 2:
            return ResultadoSE("RECHAZADO_POR_FRAUDE",
                               "Se detectaron patrones de suplantación o riesgo de identidad.",
                               ded_fraude, [], credito_evaluado=False)
        # Caso límite: una sola alerta media -> analista humano
        if len(medias) == 1:
            return ResultadoSE("REVISION_MANUAL",
                               "Señal de riesgo aislada: requiere verificación de un analista.",
                               ded_fraude, [], credito_evaluado=False)

        # 2. Identidad limpia -> motor de crédito
        ded_credito = self.evaluar_credito(solicitud)
        if any(d["nivel"] == "RECHAZO" for d in ded_credito):
            return ResultadoSE("RECHAZADO_POR_RIESGO_FINANCIERO",
                               "El cliente no cumple los criterios de política crediticia.",
                               ded_fraude, ded_credito)
        return ResultadoSE("APROBADO",
                           "Solicitud viable financieramente y sin riesgo de identidad.",
                           ded_fraude, ded_credito)


# Condición legible de cada regla (glosario), con el umbral vigente.
def condiciones_legibles(p: dict | None = None) -> dict[str, str]:
    p = {**DEFAULT_PARAMS, **(p or {})}
    return {
        "F1": f"match_facial < {p['F1']}",
        "F2": "dispositivo_nuevo AND ubicacion_distinta",
        "F3": f"minutos_registro_a_solicitud < {p['F3']:g}",
        "F4": f"solicitudes_mismo_dispositivo > {p['F4']:g}",
        "F5": "lista_restrictiva == true",
        "F6": "email_desechable == true",
        "F7": "inconsistencia_pais_ip == true",
        "F8": f"intentos_fallidos_otp >= {p['F8']:g}",
        "F9": "ip_riesgo == true",
        "C1": f"score_datacredito < {p['C1']:g}",
        "C2": f"cuota / ingresos > {p['C2']}",
        "C3": f"mora_actual_dias > {p['C3']:g}",
        "C4": f"deuda_total / ingresos > {p['C4']}",
        "C5": f"antiguedad_laboral_meses < {p['C5']:g}",
        "C6": "ingresos_mensuales < ingreso_minimo_requerido",
        "C7": "embargos_activos == true",
        "C8": f"score >= {p['C8']:g} AND mora == 0",
        "C9": f"cuota / ingresos <= {p['C9']} AND ingresos_estables",
    }


# "Por qué existe" de cada regla — Diccionario de reglas del archivo original.
GLOSARIO = {
    "F1": ("BIOMETRIA_INVALIDA", "CRITICO", "La selfie no corresponde al documento: la firma más fuerte de suplantación."),
    "F2": ("CAMBIO_DISPOSITIVO_UBICACION", "MEDIO", "Dispositivo nunca visto + ubicación fuera del historial: patrón de cuenta comprometida."),
    "F3": ("VELOCIDAD_ANORMAL", "MEDIO", "Solicitud casi instantánea tras el registro: sugiere un flujo automatizado."),
    "F4": ("GRANJA_DE_DISPOSITIVOS", "CRITICO", "Un mismo dispositivo detrás de muchas solicitudes: granja de fraude."),
    "F5": ("COINCIDENCIA_LISTA_AML_OFAC", "CRITICO", "Obligación regulatoria directa (AML/OFAC)."),
    "F6": ("DOMINIO_CORREO_TEMPORAL", "MEDIO", "Correos desechables dificultan el rastreo tras el fraude."),
    "F7": ("PAIS_DOCUMENTO_VS_IP_INCONSISTENTE", "CRITICO", "País del documento distinto al de la IP: manipulación o acceso remoto."),
    "F8": ("FALLOS_VERIFICACION_OTP", "MEDIO", "Quien se verifica no controla el canal del titular."),
    "F9": ("IP_VPN_O_ZONA_ALTO_RIESGO", "MEDIO", "VPN/proxy o zona de alto riesgo; no es prueba definitiva, por eso es nivel medio."),
    "C1": ("SCORE_CREDITICIO_BAJO", "RECHAZO", "Bajo 600 el riesgo estadístico de impago es significativamente mayor."),
    "C2": ("CAPACIDAD_DE_PAGO_EXCEDIDA", "RECHAZO", "35% es el estándar de mercado para no comprometer la subsistencia."),
    "C3": ("CLIENTE_EN_MORA", "RECHAZO", "Dar crédito a quien ya incumple multiplica el riesgo de pérdida."),
    "C4": ("ENDEUDAMIENTO_DTI_EXCESIVO", "RECHAZO", "Mira toda la carga financiera, no solo esta cuota."),
    "C5": ("ANTIGUEDAD_LABORAL_INSUFICIENTE", "RECHAZO", "Un ingreso muy reciente es más volátil y difícil de verificar."),
    "C6": ("INGRESOS_BAJO_UMBRAL_PRODUCTO", "RECHAZO", "Cada producto tiene un piso de ingresos definido por política."),
    "C7": ("EMBARGO_O_PROCESO_JUDICIAL", "RECHAZO", "Un embargo puede tomar directamente los ingresos del cliente."),
    "C8": ("HISTORIAL_EXCELENTE", "FAVORABLE", "Identifica al cliente de menor riesgo (no aprueba por sí sola)."),
    "C9": ("CAPACIDAD_HOLGADA", "FAVORABLE", "Marca al cliente con más margen frente a la cuota."),
}

# Los 4 casos predefinidos del simulador original (valores exactos).
PRESETS: dict[str, dict] = {
    "Caso 1 · Fraude detectado": dict(
        match_facial=0.45, dispositivo_nuevo=True, ubicacion_distinta=True,
        minutos_registro_a_solicitud=1, solicitudes_mismo_dispositivo=5,
        lista_restrictiva=False, email_desechable=True, inconsistencia_pais_ip=False,
        intentos_fallidos_otp=0, ip_riesgo=False,
        score_datacredito=820, mora_actual_dias=0, ingresos_mensuales=9_000_000,
        monto_cuota_solicitada=1_500_000, deuda_total_mensual=2_000_000,
        antiguedad_laboral_meses=36, ingreso_minimo_requerido=1_200_000,
        embargos_activos=False, ingresos_estables=True),
    "Caso 2 · Crédito aprobado": dict(
        match_facial=0.97, dispositivo_nuevo=False, ubicacion_distinta=False,
        minutos_registro_a_solicitud=60, solicitudes_mismo_dispositivo=1,
        lista_restrictiva=False, email_desechable=False, inconsistencia_pais_ip=False,
        intentos_fallidos_otp=0, ip_riesgo=False,
        score_datacredito=790, mora_actual_dias=0, ingresos_mensuales=5_000_000,
        monto_cuota_solicitada=700_000, deuda_total_mensual=900_000,
        antiguedad_laboral_meses=48, ingreso_minimo_requerido=1_200_000,
        embargos_activos=False, ingresos_estables=True),
    "Caso 3 · Crédito rechazado": dict(
        match_facial=0.95, dispositivo_nuevo=False, ubicacion_distinta=False,
        minutos_registro_a_solicitud=40, solicitudes_mismo_dispositivo=1,
        lista_restrictiva=False, email_desechable=False, inconsistencia_pais_ip=False,
        intentos_fallidos_otp=0, ip_riesgo=False,
        score_datacredito=520, mora_actual_dias=45, ingresos_mensuales=1_800_000,
        monto_cuota_solicitada=900_000, deuda_total_mensual=1_400_000,
        antiguedad_laboral_meses=18, ingreso_minimo_requerido=1_200_000,
        embargos_activos=False, ingresos_estables=True),
    "Caso 4 · Revisión manual": dict(
        match_facial=0.93, dispositivo_nuevo=True, ubicacion_distinta=False,
        minutos_registro_a_solicitud=25, solicitudes_mismo_dispositivo=1,
        lista_restrictiva=False, email_desechable=False, inconsistencia_pais_ip=False,
        intentos_fallidos_otp=0, ip_riesgo=False,
        score_datacredito=700, mora_actual_dias=0, ingresos_mensuales=3_000_000,
        monto_cuota_solicitada=500_000, deuda_total_mensual=700_000,
        antiguedad_laboral_meses=20, ingreso_minimo_requerido=1_200_000,
        embargos_activos=False, ingresos_estables=True),
}

# Decisión con la que el archivo original ETIQUETA cada preset.
# Ojo: el Caso 4 está etiquetado como revisión manual, pero con las reglas del
# mismo archivo no dispara ninguna alerta media (F2 exige dispositivo nuevo Y
# ubicación distinta, y el caso solo trae la primera), así que el motor lo
# aprueba. No se corrige en silencio: la página de validación lo reporta.
DECISION_ETIQUETADA_PRESET = {
    "Caso 1 · Fraude detectado": "RECHAZADO_POR_FRAUDE",
    "Caso 2 · Crédito aprobado": "APROBADO",
    "Caso 3 · Crédito rechazado": "RECHAZADO_POR_RIESGO_FINANCIERO",
    "Caso 4 · Revisión manual": "REVISION_MANUAL",
}

# Nequi IA · Sistema inteligente de originación de crédito y antifraude

Aplicación Streamlit que integra en un solo flujo el proyecto semestral de **Fundamentos de IA**
(Universidad EIA, 2026-2), aplicado a un caso **ficticio** de Nequi:

| Sprint | Técnica | Qué hace en la aplicación |
|---|---|---|
| 1 | Búsqueda informada (A\*) | Ruta de entrega de la tarjeta física (Bogotá → hub → barrio → cliente) y orden de entrega óptimo (regla de Smith, verificada con A\* y fuerza bruta). |
| 2 | Sistema experto | 18 reglas de fraude (F1–F9) y crédito (C1–C9) con encadenamiento hacia adelante y cortocircuito de seguridad. |
| 3 | Estrategia evolutiva (μ+λ) | Calibra los pesos y el umbral del score de fraude (fitness = F1-score). |
| 3 | Teoría de juegos + coevolución | Defensor contra atacante con pagos económicos; equilibrio verificado con ε-Nash, matriz de pagos y juego de inspección 2×2. |
| 4 | Lógica difusa (Mamdani) | Reemplaza las fronteras rígidas de score, carga de la cuota y DTI por un riesgo continuo de 0 a 100, con una zona de revisión manual. |

> Todos los datos son simulados y todos los parámetros son supuestos académicos. No se usan datos ni sistemas reales de Nequi.

## Flujo de una solicitud

1. **Motor de fraude (S2).** Una alerta crítica o dos medias → rechazo; una media → revisión manual. En esos casos el flujo termina.
2. **Score calibrado (S3).** Segunda opinión sobre las mismas señales; si contradice al motor de reglas, se marca para el analista.
3. **Motor de crédito (S2).** Su decisión clásica se muestra siempre. Mora, antigüedad laboral, ingreso mínimo y embargo siguen siendo filtros rígidos.
4. **Capa difusa (S4).** Riesgo de 0 a 100: bajo → aprobado, medio → revisión manual, alto → rechazo.

El análisis completo (síntesis de cada sprint, mapa de integración, contradicciones encontradas y justificación de la
lógica difusa) está en [`docs/ANALISIS.md`](docs/ANALISIS.md).

## Requisitos

- Python 3.10 o superior (probado con 3.11)
- Dependencias en `requirements.txt` (Streamlit, NumPy, pandas, Plotly)

## Ejecución local

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     ·     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

La aplicación abre en `http://localhost:8501`.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q
```

Las pruebas usan los mismos casos de la página **Validación y pruebas** (`core/casos_prueba.py`) y además verifican
que el código reproduce los resultados de los notebooks: EE con F1 = 0.8947 y umbral 0.2924, y coevolución v2 con
umbral 0.193.

## Estructura del repositorio

```
nequi-ia-app/
├── app.py                    # Punto de entrada: configuración y navegación
├── core/                     # Lógica de negocio (sin dependencia de Streamlit)
│   ├── busqueda.py           # S1 · grafo, A*, heurística por capas, políticas de entrega
│   ├── sistema_experto.py    # S2 · motor de inferencia, reglas F/C, presets
│   ├── evolutivo.py          # S3 · estrategia evolutiva (μ+λ) del score de fraude
│   ├── teoria_juegos.py      # S3 · coevolución con pagos económicos (v2) y análisis de equilibrio
│   ├── teoria_juegos_v4.py   # S3 · versión simplificada v4 (supuestos propios)
│   ├── difuso.py             # S4 · funciones de pertenencia, reglas y Mamdani
│   ├── integracion.py        # Flujo integrado S2 → S3 → S2 → S4 y validación de entradas
│   └── casos_prueba.py       # Casos de prueba compartidos por la UI y pytest
├── ui/
│   ├── componentes.py        # Estilos, tarjetas de decisión y gráficos
│   └── estado.py             # Estado de sesión y caché de cálculos
├── vistas/                   # Una página por sección
├── tests/test_casos.py
├── docs/ANALISIS.md
├── .streamlit/config.toml
├── requirements.txt
└── requirements-dev.txt
```

## Despliegue en Streamlit Community Cloud

1. Sube esta carpeta a un repositorio público de GitHub (por ejemplo `mapsita123/nequi-ia-streamlit`):
   ```bash
   git init
   git add .
   git commit -m "App integrada Nequi IA"
   git branch -M main
   git remote add origin https://github.com/mapsita123/nequi-ia-streamlit.git
   git push -u origin main
   ```
2. Entra a [share.streamlit.io](https://share.streamlit.io) con la cuenta de GitHub y elige **Create app**.
3. Selecciona el repositorio, la rama `main` y el archivo principal `app.py`.
4. Pulsa **Deploy**. Streamlit instala `requirements.txt` automáticamente.

La aplicación no usa credenciales ni secretos. `.streamlit/secrets.toml` está en `.gitignore` por si se agregan después.

## Notas de rendimiento

- La estrategia evolutiva tarda unos segundos la primera vez y queda en caché.
- La coevolución v2 con el test ε-Nash tarda entre 20 y 30 s; la v4, unos 45 s. Ambas quedan en caché por combinación de parámetros.

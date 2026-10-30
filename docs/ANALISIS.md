# Análisis previo, mapa de integración y justificación técnica

Proyecto semestral de Fundamentos de IA (Universidad EIA, 2026-2) sobre un caso **ficticio** de Nequi.
Este documento reconstruye la evolución del proyecto a partir de los archivos entregados y explica cómo se
integró en una sola aplicación Streamlit.

## 1. Fuentes analizadas

| Archivo | Contenido | Sprint |
|---|---|---|
| `mapas-reales-ciudades (1).html` | Red de reparto (hubs, barrios, clientes), costos, heurística por capas y coordenadas reales | 1 · A* |
| `Sistema Experto_ Nequi-….html` | Motor de inferencia, 18 reglas F1–F9 / C1–C9, cortocircuito, editor de umbrales y 4 casos | 2 · Sistema experto |
| `Algoritmo_Genético_Nequi (3).ipynb` | Estrategia evolutiva (μ+λ) que calibra los pesos F2–F9 y el umbral (fitness = F1-score) | 3 · Evolutivos |
| `Teoria_d_ejuegos (1).ipynb` | Coevolución defensor vs. atacante con pagos económicos, F10, ε-Nash y juego de inspección 2×2 (v2) | 3 · Teoría de juegos |
| `Teoria_de_juegos_nequi_v4_simple.ipynb` | Versión simplificada v4 con supuestos propios | 3 · Teoría de juegos |
| `Brecha Nequi.html`, `Duelo Antifraude Nequi.html` | Juegos y explicadores interactivos para la sustentación (v2/v3) | 3 · apoyo visual |
| `09_Logica_Difusa_Mercado_Libre_corregido.ipynb` | Notebook de clase: trimf, trapmf, Mamdani, centroide | 4 · Lógica difusa |

## 2. Síntesis de cada sprint

**Sprint 1 · Búsqueda informada (A\*).** Las tarjetas salen de Bogotá hacia tres hubs (Medellín 8.0 h,
Bucaramanga 7.0 h, Cartagena 11.5 h) y de ahí a barrios y clientes. A\* usa una heurística admisible por capas
(mínimo costo conocido de cada nivel: 0.45 en el hub, 0.15 en barrios, 0 en clientes). Las políticas de entrega
se comparan por Σ wᵢCᵢ (Premium 3.0, Regular 1.0). La ponderada coincide con la regla de Smith (WSPT) y se
verifica contra A\* sobre permutaciones y contra fuerza bruta.

**Sprint 2 · Sistema experto.** Dos motores de encadenamiento hacia adelante: fraude (F1–F9, críticas y medias)
y crédito (C1–C7 de rechazo, C8–C9 favorables). El fraude siempre va primero: una crítica o dos medias
rechazan, una media envía a revisión manual y, en esos casos, el crédito no se evalúa.

**Sprint 3 · Estrategia evolutiva.** (μ+λ) = (20+100), 60 generaciones y σ autoadaptativo. Calibra 8 pesos
(F2–F9) y el umbral. F1 es un control obligatorio fuera del score. Resultado reproducido: F1 de entrenamiento
0.8947, F1 de prueba 0.8889 y umbral 0.2924.

**Sprint 3 · Teoría de juegos.** Coevolución de defensores y atacantes cuyo fitness es el pago económico
(prevalencia de fraude 2 %, botín de 1.0 + 0.6 por señal, costo de 0.15 por falso positivo). F10 es una señal
estructural que el atacante no controla. El equilibrio se verifica con matriz de pagos, Nash puro, dominancia,
maximin, test de desviación (ε-Nash), comparación con una regla fija y un juego de inspección 2×2 resuelto
por indiferencia (p\* ≈ 0.559, q\* ≈ 0.214).

**Sprint 4 · Lógica difusa.** El notebook de clase usa un caso de Mercado Libre. En el proyecto se aplica a los
umbrales rígidos del motor de crédito (ver sección 5).

## 3. Mapa de integración

```
                 ┌───────────────────────── Evaluar una solicitud ─────────────────────────┐
 Solicitud ──►  [S2] Motor de fraude F1–F9 ──► crítica o ≥2 medias ──► RECHAZO POR FRAUDE (fin)
                      │                    └─► 1 media ──────────────► REVISIÓN MANUAL (fin)
                      │ (umbrales editables en la página del S2)
                      ├─► [S3] Score calibrado por la EE (mismas señales) ─► segunda opinión / discrepancia
                      ▼
                 [S2] Motor de crédito C1–C9 ──► decisión clásica (se muestra siempre)
                      │
                      ├─► C3, C5, C6, C7 rígidas ──► RECHAZO FINANCIERO
                      ▼
                 [S4] Capa difusa sobre C1, C2, C4 (conjuntos anclados en los umbrales del S2)
                      └─► riesgo 0–100 ─► bajo: APROBADO · medio: REVISIÓN MANUAL · alto: RECHAZO

 Páginas de componente: [S1] Logística A* · [S2] reglas y umbrales · [S3] EE · [S3] Teoría de juegos (v2 y v4)
 · [S3] Juego Brecha Nequi · [S4] diseño difuso · Validación (casos en vivo + coherencia EE/SE sobre 512 combinaciones)
```

Dependencias: el S3 consume las señales que produce el S2. El S4 construye sus conjuntos a partir de los
umbrales vigentes del S2, así que si se edita C1 la frontera difusa se mueve con él y no hay parámetros duplicados.
La teoría de juegos usa el mismo esquema de score con F1 como gate obligatorio que la EE. El S1 es independiente
del flujo de crédito (la entrega ocurre después de la aprobación) y se presenta como su propio módulo.

## 4. Contradicciones y vacíos encontrados, y cómo se resolvieron

| # | Hallazgo | Resolución |
|---|---|---|
| C1 | El preset **«Caso 4 · Revisión manual»** del sistema experto no dispara ninguna alerta media: F2 exige `dispositivo_nuevo` **y** `ubicacion_distinta`, y el caso solo trae la primera. Con las reglas del mismo archivo, el motor lo **aprueba**. | No se modificó ni el caso ni la regla. La aplicación muestra la discrepancia (página del S2 y Validación), y la prueba automática la registra como la única discrepancia conocida. Para que sea una revisión manual habría que poner `ubicacion_distinta = True` o cambiar F2; esa decisión le corresponde al equipo. |
| C2 | Hay **dos modelos de teoría de juegos con supuestos distintos**. v2: señales F1–F9 del SE + F10, prevalencia 2 %, falso positivo 0.15, +0.6 por señal, score normalizado. v4: señales de transacción F1–F8 con otro significado, prevalencia 4 %, falso positivo 0.5, +0.5 por señal, suma de puntos. | Se usa la **v2 como modelo integrado**, porque comparte señales con el S2 y el S3. La v4 se conserva en una pestaña aparte, con sus supuestos tal cual y una advertencia de que no alimenta el flujo integrado. |
| C3 | El contexto describe una **v3** (matriz, Nash puro, dominancia, maximin, ε-Nash, línea base, 2×2), pero el notebook v3 **no está en la carpeta**. `Brecha Nequi.html` cita sus resultados (umbral 0.254, p\* ≈ 0.533, q\* ≈ 0.213). | Se ejecuta la v2 real. Nash puro y dominancia se toman de la v4, y se agregaron maximin y la comparación con una regla fija (pesos iguales y umbral 0.5, la misma línea base del S3). Los números de la v3 no se copian: la app solo muestra lo que calcula. |
| C4 | El **script Python de A\*** no está en la carpeta, solo el HTML del mapa. | Se reconstruyó A\* con los datos del HTML. El costo barrio→cliente se deriva como g(cliente) − g(barrio), y el costo A\* resultante coincide con el g de cada cliente en el mapa (verificado en las pruebas). El orden de entrega se modela como 1‖Σ wᵢCᵢ con pᵢ = tiempo A\* desde el hub. Si el original usaba otra definición de tiempo, se cambia en `trabajos()`. |
| C5 | El tronco Bogotá→hub solo se conoce como total (p. ej. «Bogotá → Ibagué → Medellín · 8.0 h»). | Se usa como un único tramo y la ciudad intermedia es solo una etiqueta. No se inventaron costos por tramo. |
| C6 | El HTML del mapa advierte que en Medellín el costo de Bello (0.90 h) es menor que el de Poblado (1.10 h), aunque en el mapa Bello está casi al doble de distancia. | Se conservan los costos del modelo (son supuestos didácticos) y la advertencia se muestra en la página del S1. |
| C7 | Una sola señal crítica (F4, F5 o F7) **no** dispara la alerta del score de la EE: el peso relativo más alto aprendido (25.9 %) no llega al umbral (0.2924). El sistema experto sí la rechaza. | No es un error de código: un score aditivo no puede expresar «esta señal sola basta». Por eso el SE sigue siendo la política que decide y la EE es una segunda opinión. Se documenta en Validación con la tabla de coherencia sobre las 512 combinaciones. |
| C8 | El código Python del SE dentro del HTML está truncado (se perdieron los `<` al exportar). | Se usó el espejo JavaScript del mismo archivo, que tiene las condiciones completas y los valores por defecto de `.get()`. |
| C9 | La numeración de sprints no está explícita en los archivos. | Se asumió: A\* = 1, sistema experto = 2, evolutivos + teoría de juegos = 3, lógica difusa = 4 (la que el enunciado llama Sprint 4). |

## 5. Integración del juego «Brecha Nequi» (última entrega)

**Qué es.** `Brecha Nequi.html` es un juego en canvas con cuatro misiones y un cuaderno de 12 conceptos, basado
en el notebook v3:
1. **El precio de cada poder** (ninja). Cada señal F2–F9 suma +0.6 al botín y peso al puntaje; F10 aparece en el
   40 % de los intentos.
2. **El umbral de Nequi** (Guardián). Se fija el umbral con ↑/↓ y se compara contra la curva de costo exacta.
3. **El Guardián aprende** (ninja). El Guardián evoluciona con (μ+λ) = (6+16) contra los últimos 4 ataques.
4. **Duelo simultáneo.** Matriz 2×2 en la que el rival responde a las últimas 8 jugadas; se compara con el
   equilibrio mixto.

**Cómo se integró.**
- El HTML se copió **sin cambios** en `assets/brecha_nequi.html` y se embebe con `st.iframe`, que ajusta la altura
  al contenido.
- La única adaptación se hace al servirlo (`core/juego_brecha.py::html_juego`): la misión inicial se lee de una
  variable en lugar de `location.hash`, que no existe dentro del iframe.
- El botón «Reiniciar juego» recrea el iframe con una partida nueva.

**Explicaciones.** Se portó a Python la lógica exacta del juego (`pExacto`, `costoExacto`, la mejor respuesta de la
misión 1 y la solución por indiferencia de la misión 4). Así los diagramas y gráficos de la página salen de cálculos
reales y no de valores escritos a mano. Las pruebas comprueban que dan lo mismo que el cuaderno del juego
(p\* ≈ 0.533, q\* ≈ 0.213).

**Contradicción C10.** El juego usa los parámetros del notebook **v3**: pesos del mejor defensor, umbral 0.254 y la
matriz 2×2 de su sección 12. Ese notebook no está en la carpeta, así que estas constantes se toman del HTML tal
cual. La página de Teoría de juegos calcula en vivo la v2 (p\* ≈ 0.559, q\* ≈ 0.214). Ambas versiones coinciden en
la dirección del equilibrio y la diferencia se indica en la página del juego.

## 6. Justificación técnica de la lógica difusa (Sprint 4)

**Problema.** El motor de crédito decide con fronteras rígidas: `score < 600` rechaza (C1), `cuota/ingresos > 0.35`
rechaza (C2) y `DTI > 0.70` rechaza (C4). Un score de 599 y uno de 600 reciben decisiones opuestas, y el sistema
no puede decir que un perfil está *cerca* de un umbral ni ofrecer un desenlace intermedio para el crédito
(la revisión manual existía solo para fraude).

**Alternativa elegida: inferencia Mamdani.**
- La explicabilidad regla por regla es un requisito del S2 (KYC/AML, XAI), y Mamdani lo conserva: antecedentes y
  consecuentes son etiquetas lingüísticas.
- La salida difusa tiene una etiqueta «medio» que se traduce de forma natural en «revisión manual».
- Es el método del notebook de clase, así que se reutilizan sus funciones (`trimf`, `trapmf`, centroide) y sus
  conjuntos de salida.
- Se descartó **Sugeno** (consecuentes funcionales: eficiente, pero menos legible para un analista) y
  **Tsukamoto** (exige consecuentes monótonos y pierde la etiqueta intermedia).

**Variables de entrada** (procedencia: diccionario de hechos del S2).

| Variable | Cálculo | Unidad | Universo | Conjuntos (trapezoidales) | Anclaje |
|---|---|---|---|---|---|
| Score | `score_datacredito` | puntos | 150–950 ¹ | bajo (150,150,550,650) · medio (550,650,700,800) · alto (700,800,950,950) | C1 = 600 y C8 = 750 son cruces μ = 0.5 |
| Carga de la cuota | `monto_cuota_solicitada / max(ingresos,1)` | proporción | 0–1 ² | holgada (0,0,.15,.25) · moderada (.15,.25,.30,.40) · excedida (.30,.40,1,1) | C9 = 0.20 y C2 = 0.35 |
| DTI | `deuda_total_mensual / max(ingresos,1)` | proporción | 0–1 ² | aceptable (0,0,.60,.80) · excesivo (.60,.80,1,1) | C4 = 0.70 |
| **Salida**: riesgo | — | 0–100 | 0–100 | bajo (0,0,20,40) · medio △(25,50,75) · alto (60,80,100,100) | notebook de clase |

¹ El S2 no fija un rango de score; se usa el rango de referencia de las centrales de riesgo en Colombia.
² Las razones mayores que 1 se saturan en 1 porque ya pertenecen por completo a «excedida»/«excesivo».

**Decisiones de modelado declaradas.** La única información que no viene de los archivos es el **semiancho de
la transición** alrededor de cada umbral: ±50 pts de score, ±0.05 de carga y ±0.10 de DTI. Se puede editar en la
página del S4, y la validación impide anchos que crucen conjuntos. Se usan trapecios porque cada categoría
tiene una meseta de pertenencia total y su frontera viene de un umbral de política. Se descartaron las gaussianas
porque nunca llegan a 0 y activarían todas las reglas, lo que dificulta la auditoría.

**Base de reglas** (Y = mínimo).

| Regla | Enunciado | Relación con el SE |
|---|---|---|
| R1 | SI score bajo → riesgo alto | C1 |
| R2 | SI carga excedida → riesgo alto | C2 |
| R3 | SI DTI excesivo → riesgo alto | C4 |
| R4 | SI score alto Y carga holgada Y DTI aceptable → riesgo bajo | C8 + C9 |
| R5 | SI score alto Y carga moderada Y DTI aceptable → riesgo bajo | C8 |
| R6 | SI score medio Y carga holgada Y DTI aceptable → riesgo bajo | C9 |
| R7 | SI score medio Y carga moderada Y DTI aceptable → riesgo medio | Aprobado por el SE sin ninguna regla favorable (zona gris) |

R1–R6 traducen reglas existentes. **R7 es la única regla de política nueva**: el perfil que el SE aprueba
sin ninguna señal favorable pasa a revisión manual. Si el equipo prefiere aprobarlo, basta con cambiar su
consecuente a «bajo». La cobertura se verifica: en todo el espacio, alguna regla se activa con grado ≥ 0.5.

**Inferencia, agregación y defuzzificación.** Implicación por recorte (mínimo), agregación por máximo y
centroide. El centroide se eligió porque usa toda la forma de la salida agregada: el puntaje refleja la fuerza
de todas las reglas activas y no solo la más fuerte, como haría el método de la media de máximos.

**Salida y acción.** Riesgo 0–100 y la etiqueta con mayor pertenencia en el centroide (en empate gana la más
riesgosa): bajo → APROBADO, medio → REVISIÓN MANUAL, alto → RECHAZO FINANCIERO.

**Interacción con las reglas existentes (no se sustituyen automáticamente).**
- El motor de fraude no cambia y va primero: AML, biometría o granja de dispositivos no admiten grados.
- C3 (mora), C5 (antigüedad), C6 (ingreso mínimo) y C7 (embargo) siguen siendo rígidas y bloqueantes.
- C1, C2 y C4 pasan a la capa difusa, y C8 y C9 fundamentan las reglas favorables.
- La decisión clásica del SE se muestra siempre junto a la integrada, para que se vea qué cambió y por qué.

**Validación.** `core/casos_prueba.py` (visible en la página Validación y ejecutado por `pytest`) comprueba:
el anclaje μ = 0.5 en cada umbral, las decisiones en casos claros y límite, la continuidad (599 frente a 601 cambian
menos de 2 puntos), la monotonía en score y carga, la cobertura de reglas, el rechazo de entradas inválidas
y el flujo integrado completo (cortocircuito, reglas rígidas, límites de mora 30/31 y de match facial 0.79/0.80).

**Extensión no implementada.** Calibrar los semianchos con la estrategia evolutiva del S3 (sistema genético-difuso).
No se implementó porque no hay un histórico etiquetado de crédito en el material, y simularlo sería inventar datos.

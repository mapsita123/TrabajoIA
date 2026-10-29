"""
Sprint 1 · Búsqueda informada (A*) — logística de tarjetas físicas.

Fuente disponible: "mapas-reales-ciudades (1).html". Ese archivo trae la red de
cada ciudad (aristas hub→barrio y barrio→barrio con su costo en horas), el
costo g de cada barrio y cliente desde el hub, la heurística por capas
(h = 0.45 en el hub, 0.15 en los barrios, 0 en los clientes), el tronco desde
Bogotá y el peso de cada cliente (Premium 3.0, Regular 1.0).

VACÍO DOCUMENTADO: el script Python original de A* no está en la carpeta.
- El costo barrio→cliente no aparece como arista; se deriva como g(cliente) − g(barrio).
- El tronco Bogotá→hub solo se conoce como total (8.0 / 7.0 / 11.5 h); la
  ciudad intermedia se muestra como etiqueta, no como nodo con costo propio.
- La secuenciación de entregas se reconstruye como el problema 1||Σ wᵢCᵢ con
  tiempo de proceso pᵢ = costo A* hub→cliente, que es el modelo en el que la
  regla de Smith (WSPT) es óptima. Si el original usaba otra definición de
  tiempo, basta con cambiar `tiempo_proceso`.
"""
from __future__ import annotations

import heapq
import itertools
import math
from dataclasses import dataclass

PESO_CLIENTE = {"Premium": 3.0, "Regular": 1.0}
H_HUB, H_BARRIO, H_CLIENTE = 0.45, 0.15, 0.0

CIUDADES = {
    "Medellín": {
        "tronco": ("Bogotá → Ibagué → Medellín", 8.0),
        "hub": (6.2518, -75.5636),
        "barrios": {"Laureles": (6.2447, -75.5916), "Bello": (6.3378, -75.5544), "Poblado": (6.2088, -75.5678)},
        "aristas": [("HUB", "Laureles", 0.4), ("HUB", "Bello", 0.9), ("HUB", "Poblado", 1.4),
                    ("Laureles", "Poblado", 0.7), ("Laureles", "Bello", 0.6), ("Bello", "Poblado", 1.1)],
        # cliente: (barrio, tipo, g desde el hub en el mapa, coordenadas)
        "clientes": {
            "MED_3": ("Laureles", "Regular", 0.55, (6.2412, -75.5960)),
            "MED_4": ("Laureles", "Regular", 0.70, (6.2478, -75.5972)),
            "MED_5": ("Bello", "Regular", 1.20, (6.3340, -75.5590)),
            "MED_6": ("Bello", "Premium", 1.40, (6.3425, -75.5502)),
            "MED_2": ("Poblado", "Premium", 1.50, (6.2065, -75.5720)),
            "MED_1": ("Poblado", "Premium", 2.50, (6.1985, -75.5640)),
        },
        "g_barrio": {"Laureles": 0.40, "Bello": 0.90, "Poblado": 1.10},
    },
    "Bucaramanga": {
        "tronco": ("Bogotá → Tunja → Bucaramanga", 7.0),
        "hub": (7.1254, -73.1198),
        "barrios": {"Cabecera": (7.1080, -73.1085), "Floridablanca": (7.0625, -73.0864), "Girón": (7.0703, -73.1697)},
        "aristas": [("HUB", "Cabecera", 0.3), ("HUB", "Floridablanca", 1.0), ("HUB", "Girón", 1.3),
                    ("Cabecera", "Floridablanca", 0.5), ("Floridablanca", "Girón", 0.6)],
        "clientes": {
            "BGA_1": ("Cabecera", "Regular", 0.50, (7.1050, -73.1120)),
            "BGA_2": ("Floridablanca", "Regular", 1.10, (7.0590, -73.0900)),
            "BGA_3": ("Girón", "Premium", 1.80, (7.0730, -73.1740)),
            "BGA_4": ("Girón", "Premium", 2.20, (7.0660, -73.1660)),
        },
        "g_barrio": {"Cabecera": 0.30, "Floridablanca": 0.80, "Girón": 1.30},
    },
    "Cartagena": {
        "tronco": ("Bogotá → Puerto Salgar → Cartagena", 11.5),
        "hub": (10.4100, -75.5300),
        "barrios": {"Getsemaní": (10.4200, -75.5450), "Bocagrande": (10.4000, -75.5560), "Turbaco": (10.3400, -75.4150)},
        "aristas": [("HUB", "Getsemaní", 0.3), ("HUB", "Bocagrande", 0.9), ("HUB", "Turbaco", 1.6),
                    ("Getsemaní", "Bocagrande", 0.4), ("Bocagrande", "Turbaco", 1.0)],
        "clientes": {
            "CTG_1": ("Getsemaní", "Regular", 0.50, (10.4225, -75.5480)),
            "CTG_2": ("Getsemaní", "Regular", 0.80, (10.4180, -75.5495)),
            "CTG_3": ("Bocagrande", "Premium", 1.10, (10.3960, -75.5590)),
            "CTG_5": ("Turbaco", "Premium", 2.10, (10.3440, -75.4200)),
            "CTG_4": ("Turbaco", "Premium", 2.60, (10.3355, -75.4090)),
        },
        "g_barrio": {"Getsemaní": 0.30, "Bocagrande": 0.70, "Turbaco": 1.60},
    },
}


# ------------------------------------------------------------------ grafo ---
def construir_grafo(ciudad: str) -> dict[str, dict[str, float]]:
    """Grafo no dirigido hub–barrios–clientes de una ciudad."""
    c = CIUDADES[ciudad]
    grafo: dict[str, dict[str, float]] = {"HUB": {}}
    for b in c["barrios"]:
        grafo.setdefault(b, {})
    for u, v, costo in c["aristas"]:
        grafo[u][v] = costo
        grafo[v][u] = costo
    for cliente, (barrio, _tipo, g, _ll) in c["clientes"].items():
        costo = round(g - c["g_barrio"][barrio], 4)  # derivado (ver docstring)
        grafo[barrio][cliente] = costo
        grafo.setdefault(cliente, {})[barrio] = costo
    return grafo


def heuristica(nodo: str, ciudad: str) -> float:
    """Heurística admisible por capas: mínimo costo conocido de cada nivel de la red."""
    if nodo == "HUB":
        return H_HUB
    if nodo in CIUDADES[ciudad]["barrios"]:
        return H_BARRIO
    return H_CLIENTE


def verificar_admisibilidad(ciudad: str) -> list[dict]:
    """Compara h(n) con el costo real óptimo h*(n) hasta el cliente más cercano."""
    grafo = construir_grafo(ciudad)
    clientes = list(CIUDADES[ciudad]["clientes"])
    filas = []
    for nodo in grafo:
        h_real = min(dijkstra(grafo, nodo).get(c, math.inf) for c in clientes)
        filas.append({"nodo": nodo, "h": heuristica(nodo, ciudad), "h*": round(h_real, 4),
                      "admisible": heuristica(nodo, ciudad) <= h_real + 1e-9})
    return filas


def dijkstra(grafo, origen):
    dist = {origen: 0.0}
    cola = [(0.0, origen)]
    while cola:
        d, u = heapq.heappop(cola)
        if d > dist.get(u, math.inf):
            continue
        for v, w in grafo[u].items():
            if d + w < dist.get(v, math.inf):
                dist[v] = d + w
                heapq.heappush(cola, (d + w, v))
    return dist


@dataclass
class ResultadoAEstrella:
    camino: list[str]
    costo: float
    expandidos: list[str]
    traza: list[dict]


def a_estrella(ciudad: str, destino: str, origen: str = "HUB") -> ResultadoAEstrella:
    """A* clásico con lista abierta (heap) y conjunto cerrado."""
    grafo = construir_grafo(ciudad)
    if destino not in grafo:
        raise ValueError(f"El destino {destino} no existe en la red de {ciudad}.")
    contador = itertools.count()
    abiertos = [(heuristica(origen, ciudad), next(contador), origen)]
    g = {origen: 0.0}
    padre: dict[str, str | None] = {origen: None}
    cerrados: set[str] = set()
    expandidos, traza = [], []
    while abiertos:
        f, _, nodo = heapq.heappop(abiertos)
        if nodo in cerrados:
            continue
        cerrados.add(nodo)
        expandidos.append(nodo)
        traza.append({"paso": len(expandidos), "nodo": nodo, "g": round(g[nodo], 3),
                      "h": heuristica(nodo, ciudad), "f": round(f, 3)})
        if nodo == destino:
            camino = []
            while nodo is not None:
                camino.append(nodo)
                nodo = padre[nodo]
            return ResultadoAEstrella(camino[::-1], g[destino], expandidos, traza)
        for vecino, costo in grafo[nodo].items():
            nuevo_g = g[nodo] + costo
            if nuevo_g < g.get(vecino, math.inf) - 1e-12:
                g[vecino] = nuevo_g
                padre[vecino] = nodo
                heapq.heappush(abiertos, (nuevo_g + heuristica(vecino, ciudad), next(contador), vecino))
    raise ValueError("No existe ruta.")


def rutas_desde_bogota(ciudad: str) -> list[dict]:
    """Ruta completa de cada cliente: tronco desde Bogotá + tramo local óptimo (A*)."""
    c = CIUDADES[ciudad]
    nombre_tronco, horas_tronco = c["tronco"]
    filas = []
    for cliente, (_barrio, tipo, g_mapa, _ll) in c["clientes"].items():
        r = a_estrella(ciudad, cliente)
        filas.append({"cliente": cliente, "tipo": tipo, "peso": PESO_CLIENTE[tipo],
                      "ruta_local": " → ".join(r.camino), "horas_local": round(r.costo, 2),
                      "g_mapa": g_mapa, "horas_total": round(horas_tronco + r.costo, 2),
                      "nodos_expandidos": len(r.expandidos)})
    return filas


# --------------------------------------------- políticas de entrega (WSPT) ---
def trabajos(ciudad: str) -> list[dict]:
    """Cada cliente es un trabajo con peso wᵢ y tiempo pᵢ = costo A* hub→cliente."""
    return [{"cliente": f["cliente"], "tipo": f["tipo"], "w": f["peso"], "p": f["horas_local"]}
            for f in rutas_desde_bogota(ciudad)]


def costo_ponderado(secuencia: list[dict]) -> float:
    """Σ wᵢ·Cᵢ, con Cᵢ = tiempo acumulado al terminar la entrega i."""
    t, total = 0.0, 0.0
    for j in secuencia:
        t += j["p"]
        total += j["w"] * t
    return total


POLITICAS = {
    "Rapidez (más cercano primero)": lambda js: sorted(js, key=lambda j: (j["p"], j["cliente"])),
    "Premium estricto": lambda js: sorted(js, key=lambda j: (-j["w"], j["p"], j["cliente"])),
    "Ponderada (regla de Smith, WSPT)": lambda js: sorted(js, key=lambda j: (-j["w"] / j["p"], j["cliente"])),
}


def comparar_politicas(ciudad: str) -> list[dict]:
    js = trabajos(ciudad)
    filas = []
    for nombre, regla in POLITICAS.items():
        sec = regla(js)
        filas.append({"politica": nombre, "secuencia": " → ".join(j["cliente"] for j in sec),
                      "costo": round(costo_ponderado(sec), 4)})
    return filas


def a_estrella_secuencia(js: list[dict]) -> dict:
    """
    A* sobre el espacio de permutaciones (estado = clientes ya entregados).
    g = Σ wᵢCᵢ acumulado; h = Σ_{j pendiente} wⱼ·(T + pⱼ), cota inferior
    admisible porque cada pendiente termina como pronto en T + pⱼ.
    """
    n = len(js)
    contador = itertools.count()
    inicio = (0.0, 0.0, (), next(contador))
    abiertos = [(sum(j["w"] * j["p"] for j in js), inicio)]
    mejor_g: dict[frozenset, float] = {}
    expandidos = 0
    while abiertos:
        _f, (g, T, sec, _) = heapq.heappop(abiertos)
        if len(sec) == n:
            return {"secuencia": [js[i]["cliente"] for i in sec], "costo": round(g, 4), "expandidos": expandidos}
        clave = frozenset(sec)
        if mejor_g.get(clave, math.inf) < g - 1e-12:
            continue
        expandidos += 1
        for i in range(n):
            if i in sec:
                continue
            T2 = T + js[i]["p"]
            g2 = g + js[i]["w"] * T2
            sec2 = sec + (i,)
            c2 = frozenset(sec2)
            if g2 < mejor_g.get(c2, math.inf) - 1e-12:
                mejor_g[c2] = g2
                h = sum(js[k]["w"] * (T2 + js[k]["p"]) for k in range(n) if k not in sec2)
                heapq.heappush(abiertos, (g2 + h, (g2, T2, sec2, next(contador))))
    raise RuntimeError("Sin solución")


def fuerza_bruta(js: list[dict]) -> dict:
    mejor = min(itertools.permutations(js), key=costo_ponderado)
    return {"secuencia": [j["cliente"] for j in mejor], "costo": round(costo_ponderado(list(mejor)), 4),
            "permutaciones": math.factorial(len(js))}

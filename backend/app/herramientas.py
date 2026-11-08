from decimal import Decimal

import httpx

from app.db import get_cursor

HTTP_TIMEOUT = 8.0
USER_AGENT = "AsistenteVideojuegosUMES/1.0 (proyecto academico)"


# ---------- utilidades ----------
def _num(valor):
    return float(valor) if isinstance(valor, Decimal) else valor


def _juego_json(fila: dict) -> dict:
    return {
        "id": fila["id"],
        "titulo": fila["titulo"],
        "genero": fila["genero"],
        "plataforma": fila["plataforma"],
        "precio": _num(fila["precio"]),
        "stock": fila["stock"],
    }


def _agregar_fuente(ctx: dict, fuente: dict) -> None:
    if fuente not in ctx["fuentes"]:
        ctx["fuentes"].append(fuente)


def generos_catalogo() -> list:
    with get_cursor() as cur:
        cur.execute("SELECT DISTINCT genero FROM videojuegos ORDER BY genero")
        return [f["genero"] for f in cur.fetchall()]


# ---------- herramientas del catálogo (base de datos) ----------
def buscar_juego(ctx, titulo: str):
    titulo = (titulo or "").strip()
    if not titulo:
        return {"error": "Debes indicar un título o palabra clave"}
    with get_cursor() as cur:
        cur.execute(
            """SELECT id, titulo, genero, plataforma, precio, stock
               FROM videojuegos WHERE titulo ILIKE %s ORDER BY titulo LIMIT 5""",
            (f"%{titulo}%",),
        )
        filas = cur.fetchall()
    for f in filas:
        _agregar_fuente(ctx, {"tipo": "catalogo", "id": f["id"], "titulo": f["titulo"]})
    return {
        "busqueda": titulo,
        "cantidad": len(filas),
        "encontrados": [_juego_json(f) for f in filas],
    }


def obtener_resenas(ctx, juego_id: int):
    try:
        juego_id = int(juego_id)
    except (TypeError, ValueError):
        return {"error": "juego_id debe ser un número entero"}
    with get_cursor() as cur:
        cur.execute("SELECT titulo FROM videojuegos WHERE id = %s", (juego_id,))
        juego = cur.fetchone()
        if not juego:
            return {"error": "No existe un videojuego con ese id"}
        cur.execute(
            """SELECT ROUND(AVG(puntuacion)::numeric, 1) AS promedio, COUNT(*) AS total
               FROM resenas WHERE videojuego_id = %s""",
            (juego_id,),
        )
        resumen = cur.fetchone()
        cur.execute(
            "SELECT autor, puntuacion, comentario FROM resenas WHERE videojuego_id = %s ORDER BY id LIMIT 3",
            (juego_id,),
        )
        comentarios = cur.fetchall()
    return {
        "id": juego_id,
        "titulo": juego["titulo"],
        "promedio": _num(resumen["promedio"]),
        "total_resenas": resumen["total"],
        "comentarios": comentarios,
    }


def calcular_total(ctx, ids: list):
    """Suma los precios reales de la base de datos (una unidad de cada juego)."""
    try:
        ids = sorted({int(i) for i in ids})
    except (TypeError, ValueError):
        return {"error": "ids debe ser una lista de números enteros"}
    if not ids:
        return {"error": "La lista de ids está vacía"}
    with get_cursor() as cur:
        cur.execute(
            """SELECT id, titulo, genero, plataforma, precio, stock
               FROM videojuegos WHERE id = ANY(%s) ORDER BY id""",
            (ids,),
        )
        filas = cur.fetchall()
    for f in filas:
        _agregar_fuente(ctx, {"tipo": "catalogo", "id": f["id"], "titulo": f["titulo"]})
    encontrados = {f["id"] for f in filas}
    total = sum((f["precio"] for f in filas), Decimal("0"))
    return {
        "juegos": [_juego_json(f) for f in filas],
        "total": float(round(total, 2)),
        "sin_stock": [f["titulo"] for f in filas if f["stock"] <= 0],
        "ids_no_encontrados": [i for i in ids if i not in encontrados],
    }


def comparar_con_presupuesto(ctx, total: float, presupuesto: float):
    try:
        total = float(total)
        presupuesto = float(presupuesto)
    except (TypeError, ValueError):
        return {"error": "total y presupuesto deben ser números"}
    diferencia = round(presupuesto - total, 2)
    return {
        "total": round(total, 2),
        "presupuesto": round(presupuesto, 2),
        "alcanza": diferencia >= 0,
        "diferencia": diferencia,  # positivo = sobra; negativo = falta
        "porcentaje_usado": round(total / presupuesto * 100, 1) if presupuesto > 0 else None,
    }


def buscar_alternativas_catalogo(ctx, genero=None, plataforma=None, precio_max=None, excluir_ids=None):
    condiciones = ["v.stock > 0"]
    valores = []
    if genero:
        condiciones.append("v.genero ILIKE %s")
        valores.append(f"%{genero}%")
    if plataforma:
        condiciones.append("(v.plataforma ILIKE %s OR v.plataforma = 'Multiplataforma')")
        valores.append(f"%{plataforma}%")
    if precio_max is not None:
        try:
            valores.append(float(precio_max))
        except (TypeError, ValueError):
            return {"error": "precio_max debe ser un número"}
        condiciones.append("v.precio <= %s")
    if excluir_ids:
        try:
            ids = [int(i) for i in excluir_ids]
        except (TypeError, ValueError):
            return {"error": "excluir_ids debe ser una lista de enteros"}
        condiciones.append("v.id <> ALL(%s)")
        valores.append(ids)
    sql = f"""SELECT v.id, v.titulo, v.genero, v.plataforma, v.precio, v.stock,
                     ROUND(AVG(r.puntuacion)::numeric, 1) AS promedio,
                     COUNT(r.id) AS total_resenas
              FROM videojuegos v
              LEFT JOIN resenas r ON r.videojuego_id = v.id
              WHERE {' AND '.join(condiciones)}
              GROUP BY v.id
              ORDER BY promedio DESC NULLS LAST, v.precio ASC
              LIMIT 6"""
    with get_cursor() as cur:
        cur.execute(sql, valores)
        filas = cur.fetchall()
    for f in filas:
        _agregar_fuente(ctx, {"tipo": "catalogo", "id": f["id"], "titulo": f["titulo"]})
    return {
        "cantidad": len(filas),
        "alternativas": [
            {**_juego_json(f), "promedio": _num(f["promedio"]), "total_resenas": f["total_resenas"]}
            for f in filas
        ],
    }


# ---------- herramientas externas (APIs públicas sin clave) ----------
def consultar_ofertas_externas(ctx, titulo: str):
    """Precios mínimos en tiendas de PC según CheapShark (referencia externa)."""
    try:
        r = httpx.get(
            "https://www.cheapshark.com/api/1.0/games",
            params={"title": titulo, "limit": 3},
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        datos = r.json()
    except Exception as e:
        return {"disponible": False, "mensaje": f"No se pudo consultar CheapShark: {e}"}
    resultados = []
    for d in datos:
        try:
            precio = float(d.get("cheapest"))
        except (TypeError, ValueError):
            precio = None
        resultados.append({"nombre": d.get("external"), "precio_minimo_usd": precio})
        _agregar_fuente(ctx, {"tipo": "externa", "fuente": "CheapShark", "detalle": d.get("external")})
    return {"disponible": True, "fuente": "CheapShark (tiendas de PC)", "resultados": resultados}


def buscar_en_wikipedia(ctx, consulta: str):
    """Resumen breve de un videojuego en Wikipedia (referencia externa)."""
    try:
        r = httpx.get(
            "https://es.wikipedia.org/w/api.php",
            params={
                "action": "query", "format": "json",
                "generator": "search", "gsrsearch": f"{consulta} videojuego", "gsrlimit": 1,
                "prop": "extracts", "exintro": 1, "explaintext": 1, "exchars": 600,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        paginas = (r.json().get("query") or {}).get("pages") or {}
    except Exception as e:
        return {"disponible": False, "mensaje": f"No se pudo consultar Wikipedia: {e}"}
    if not paginas:
        return {"disponible": True, "resultados": [], "mensaje": "Wikipedia no devolvió resultados"}
    pagina = next(iter(paginas.values()))
    _agregar_fuente(ctx, {"tipo": "externa", "fuente": "Wikipedia", "detalle": pagina.get("title")})
    return {
        "disponible": True,
        "fuente": "Wikipedia",
        "titulo": pagina.get("title"),
        "resumen": pagina.get("extract"),
    }


# ---------- registro de herramientas (lo que ve el modelo) ----------
def _tool(nombre: str, descripcion: str, propiedades: dict, requeridos: list) -> dict:
    return {
        "type": "function",
        "function": {
            "name": nombre,
            "description": descripcion,
            "parameters": {"type": "object", "properties": propiedades, "required": requeridos},
        },
    }


HERRAMIENTAS = {
    "buscar_juego": {
        "funcion": buscar_juego,
        "schema": _tool(
            "buscar_juego",
            "Busca videojuegos del catálogo por palabra clave del título. Devuelve id, precio y stock.",
            {"titulo": {"type": "string", "description": "Palabra clave del título, ej: 'Zelda'"}},
            ["titulo"],
        ),
    },
    "obtener_resenas": {
        "funcion": obtener_resenas,
        "schema": _tool(
            "obtener_resenas",
            "Devuelve la valoración promedio y algunos comentarios de un videojuego del catálogo.",
            {"juego_id": {"type": "integer", "description": "Id del videojuego"}},
            ["juego_id"],
        ),
    },
    "calcular_total": {
        "funcion": calcular_total,
        "schema": _tool(
            "calcular_total",
            "Suma los precios reales de una lista de videojuegos (una unidad de cada uno).",
            {"ids": {"type": "array", "items": {"type": "integer"}, "description": "Ids de los juegos"}},
            ["ids"],
        ),
    },
    "comparar_con_presupuesto": {
        "funcion": comparar_con_presupuesto,
        "schema": _tool(
            "comparar_con_presupuesto",
            "Compara un total con el presupuesto del usuario y dice si alcanza y cuánto sobra o falta.",
            {
                "total": {"type": "number", "description": "Total calculado en USD"},
                "presupuesto": {"type": "number", "description": "Presupuesto del usuario en USD"},
            },
            ["total", "presupuesto"],
        ),
    },
    "buscar_alternativas_catalogo": {
        "funcion": buscar_alternativas_catalogo,
        "schema": _tool(
            "buscar_alternativas_catalogo",
            "Busca juegos disponibles (con stock) del catálogo filtrando por género, plataforma y precio máximo. "
            "Ordena por mejor valoración.",
            {
                "genero": {"type": "string", "description": "Género exacto del catálogo"},
                "plataforma": {"type": "string", "description": "Plataforma, ej: 'PC' o 'Nintendo Switch'"},
                "precio_max": {"type": "number", "description": "Precio máximo en USD"},
                "excluir_ids": {"type": "array", "items": {"type": "integer"},
                                "description": "Ids de juegos a excluir"},
            },
            [],
        ),
    },
    "consultar_ofertas_externas": {
        "funcion": consultar_ofertas_externas,
        "schema": _tool(
            "consultar_ofertas_externas",
            "Consulta precios mínimos de un juego en tiendas de PC (CheapShark, fuente externa).",
            {"titulo": {"type": "string", "description": "Título del juego en inglés o español"}},
            ["titulo"],
        ),
    },
    "buscar_en_wikipedia": {
        "funcion": buscar_en_wikipedia,
        "schema": _tool(
            "buscar_en_wikipedia",
            "Obtiene un resumen breve de un videojuego en Wikipedia (fuente externa).",
            {"consulta": {"type": "string", "description": "Nombre del juego"}},
            ["consulta"],
        ),
    },
}
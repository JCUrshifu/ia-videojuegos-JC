import re

from app.db import get_cursor


def _consulta_or(texto: str) -> str:
    """Convierte la pregunta en palabras unidas por OR para to_tsquery."""
    palabras = re.findall(r"[^\W_]{3,}", texto.lower())
    unicas = list(dict.fromkeys(palabras))[:12]
    return " | ".join(unicas)


def recuperar_juegos(texto: str, limite: int = 5) -> list:
    """Busca los videojuegos más relacionados con el texto (búsqueda de texto en PostgreSQL)."""
    consulta = _consulta_or(texto)
    if not consulta:
        return []
    with get_cursor() as cur:
        cur.execute(
            """SELECT v.id, v.titulo, v.genero, v.plataforma, v.precio, v.stock, v.anio, v.descripcion,
                      ts_rank(v.busqueda, to_tsquery('spanish', %s)) AS relevancia
               FROM videojuegos v
               WHERE v.busqueda @@ to_tsquery('spanish', %s)
               ORDER BY relevancia DESC, v.titulo
               LIMIT %s""",
            (consulta, consulta, limite),
        )
        juegos = cur.fetchall()
        resenas = {}
        if juegos:
            cur.execute(
                """SELECT videojuego_id,
                          ROUND(AVG(puntuacion)::numeric, 1) AS promedio,
                          COUNT(*) AS total,
                          (array_agg(comentario ORDER BY id))[1:2] AS comentarios
                   FROM resenas
                   WHERE videojuego_id = ANY(%s)
                   GROUP BY videojuego_id""",
                ([j["id"] for j in juegos],),
            )
            resenas = {r["videojuego_id"]: r for r in cur.fetchall()}
    for j in juegos:
        r = resenas.get(j["id"])
        j["promedio"] = float(r["promedio"]) if r else None
        j["total_resenas"] = r["total"] if r else 0
        j["comentarios"] = r["comentarios"] if r else []
    return juegos


def resumen_catalogo() -> str:
    """Datos generales del catálogo, para preguntas como '¿cuántos juegos hay?'."""
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total, MIN(precio) AS minimo, MAX(precio) AS maximo FROM videojuegos")
        r = cur.fetchone()
        cur.execute("SELECT DISTINCT genero FROM videojuegos ORDER BY genero")
        generos = [f["genero"] for f in cur.fetchall()]
    return (f"RESUMEN DEL CATÁLOGO: {r['total']} videojuegos. Géneros: {', '.join(generos)}. "
            f"Precios entre ${r['minimo']} y ${r['maximo']} (USD).")


def construir_contexto(juegos: list) -> str:
    partes = [resumen_catalogo()]
    if not juegos:
        partes.append("No se encontraron videojuegos relacionados con la pregunta.")
    for j in juegos:
        texto = (f"[ID {j['id']}] {j['titulo']} | Género: {j['genero']} | Plataforma: {j['plataforma']} | "
                 f"Precio: ${j['precio']} | Stock: {j['stock']} | Año: {j['anio']}\n"
                 f"Descripción: {j['descripcion']}")
        if j["promedio"] is not None:
            texto += f"\nReseñas: promedio {j['promedio']}/5 ({j['total_resenas']} reseñas)."
            for c in j["comentarios"]:
                texto += f' Comentario: "{c}".'
        partes.append(texto)
    return "\n\n".join(partes)
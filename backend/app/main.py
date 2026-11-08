from fastapi import FastAPI, HTTPException

from app.db import get_cursor

app = FastAPI(
    title="Asistente de Videojuegos con IA",
    description="API REST con chatbot RAG y agentes de IA.",
    version="0.1.0",
)


@app.get("/salud", tags=["Sistema"])
def salud():
    """Comprueba que la API y la base de datos funcionan."""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM videojuegos")
            juegos = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM servicios")
            servicios = cur.fetchone()["total"]
        return {"estado": "ok", "videojuegos": juegos, "servicios": servicios}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
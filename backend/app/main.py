from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.db import get_cursor
from app.routers import auth, catalogo, historial, ia, reportes, servicios, usuarios

INDEX = Path(__file__).parent / "static" / "index.html"

app = FastAPI(
    title="Asistente de Videojuegos con IA",
    description="API REST con chatbot RAG y agentes de IA.",
    version="0.5.0",
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(servicios.router)
app.include_router(catalogo.videojuegos)
app.include_router(catalogo.resenas)
app.include_router(ia.router)
app.include_router(historial.historial)
app.include_router(historial.consumo)
app.include_router(reportes.router)


@app.get("/", include_in_schema=False)
def inicio():
    """Interfaz web de la aplicación."""
    return FileResponse(INDEX)


@app.get("/health", include_in_schema=False)
def health():
    """Comprobación ligera para el hosting (no consulta la base de datos)."""
    return {"estado": "ok"}


@app.get("/salud", tags=["Sistema"])
def salud():
    """Comprueba que la API y la base de datos funcionan."""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM videojuegos")
            juegos = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM servicios")
            servicios_total = cur.fetchone()["total"]
        return {"estado": "ok", "videojuegos": juegos, "servicios": servicios_total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {e}")
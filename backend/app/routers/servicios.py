from fastapi import APIRouter, Depends

from app.crud import actualizar_fila
from app.db import get_cursor
from app.deps import solo_admin, usuario_actual
from app.schemas import ServicioActualizar

router = APIRouter(prefix="/servicios", tags=["Servicios de IA"])

COLUMNAS = "id, codigo, nombre, descripcion, activo"
PERMITIDAS = {"nombre", "descripcion", "activo"}


@router.get("")
def listar(usuario: dict = Depends(usuario_actual)):
    """El usuario ve solo los servicios activos; el admin ve todos."""
    with get_cursor() as cur:
        if usuario["rol"] == "admin":
            cur.execute(f"SELECT {COLUMNAS} FROM servicios ORDER BY id")
        else:
            cur.execute(f"SELECT {COLUMNAS} FROM servicios WHERE activo ORDER BY id")
        return cur.fetchall()


@router.put("/{servicio_id}")
def actualizar(servicio_id: int, datos: ServicioActualizar, admin: dict = Depends(solo_admin)):
    """Activa o desactiva un servicio y edita su nombre o descripción (solo admin)."""
    campos = datos.model_dump(exclude_unset=True)
    return actualizar_fila("servicios", servicio_id, campos, PERMITIDAS, COLUMNAS)
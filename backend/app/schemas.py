from typing import Literal, Optional

from pydantic import BaseModel, Field

EMAIL_PATRON = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
Rol = Literal["admin", "usuario"]


class UsuarioCrear(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=150, pattern=EMAIL_PATRON)
    password: str = Field(min_length=6, max_length=72)
    rol: Rol = "usuario"
    limite_tokens: int = Field(default=20000, ge=0)


class UsuarioActualizar(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    email: Optional[str] = Field(default=None, max_length=150, pattern=EMAIL_PATRON)
    password: Optional[str] = Field(default=None, min_length=6, max_length=72)
    rol: Optional[Rol] = None
    activo: Optional[bool] = None
    limite_tokens: Optional[int] = Field(default=None, ge=0)


class ServicioActualizar(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=100)
    descripcion: Optional[str] = None
    activo: Optional[bool] = None


class VideojuegoCrear(BaseModel):
    titulo: str = Field(min_length=1, max_length=150)
    genero: str = Field(min_length=1, max_length=40)
    plataforma: str = Field(min_length=1, max_length=40)
    precio: float = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    anio: Optional[int] = None
    descripcion: Optional[str] = None


class VideojuegoActualizar(BaseModel):
    titulo: Optional[str] = Field(default=None, min_length=1, max_length=150)
    genero: Optional[str] = Field(default=None, min_length=1, max_length=40)
    plataforma: Optional[str] = Field(default=None, min_length=1, max_length=40)
    precio: Optional[float] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    anio: Optional[int] = None
    descripcion: Optional[str] = None


class ResenaCrear(BaseModel):
    videojuego_id: int
    autor: str = Field(min_length=1, max_length=80)
    puntuacion: int = Field(ge=1, le=5)
    comentario: Optional[str] = None


class ResenaActualizar(BaseModel):
    autor: Optional[str] = Field(default=None, min_length=1, max_length=80)
    puntuacion: Optional[int] = Field(default=None, ge=1, le=5)
    comentario: Optional[str] = None
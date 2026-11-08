from fastapi import APIRouter, Depends

from app import agentes, chatbot
from app.deps import usuario_actual
from app.schemas import AgentePeticion, ChatPregunta

router = APIRouter(prefix="/ia")


@router.post("/chatbot", tags=["Chatbot RAG"])
def preguntar(datos: ChatPregunta, usuario: dict = Depends(usuario_actual)):
    """Pregunta al chatbot. Para continuar una conversación, envía su `conversacion_id`."""
    return chatbot.responder(usuario, datos.pregunta, datos.conversacion_id)


@router.post("/agente-presupuesto", tags=["Agentes de IA"])
def agente_presupuesto(datos: AgentePeticion, usuario: dict = Depends(usuario_actual)):
    """Agente analizador de presupuesto: busca los juegos, calcula el total y lo compara."""
    return agentes.ejecutar_servicio(usuario, "agente_presupuesto", datos.solicitud)


@router.post("/agente-alternativas", tags=["Agentes de IA"])
def agente_alternativas(datos: AgentePeticion, usuario: dict = Depends(usuario_actual)):
    """Agente de alternativas: busca opciones más económicas y consulta fuentes externas."""
    return agentes.ejecutar_servicio(usuario, "agente_alternativas", datos.solicitud)
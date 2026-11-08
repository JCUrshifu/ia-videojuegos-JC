from fastapi import APIRouter, Depends

from app import chatbot
from app.deps import usuario_actual
from app.schemas import ChatPregunta

router = APIRouter(prefix="/ia", tags=["Chatbot RAG"])


@router.post("/chatbot")
def preguntar(datos: ChatPregunta, usuario: dict = Depends(usuario_actual)):
    """Pregunta al chatbot. Para continuar una conversación, envía su `conversacion_id`."""
    return chatbot.responder(usuario, datos.pregunta, datos.conversacion_id)
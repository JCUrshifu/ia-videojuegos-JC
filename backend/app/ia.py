from fastapi import HTTPException
from groq import Groq
from app.config import GROQ_API_KEY, GROQ_MODEL

_cliente = None

def _obtener_cliente() -> Groq:
    global _cliente
    if _cliente is None:
        if not GROQ_API_KEY:
            raise HTTPException(status_code=500, detail="Falta GROQ_API_KEY en el archivo .env")
        _cliente = Groq(api_key=GROQ_API_KEY)
    return _cliente

def llamar_modelo(mensajes: list, tools: list | None = None, temperature: float = 0.2):
    """Llama a Groq. Devuelve (mensaje, tokens_entrada, tokens_salida)."""
    modelo_a_usar = GROQ_MODEL if GROQ_MODEL else "openai/gpt-oss-120b"
    parametros = {"model": modelo_a_usar, "messages": mensajes, "temperature": temperature}
    if tools:
        parametros["tools"] = tools
        parametros["tool_choice"] = "auto"
    try:
        respuesta = _obtener_cliente().chat.completions.create(**parametros)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error al consultar el proveedor de IA: {e}")
    uso = respuesta.usage
    entrada = getattr(uso, "prompt_tokens", 0) or 0
    salida = getattr(uso, "completion_tokens", 0) or 0
    return respuesta.choices[0].message, entrada, salida
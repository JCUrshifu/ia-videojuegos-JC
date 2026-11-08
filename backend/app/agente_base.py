import json
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.herramientas import HERRAMIENTAS

MAX_PASOS = 6
_cliente = None


def _obtener_cliente() -> Groq:
    global _cliente
    if _cliente is None:
        if not GROQ_API_KEY:
            raise HTTPException(status_code=500, detail="Falta GROQ_API_KEY en el archivo .env")
        _cliente = Groq(api_key=GROQ_API_KEY)
    return _cliente


def llamar_modelo_tools(mensajes: list, tools: list | None = None):
    """Llama a Groq (con herramientas si se envían). Devuelve (mensaje, tokens_entrada, tokens_salida)."""
    parametros = {"model": GROQ_MODEL, "messages": mensajes, "temperature": 0.2}
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


def _json_default(valor):
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, datetime):
        return valor.isoformat()
    return str(valor)


def _ejecutar_herramienta(nombre: str, argumentos_json: str, permitidas: list, ctx: dict):
    if nombre not in permitidas:
        return {"error": f"Herramienta no disponible: {nombre}"}, {}
    try:
        argumentos = json.loads(argumentos_json) if argumentos_json else {}
    except json.JSONDecodeError:
        return {"error": "Los argumentos no son un JSON válido"}, {}
    try:
        return HERRAMIENTAS[nombre]["funcion"](ctx, **argumentos), argumentos
    except TypeError as e:
        return {"error": f"Argumentos incorrectos: {e}"}, argumentos
    except Exception as e:
        return {"error": f"Falló la herramienta: {e}"}, argumentos


def ejecutar_agente(system_prompt: str, solicitud: str, herramientas: list, tokens_restantes: int) -> dict:
    """Bucle del agente: el modelo elige herramientas hasta poder responder (máx. MAX_PASOS)."""
    esquemas = [HERRAMIENTAS[n]["schema"] for n in herramientas]
    ctx = {"fuentes": []}
    mensajes = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": solicitud},
    ]
    pasos = []
    t_entrada = t_salida = 0
    respuesta = None
    excedido = False

    for _ in range(MAX_PASOS):
        mensaje, ti, to = llamar_modelo_tools(mensajes, esquemas)
        t_entrada += ti
        t_salida += to

        if not mensaje.tool_calls:
            respuesta = (mensaje.content or "").strip()
            break

        llamada = {"role": "assistant", "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}}
            for tc in mensaje.tool_calls
        ]}
        if mensaje.content:
            llamada["content"] = mensaje.content
        mensajes.append(llamada)

        for tc in mensaje.tool_calls:
            resultado, argumentos = _ejecutar_herramienta(
                tc.function.name, tc.function.arguments, herramientas, ctx
            )
            pasos.append({
                "paso": len(pasos) + 1,
                "herramienta": tc.function.name,
                "argumentos": argumentos,
                "resultado": resultado,
            })
            mensajes.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(resultado, ensure_ascii=False, default=_json_default),
            })

        if t_entrada + t_salida >= tokens_restantes:
            excedido = True
            break

    if not respuesta:
        if excedido:
            respuesta = ("Se alcanzó tu límite de tokens antes de terminar el análisis. "
                         "Pide al administrador que lo amplíe.")
        else:
            mensajes.append({
                "role": "user",
                "content": "Con la información reunida hasta ahora, redacta la respuesta final "
                           "para el usuario. No uses más herramientas.",
            })
            mensaje, ti, to = llamar_modelo_tools(mensajes, None)
            t_entrada += ti
            t_salida += to
            respuesta = (mensaje.content or "").strip() or "No pude generar una respuesta. Intenta de nuevo."

    return {
        "respuesta": respuesta,
        "pasos": pasos,
        "fuentes": ctx["fuentes"],
        "t_entrada": t_entrada,
        "t_salida": t_salida,
    }
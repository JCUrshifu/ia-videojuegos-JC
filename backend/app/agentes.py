from app import agente_base, chatbot, tokens
from app.herramientas import generos_catalogo

PROMPT_PRESUPUESTO = """Eres un agente analizador de presupuesto de una tienda de videojuegos. Respondes siempre en español.
El usuario te dice qué videojuegos quiere comprar y cuánto dinero tiene (en dólares, USD).
Sigue estos pasos usando las herramientas, sin saltarte ninguno:
1. Para cada juego que pida el usuario, llama a buscar_juego con una palabra clave distintiva del título
   (por ejemplo 'Zelda'). Si no hay resultados, prueba una vez con una palabra más corta; si sigue sin
   aparecer, indica que ese juego no está en el catálogo.
2. Con los ids encontrados, llama a calcular_total (una unidad de cada juego). NUNCA sumes ni restes por tu cuenta.
3. Llama a comparar_con_presupuesto con el total y el presupuesto del usuario.
4. Si algún juego no tiene stock, avísalo.
5. Si el usuario no indicó presupuesto, no lo inventes: calcula el total y pide el presupuesto.
Respuesta final (máximo 150 palabras): lista de juegos con su precio y [ID n], el total, el presupuesto,
si ALCANZA o NO ALCANZA y cuánto sobra o falta. Si no alcanza, sugiere pedir alternativas al agente de alternativas.
Usa solo los datos que devolvieron las herramientas."""


def _prompt_alternativas() -> str:
    generos = ", ".join(generos_catalogo())
    return f"""Eres un agente de recomendación de alternativas de una tienda de videojuegos. Respondes siempre en español.
El usuario quiere opciones más económicas o parecidas, normalmente porque su presupuesto no alcanza. Precios en USD.
Géneros del catálogo: {generos}. La plataforma 'Multiplataforma' sirve para cualquier plataforma.
Sigue estos pasos con las herramientas:
1. Si el usuario menciona un juego de referencia, búscalo con buscar_juego para conocer su género, plataforma y precio.
2. Llama a buscar_alternativas_catalogo con el género, precio_max (el presupuesto del usuario) y excluir_ids
   con el id del juego de referencia.
3. Si devuelve menos de 3 resultados, AMPLÍA la búsqueda: repite sin el género o con un género parecido,
   y menciona que ampliaste la búsqueda.
4. Para los 2 o 3 mejores candidatos, usa obtener_resenas para comparar su valoración.
5. Para el mejor candidato, usa consultar_ofertas_externas; si no hay datos, usa buscar_en_wikipedia para
   complementar. Los datos externos son solo referencia: aclara su fuente. Si una fuente externa falla, continúa sin ella.
6. Nunca inventes juegos ni precios: usa solo lo que devolvieron las herramientas.
Respuesta final: una recomendación principal y hasta 2 alternativas, cada una con título [ID n], precio,
valoración y por qué la recomiendas, más una breve comparación. Indica las fuentes externas si las usaste."""


CONFIG = {
    "agente_presupuesto": {
        "prompt": lambda: PROMPT_PRESUPUESTO,
        "herramientas": ["buscar_juego", "calcular_total", "comparar_con_presupuesto"],
    },
    "agente_alternativas": {
        "prompt": _prompt_alternativas,
        "herramientas": [
            "buscar_juego", "buscar_alternativas_catalogo", "obtener_resenas",
            "consultar_ofertas_externas", "buscar_en_wikipedia",
        ],
    },
}


def ejecutar_servicio(usuario: dict, codigo: str, solicitud: str) -> dict:
    servicio = tokens.obtener_servicio_activo(codigo)   # 403 si el admin lo desactivó
    restante = tokens.verificar_cupo(usuario)           # 429 si agotó su límite
    config = CONFIG[codigo]

    resultado = agente_base.ejecutar_agente(
        config["prompt"](), solicitud, config["herramientas"], restante
    )
    conversacion_id = chatbot.guardar_intercambio(
        usuario["id"], servicio["id"], None, solicitud, resultado["respuesta"],
        resultado["fuentes"], resultado["t_entrada"], resultado["t_salida"],
    )
    total = resultado["t_entrada"] + resultado["t_salida"]
    return {
        "conversacion_id": conversacion_id,
        "respuesta": resultado["respuesta"],
        "pasos": resultado["pasos"],
        "fuentes": resultado["fuentes"],
        "tokens": {"entrada": resultado["t_entrada"], "salida": resultado["t_salida"], "total": total},
        "tokens_restantes": max(restante - total, 0),
    }
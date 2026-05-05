from app.nodes import app
from langgraph.types import Command
import sqlite3
import time


def _clear_user_state(user_id: str):
    try:
        thread_id = f"conversation_{user_id}"
        conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        try:
            cursor.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        except:
            pass
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Flow] Error limpiando estado: {e}")


# ── Mensajes de progreso (bocadillo) ────────────────────────────────────────
NODE_MESSAGES = {
    "router":                "Analizando...",
    "tool_interpreter":      "Interpretando petición...",
    "reasoning_interpreter": "Procesando petición...",
    "verifier":              "Verificando conflictos...",
    "tool_executor":         "Ejecutando acción...",
    "reasoning_executor":    "Consultando calendario...",
    "proposer":              "Buscando huecos libres...",
    "analysis":              "Analizando resultados...",
    "chat":                  "Pensando...",
    "process_user_decision": "Procesando...",
    "confirmer":             "Finalizando..."
}

# ── Frases typewriter por nodo ───────────────────────────────────────────────
NODE_TYPEWRITER = {
    "router": [
        "Leyendo tu mensaje...",
        "Clasificando la intención...",
    ],
    "tool_interpreter": [
        "Extrayendo nombre del evento...",
        "Determinando fecha y hora...",
    ],
    "reasoning_interpreter": [
        "Identificando qué información necesito...",
        "Preparando consulta al calendario...",
    ],
    "verifier": [
        "Comprobando el hueco horario...",
        "Buscando eventos solapados...",
    ],
    "tool_executor": [
        "Conectando con Google Calendar...",
        "Aplicando los cambios...",
    ],
    "reasoning_executor": [
        "Obteniendo tus eventos...",
        "Leyendo el calendario...",
    ],
    "proposer": [
        "Calculando huecos disponibles...",
        "Seleccionando las mejores opciones...",
    ],
    "analysis": [
        "Procesando los datos...",
        "Preparando el resumen...",
    ],
    "chat": [
        "Preparando respuesta...",
    ],
    "process_user_decision": [
        "Interpretando tu elección...",
    ],
    "confirmer": [
        "Dando forma a la respuesta...",
    ],
}

TYPEWRITER_CHUNK = 4  # caracteres por tick


def _emit_typewriter(frases: list):
    """Generador: emite chunks de texto letra a letra para cada frase."""
    for frase in frases:
        for i in range(0, len(frase), TYPEWRITER_CHUNK):
            yield {"type": "stream_chunk", "text": frase[i:i + TYPEWRITER_CHUNK]}
            time.sleep(0.1)
        time.sleep(0.8)
        yield {"type": "stream_chunk", "text": "\n"}


def _process_node(node_name: str, action: dict):
    """
    Generador: procesa un nodo y emite progress + typewriter.
    Devuelve también señales especiales para interrupt y confirmer.
    """
    # 1. Bocadillo de progreso
    if node_name in NODE_MESSAGES:
        yield {"type": "progress", "message": NODE_MESSAGES[node_name]}

    # 2. Typewriter cosmético
    if node_name in NODE_TYPEWRITER:
        yield from _emit_typewriter(NODE_TYPEWRITER[node_name])

    # 3. Interrupción (human-in-the-loop)
    if node_name == "__interrupt__":
        interrupt_data = action["__interrupt__"][0].value
        yield {
            "type": "response",
            "data": {
                "status": "waiting",
                "response": interrupt_data.get("response", "Elige una opción:"),
                "suggested_slots": interrupt_data.get("suggested_slots", [])
            }
        }

    # 4. Respuesta final
    if node_name == "confirmer":
        yield {
            "type": "confirmer",  # señal interna, no se emite al frontend
            "final_response": action["confirmer"].get("final_response")
        }


def run_agent(user_input: str, user_id: str, user_preferences: str = "", conversation_history: list = None):
    config = {"configurable": {"thread_id": f"conversation_{user_id}"}}
    inputs = {
        "input_user": user_input,
        "user_id": user_id,
        "user_preferences": user_preferences,
        "conversation_history": conversation_history or []
    }

    state = app.get_state(config)
    stream_input = Command(resume=user_input) if state.next else inputs

    try:
        result_found = False
        calendar_modified = False

        for action in app.stream(stream_input, config=config):
            for node_name in action.keys():

                if node_name == "tool_executor":
                    calendar_modified = True

                for event in _process_node(node_name, action):

                    # Señal interna de confirmer → construir respuesta final y salir
                    if event["type"] == "confirmer":
                        yield {
                            "type": "response",
                            "data": {
                                "status": "complete",
                                "response": event["final_response"] or "No pude procesar tu mensaje.",
                                "calendar_modified": calendar_modified
                            }
                        }
                        result_found = True
                        return

                    # Señal de interrupción → emitir y salir
                    if event["type"] == "response" and event["data"].get("status") == "waiting":
                        yield event
                        result_found = True
                        return

                    # Cualquier otra cosa (progress, stream_chunk) → emitir directamente
                    yield event

        if not result_found:
            _clear_user_state(user_id)
            yield from _run_fresh(inputs, config)

    except Exception as e:
        print(f"[Flow] Error: {e}")
        _clear_user_state(user_id)
        try:
            yield from _run_fresh(inputs, config)
        except Exception as e2:
            print(f"[Flow] Error en reintento: {e2}")
            yield {
                "type": "response",
                "data": {"status": "error", "response": "Ha ocurrido un error. Por favor, inténtalo de nuevo."}
            }


def _run_fresh(inputs: dict, config: dict):
    """Ejecuta el grafo desde cero (sin estado previo)."""
    calendar_modified = False

    for action in app.stream(inputs, config=config):
        for node_name in action.keys():

            if node_name == "tool_executor":
                calendar_modified = True

            for event in _process_node(node_name, action):

                if event["type"] == "confirmer":
                    yield {
                        "type": "response",
                        "data": {
                            "status": "complete",
                            "response": event["final_response"] or "No pude procesar tu mensaje.",
                            "calendar_modified": calendar_modified
                        }
                    }
                    return

                if event["type"] == "response" and event["data"].get("status") == "waiting":
                    yield event
                    return

                yield event
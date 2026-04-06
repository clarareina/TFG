from app.nodes import app
from langgraph.types import Command
import sqlite3


def _clear_user_state(user_id: str):
    """
    Borra el estado del usuario de la BD para empezar de cero.
    Se usa cuando hay errores o cuando la reanudación falla.
    """
    try:
        thread_id = f"conversation_{user_id}"
        conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
        cursor = conn.cursor()
        
        # Eliminamos los checkpoints (historial de estados de LangGraph)
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        try:
            cursor.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        except:
            pass
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Flow] Error limpiando estado: {e}")


# MAPEO DE NODOS A MENSAJES DE PROGRESO
NODE_MESSAGES = {
    "router": "Analizando...",
    "tool_interpreter": "Interpretando petición...",
    "reasoning_interpreter": "Procesando petición...",
    "verifier": "Verificando conflictos...",
    "tool_executor": "Ejecutando acción...",
    "reasoning_executor": "Consultando calendario...",
    "proposer": "Buscando huecos libres...",
    "analysis": "Analizando resultados...",
    "chat": "Pensando...",
    # "get_user_decision": "Esperando tu respuesta...",
    "process_user_decision": "Procesando...",
    "confirmer": "Finalizando..."
}


def run_agent(user_input: str, user_id: str, user_preferences: str = "", conversation_history: list = None):
    """
    FUNCIÓN PRINCIPAL DEL AGENTE (generador con streaming).
    
    Ejecuta el grafo de LangGraph y EMITE actualizaciones de progreso
    mientras procesa cada nodo. Maneja tanto conversaciones nuevas como
    reanudación de conversaciones pausadas (human-in-the-loop).
    
    ARGUMENTOS:
        user_input: El mensaje del usuario
        user_id: Email del usuario (identificador único)
        user_preferences: Preferencias guardadas del usuario (opcional)
        conversation_history: Últimos mensajes de la conversación (opcional)
    
    YIELDS (emite):
        {"type": "progress", "message": "..."} → Mensaje de progreso para mostrar
        {"type": "response", "data": {...}}   → Respuesta final del agente
    
    USO:
        for update in run_agent(...):
            if update["type"] == "progress":
                print(update["message"])  # "Analizando..."
            elif update["type"] == "response":
                result = update["data"]   # {"status": "complete", "response": "..."}
    """
    
    # Configuración del thread (cada usuario tiene su propia conversación)
    config = {"configurable": {"thread_id": f"conversation_{user_id}"}}
    
    # Inputs iniciales para el grafo
    inputs = {
        "input_user": user_input, 
        "user_id": user_id, 
        "user_preferences": user_preferences,
        "conversation_history": conversation_history or []
    }
    
    # DETECTAR SI HAY QUE REANUDAR UNA CONVERSACIÓN PAUSADA
    state = app.get_state(config)
    
    # Si state.next tiene valor, significa que el grafo está pausado esperando
    # respuesta del usuario (human-in-the-loop). En ese caso, reanudamos.
    if state.next:
        stream_input = Command(resume=user_input)  # Reanudar con la respuesta del usuario
    else:
        stream_input = inputs  # Conversación nueva
    
    # EJECUTAR EL GRAFO Y EMITIR ACTUALIZACIONES
    try:
        result_found = False
        calendar_modified = False  # Rastrear si hubo modificación
        
        # app.stream() ejecuta el grafo paso a paso
        for action in app.stream(stream_input, config=config):
            
            # 'action' es un diccionario donde la KEY es el nombre del nodo
            # que acaba de ejecutarse. Ejemplo: {"router": {...}}
            
            for node_name in action.keys():
                
                # 1. EMITIR MENSAJE DE PROGRESO
                # Si el nodo tiene un mensaje amigable configurado, lo enviamos
                if node_name in NODE_MESSAGES:
                    yield {
                        "type": "progress",
                        "message": NODE_MESSAGES[node_name]
                    }
                
                # Detectar si se ejecutó una acción de escritura
                if node_name == "tool_executor":
                    # Si pasó por tool_executor, hubo modificación del calendario
                    calendar_modified = True
                
                # 2. DETECTAR INTERRUPCIÓN (human-in-the-loop)
                # El grafo se pausa y espera que el usuario elija una opción
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
                    result_found = True
                    return  # Terminar el generador, esperamos respuesta
                
                # 3. DETECTAR RESPUESTA FINAL
                # El grafo llegó al nodo final (confirmer)
                if node_name == "confirmer":
                    final_response = action["confirmer"].get("final_response")
                    
                    yield {
                        "type": "response",
                        "data": {
                            "status": "complete",
                            "response": final_response or "No pude procesar tu mensaje.",
                            "calendar_modified": calendar_modified
                        }
                    }
                    result_found = True
                    return  # Terminar el generador
        
        # Si el grafo terminó pero no encontramos respuesta válida
        if not result_found:
            # Esto puede pasar si reanudamos pero el grafo no devolvió nada útil
            _clear_user_state(user_id)
            
            # Reintentar como conversación nueva
            for update in _run_fresh(inputs, config):
                yield update
    
    except Exception as e:
        # Si hay cualquier error, limpiamos el estado e intentamos de nuevo
        _clear_user_state(user_id)
        
        # Reintentar como conversación nueva
        try:
            for update in _run_fresh(inputs, config):
                yield update
        except Exception as e2:
            print(f"DEBUG ERROR en Nodo: {str(e2)}") # Esto te dirá la verdad en la terminal
            # Si sigue fallando, emitir error
            yield {
                "type": "response",
                "data": {
                    "status": "error",
                    "response": "Ha ocurrido un error. Por favor, inténtalo de nuevo."
                }
            }


def _run_fresh(inputs: dict, config: dict):
    """
    Helper interno: Ejecuta el grafo desde cero (sin estado previo).
    Se usa cuando la reanudación falla o hay errores.
    """
    for action in app.stream(inputs, config=config):
        for node_name in action.keys():
            if node_name in NODE_MESSAGES:
                yield {"type": "progress", "message": NODE_MESSAGES[node_name]}
            
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
                return
            
            if node_name == "confirmer":
                yield {
                    "type": "response",
                    "data": {
                        "status": "complete",
                        "response": action["confirmer"].get("final_response") or "No pude procesar tu mensaje."
                    }
                }
                return
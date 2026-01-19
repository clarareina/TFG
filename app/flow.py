from app.nodes import app
from langgraph.types import Command
import sqlite3

def _clear_user_state(user_id: str):
    """Borra el estado del usuario de la BD para empezar de cero."""
    try:
        # thread_id único por usuario
        thread_id = f"conversation_{user_id}"
        conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
        cursor = conn.cursor()
        
        # Eliminamos los checkpoints (el historial de estados de LangGraph)
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        try:
            # Eliminamos escrituras pendientes si existen
            cursor.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        except:
            pass
        
        conn.commit()
        conn.close()
        print(f"[Flow] Estado limpiado para {user_id}")
    except Exception as e:
        print(f"[Flow] Error limpiando estado: {e}")

def _run_new_flow(user_input: str, user_id: str, config: dict, user_preferences: str) -> dict:
    """Ejecuta el flujo desde el principio."""
    
    inputs = {
        "input_user": user_input, 
        "user_id": user_id, 
        "user_preferences": user_preferences 
    }
    
    result = None
    
    # app.stream ejecuta el grafo paso a paso
    for event in app.stream(inputs, config=config):
        
        # Interrupción (Human-in-the-loop)
        # Si el grafo se detiene capturamos el evento
        if "__interrupt__" in event:
            interrupt_data = event["__interrupt__"][0].value
            return {
                "status": "waiting", # Indicamos al frontend que esperamos respuesta
                "response": interrupt_data.get("response", "Elige una opción:"),
                "suggested_slots": interrupt_data.get("suggested_slots", [])
            }
        
        # Si llegamos al nodo final (confirmer), capturamos la respuesta.
        if "confirmer" in event:
            result = event["confirmer"].get("final_response")
    
    return {"status": "complete", "response": result or "No pude procesar tu mensaje. Por favor, inténtalo de nuevo."}

def run_agent(user_input: str, user_id: str, user_preferences: str = "") -> dict:
    """
    Ejecuta el agente gestionando pausas y reanudaciones.
    Si la reanudación falla, limpia el estado y procesa como nueva conversación.
    """
    config = {"configurable": {"thread_id": f"conversation_{user_id}"}}
    
    # Obtenemos el estado actual desde la base de datos (checkpoints)
    state = app.get_state(config)
    
    # 1. LOGICA DE REANUDACIÓN
    # Si tiene valor, el grafo se quedó "pausado" en un nodo anterior esperando input del usuario 
    if state.next: 
        
        try:
            result = None
            # Command(resume=...) para decirle al grafo: "Aquí tienes la respuesta que esperabas, continúa".
            for event in app.stream(Command(resume=user_input), config=config):
                
                # si vuelve a interrumpirse 
                if "__interrupt__" in event:
                    interrupt_data = event["__interrupt__"][0].value
                    return {
                        "status": "waiting",
                        "response": interrupt_data.get("response", "Elige una opción:"),
                        "suggested_slots": interrupt_data.get("suggested_slots", [])
                    }
                
                if "confirmer" in event:
                    result = event["confirmer"].get("final_response")
            
            if result:
                return {"status": "complete", "response": result}
            else:
                #Fallo en reanudación
                # Si reanudamos pero el grafo no devolvió nada útil borramos todo y tratamos el mensaje como si fuera nuevo.
                _clear_user_state(user_id)
                return _run_new_flow(user_input, user_id, config, user_preferences)
                
        except Exception as e:
            _clear_user_state(user_id)
            return _run_new_flow(user_input, user_id, config, user_preferences)
    
    # 2. LOGICA DE INICIO NUEVO
    # Si no había estado pendiente, es una conversación normal.
    else:
        return _run_new_flow(user_input, user_id, config, user_preferences)
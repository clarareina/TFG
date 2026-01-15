from app.nodes import app
from langgraph.types import Command
import sqlite3

def _clear_user_state(user_id: str):
    """Borra el estado del usuario de la BD para empezar de cero."""
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
        print(f"[Flow] Estado limpiado para {user_id}")
    except Exception as e:
        print(f"[Flow] Error limpiando estado: {e}")

def _run_new_flow(user_input: str, user_id: str, config: dict) -> dict:
    """Ejecuta el flujo desde el principio."""
    inputs = {"input_user": user_input, "user_id": user_id}
    result = None
    
    for event in app.stream(inputs, config=config):
        if "__interrupt__" in event:
            interrupt_data = event["__interrupt__"][0].value
            return {
                "status": "waiting",
                "response": interrupt_data.get("response", "Elige una opción:"),
                "suggested_slots": interrupt_data.get("suggested_slots", [])
            }
        
        if "confirmer" in event:
            result = event["confirmer"].get("final_response")
    
    return {"status": "complete", "response": result or "No pude procesar tu mensaje. Por favor, inténtalo de nuevo."}

def run_agent(user_input: str, user_id: str) -> dict:
    """
    Ejecuta el agente gestionando pausas y reanudaciones.
    Si la reanudación falla, limpia el estado y procesa como nueva conversación.
    """
    config = {"configurable": {"thread_id": f"conversation_{user_id}"}}
    
    state = app.get_state(config)
    
    # LOGICA DE REANUDACIÓN
    if state.next:  # Si hay un paso pendiente
        
        try:
            result = None
            for event in app.stream(Command(resume=user_input), config=config):
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
                # Fallo sin resultado: limpiar estado y procesar como nuevo
                print(f"[Flow] Reanudación sin resultado, limpiando y reprocesando...")
                _clear_user_state(user_id)
                return _run_new_flow(user_input, user_id, config)
                
        except Exception as e:
            print(f"[Flow Error] Error en reanudación: {e}. Limpiando estado...")
            _clear_user_state(user_id)
            return _run_new_flow(user_input, user_id, config)
    
    # LOGICA DE INICIO NUEVO
    else:
        return _run_new_flow(user_input, user_id, config)
from app.nodes import app 
from langgraph.types import Command

# dice qué "cajón" de memoria usar
config = {"configurable": {"thread_id": "conversation_1"}}


def run_agent(user_input: str) -> dict:
    """
    Ejecuta el agente. Puede devolver:
    - {"status": "complete", "response": "..."} si terminó
    - {"status": "waiting", "message": "...", "suggested_slots": [...]} si espera decisión
    """
    # Primero verificamos si hay un interrupt pendiente (el flujo está pausado)
    state = app.get_state(config)
    
    if state.next:  # Hay un nodo pendiente de ejecutar (el flujo está pausado)
        # El usuario está respondiendo a un interrupt - reanudar el flujo
        result = None
        for event in app.stream(Command(resume=user_input), config=config):
            if "__interrupt__" in event:
                # Aún está en interrupt (por si acaso)
                interrupt_data = event["__interrupt__"][0].value
                return {
                    "status": "waiting",
                    "message": interrupt_data.get("message", "Elige una opción:"),
                    "suggested_slots": interrupt_data.get("suggested_slots", [])
                }
            if "confirmer" in event:
                result = event["confirmer"].get("final_response")
        
        return {"status": "complete", "response": result or "Error"}
    
    else:
        # Nueva petición - iniciar el flujo
        inputs = {"input_user": user_input}
        result = None
        
        for event in app.stream(inputs, config=config):
            if "__interrupt__" in event:
                # El flujo se pausó esperando decisión del usuario
                interrupt_data = event["__interrupt__"][0].value
                return {
                    "status": "waiting",
                    "message": interrupt_data.get("message", "Elige una opción:"),
                    "suggested_slots": interrupt_data.get("suggested_slots", [])
                }
            if "confirmer" in event:
                result = event["confirmer"].get("final_response")
        
        return {"status": "complete", "response": result or "Error"}

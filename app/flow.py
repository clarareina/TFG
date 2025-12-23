from app.nodes import app # Importas el agente YA compilado

# Le dices qué "cajón" de memoria usar
config = {"configurable": {"thread_id": "conversation_1"}}

def run_agent(user_input: str) -> str:
        
    inputs = {"input_user": user_input}
    final_response = "Error"
    
    # app.stream() ejecuta el grafo Y gestiona la memoria
    for event in app.stream(inputs, config=config):
        if "confirmer" in event:
            final_response = event["confirmer"].get("final_response")
    return final_response

# # app/flow.py
# from typing import Dict, Any
# from nodes import interpret_command_node, execute_calendar_node, confirmation_node

# def run_agent(user_input: str) -> Dict[str, Any]:
#     """
#     Ejecuta el flujo completo del agente:
#     1) Interpreta la orden del usuario.
#     2) Ejecuta las acciones necesarias.
#     3) Devuelve una respuesta final.
#     """
#     # Estado inicial
#     state: Dict[str, Any] = {
#         "input_user": user_input,
#         "conversation_history": [],
#         "structured_json_list": None,
#         "api_response_list": None,
#         "final_response": None,
#         "error_message": None
#     }

#     try:
#         state.update(interpret_command_node(state))
#         state.update(execute_calendar_node(state))
#         state.update(confirmation_node(state))

#     except Exception as e:
#         state["error_message"] = "internal_error"
#         state["final_response"] = "Ocurrió un problema al procesar tu solicitud."

#     return state



from nodes import app # Importas el agente YA compilado

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

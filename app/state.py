from typing import TypedDict, Optional, List, Dict, Any, Literal


class UndoableAction(TypedDict):
    """
    Guarda la información necesaria para revertir una acción 
    ejecutada en Google Calendar.
    """
    operation: Literal["create_event", "delete_event", "patch_event", "delete_date_events"] # La acción que se realizó
    calendarId: str
    eventId: str  # Para acciones simples
    previous_body: Optional[Dict[str, Any]] # El 'body' ANTES de la acción (acciones simples)
    previous_bodies: Optional[List[Dict[str, Any]]] # Lista de bodies para delete_date_events

class VerificationResult(TypedDict):
    """
    Almacena el resultado de una comprobación de conflictos.
    """
    conflict_found: bool                  
    conflicting_events: List[Dict[str, Any]] # Lista de eventos que chocan

class AgentState(TypedDict):
    """
    Representa el estado completo de una ejecución del agente.
    (Este es el "formulario" que viaja por el grafo)
    """
    input_user: str
    user_id: str
    user_preferences: str
    
    conversation_history: List[Dict[str, str]]  
    last_llm_response: Optional[str]            # Última respuesta del asistente (para contexto en router y process_user_decision)

    structured_json_list: Optional[List[Dict[str, Any]]]   # El JSON que sale de Gemini
    api_response_list: Optional[List[Any]]   # La respuesta de Calendar 
    final_response: Optional[str]
    error_message: Optional[str]
    last_undoable_action: Optional[List[UndoableAction]] # Lista de acciones que podemos deshacer
    verification_result: Optional[VerificationResult] # Resultado de la comprobación
    pending_action: Optional[Dict[str, Any]]   # Almacena la acción que causó el conflicto
    suggested_slots: Optional[List[Dict[str, str]]]  # Almacena las sugerencias (ej. [{'start': ..., 'end': ...}])
    user_choice: Optional[str]
    routing_decision: Optional[str]
    is_final: Optional[bool]
    analysis_has_options: Optional[bool]  # Para bifurcación en analysis_node
    tool_refused: Optional[bool]          # True si tool_interpreter rechazó la petición por no ser una acción de calendario
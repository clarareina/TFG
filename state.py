from typing import TypedDict, Optional, List, Dict, Any, Literal


class UndoableAction(TypedDict):
    """
    Guarda la información necesaria para revertir una acción 
    ejecutada en Google Calendar.
    """
    operation: Literal["create_event", "delete_event", "patch_event"] # La acción que se realizó
    calendarId: str
    eventId: str
    previous_body: Optional[Dict[str, Any]] # El 'body' ANTES de la acción

class VerificationResult(TypedDict):
    """
    Almacena el resultado de una comprobación de conflictos.
    """
    conflict_found: bool                  # ¿Se ha encontrado un conflicto?
    conflicting_events: List[Dict[str, Any]] # Lista de eventos (cuerpos) que chocan

class AgentState(TypedDict):
    """
    Representa el estado completo de una ejecución del agente.
    (Este es el "formulario" que viaja por el grafo)
        """
    input_user: str

    conversation_history: List[str]

    structured_json_list: Optional[List[Dict[str, Any]]]   # El JSON que sale de Gemini
    api_response_list: Optional[List[Any]]   # La respuesta de Calendar 
    final_response: Optional[str]
    error_message: Optional[str]
    last_undoable_action: Optional[UndoableAction] # La última acción que podemos deshacer
    verification_result: Optional[VerificationResult] # Resultado de la comprobación
    pending_action: Optional[Dict[str, Any]]   # Almacena la acción que causó el conflicto
    suggested_slots: Optional[List[Dict[str, str]]]  # Almacena las sugerencias (ej. [{'start': ..., 'end': ...}])



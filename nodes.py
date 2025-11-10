import json
import re
from typing import TypedDict, Optional, List, Dict, Any, Literal
from prompt import prompt as gemini_prompt_template
from gemini_client import generar_respuesta
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph
import calendar_functions 
from state import AgentState, VerificationResult
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo 
import sqlite3, atexit

# ----------------------------------------------------------------------
# FUNCIONES AUXILIARES 
# ----------------------------------------------------------------------

def clean_json(text):
    """Limpia el 'wrapper' ```json ... ``` de la respuesta de Gemini."""
    if not text:
        return ""
    return re.sub(r"```json|```", "", text, flags=re.IGNORECASE).strip()


def interpret_response_json(text):
    """Convierte el texto limpio de Gemini en un dict o lista de Python."""
    clean_text = clean_json(text)
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        print(f"Error: Gemini devolvió un JSON inválido:\n{clean_text}")
        return None


# ----------------------------------------------------------------------
# MAPA DE FUNCIONES
# ----------------------------------------------------------------------

FUNCTION_MAP = {
    "create_event": calendar_functions.create_event,
    "delete_event": calendar_functions.delete_event,
    "duplicate_event": calendar_functions.duplicate_event,
    "patch_event": calendar_functions.patch_event,
    "get_events": calendar_functions.get_events,
    "undo_last_action": calendar_functions.undo_last_action
}


# ----------------------------------------------------------------------
# NODOS
# ----------------------------------------------------------------------

def interpret_command_node(state: dict) -> dict:
    """Envía el prompt al modelo Gemini y devuelve la estructura JSON de acciones."""
    user_input = state['input_user']
    prompt_final = f"{gemini_prompt_template}\n\nUsuario: {user_input}\n"
    response_text = generar_respuesta(prompt_final)
    json_object = interpret_response_json(response_text)

    actions_to_execute = []
    if isinstance(json_object, list):
        actions_to_execute = json_object
    elif isinstance(json_object, dict):
        actions_to_execute.append(json_object)
            
    return {"structured_json_list": actions_to_execute}


def execute_calendar_node(state: AgentState) -> dict:
    """Ejecuta las acciones indicadas en el JSON interpretado."""
    action_list = state.get('structured_json_list', [])
    current_undo_state = state.get('last_undoable_action')
    execution_results = []

    for action in action_list:
        function_name = action.get("function")
        parameters = action.get("parameters", {})

        if function_name in FUNCTION_MAP:
            actual_function = FUNCTION_MAP[function_name]

            if function_name == "undo_last_action":
                parameters = {"action_to_undo": current_undo_state}

            try:
                action_result = actual_function(**parameters)
                if isinstance(action_result, dict):
                    response_str = action_result.get("response", "Acción completada.")
                    new_undo_info = action_result.get("undo_info") 
                    execution_results.append(response_str)
                    current_undo_state = new_undo_info
                else:
                    execution_results.append(str(action_result))
            except Exception as e:
                execution_results.append(f"Error: {e}")
        else:
            execution_results.append(f"Error: función {function_name} no encontrada.")

    return {
        "api_response_list": execution_results,
        "last_undoable_action": current_undo_state
    }


def confirmation_node(state: dict) -> dict:
    """Devuelve la respuesta final al usuario."""
    results = state.get("api_response_list", [])
    if not results:
        return {"final_response": "No se obtuvo respuesta del calendario."}
    return {"final_response": results[0]} 


# ----------------------------------------------------------------------
# VERIFICATION NODE 
# ----------------------------------------------------------------------

LOCAL_TZ = ZoneInfo("Europe/Madrid")

def verification_node(state: AgentState) -> dict:
    """
    Verifica si hay conflictos horarios antes de crear, duplicar o editar.
    """
    action_list = state.get('structured_json_list', [])
    if not action_list or len(action_list) > 1:
        return {}
        
    action = action_list[0]
    function_name = action.get("function")
    parameters = action.get("parameters", {})

    check_start = None
    check_end = None
    
    if function_name == "create_event":
        start_date = parameters.get("start_date")
        start_time = parameters.get("start_time")
        end_date = parameters.get("end_date")
        end_time = parameters.get("end_time")

        if not start_date:
            return {}
        
        if not start_time:
            # Evento de día completo
            check_start = start_date
            # Aseguramos que end_date tenga valor para la API (si es un solo día)
            check_end = end_date if end_date else start_date
        else:
            try:
                start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)
                if not end_time:
                    end_dt = start_dt + timedelta(hours=1)
                else:
                    end_dt = datetime.strptime(f"{end_date or start_date} {end_time}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)

                check_start = start_dt.isoformat()
                check_end = end_dt.isoformat()
            except ValueError as e:
                print(f"[Verification] Error al parsear fecha/hora: {e}")
                return {}
        
    elif function_name == "duplicate_event":
        start_date = parameters.get("new_date")
        start_time = parameters.get("new_time")

        if not start_date:
            return {}
        
        try:
            start_dt = datetime.strptime(f"{start_date} {start_time or '00:00'}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)
            end_dt = start_dt + timedelta(hours=1) # Asumimos 1h por defecto para duplicados
            check_start = start_dt.isoformat()
            check_end = end_dt.isoformat()
        except ValueError as e:
            print(f"[Verification] Error al parsear fecha/hora: {e}")
            return {}
                
    elif function_name == "patch_event":
        changes = parameters.get("changes", {})
        if "start" in changes:
            start_data = changes.get("start", {})
            end_data = changes.get("end", {}) 
            start_str = start_data.get("dateTime", start_data.get("date"))
            end_str = end_data.get("dateTime", end_data.get("date"))
            
            if not start_str or not end_str:
                 # Si no se están modificando las fechas, no hay conflicto que verificar
                 return {}

            try:
                # Parsear el string 'naive' de Gemini (ej. "2025-11-08T12:00:00")
                naive_start = datetime.fromisoformat(start_str)
                naive_end = datetime.fromisoformat(end_str)

                # Asignarle la zona horaria local (Europe/Madrid)
                aware_start = naive_start.replace(tzinfo=LOCAL_TZ)
                aware_end = naive_end.replace(tzinfo=LOCAL_TZ)
                
                check_start = aware_start.isoformat()
                check_end = aware_end.isoformat()

            except ValueError as e:
                print(f"[Verification] Error al parsear dateTime de patch: {e}")
                return {}
        else:
            # Si el patch no incluye 'start', no hay nada que verificar
            return {}
    else:
        # Si la función no es create, duplicate o patch, no verificamos
        return {}

    if not check_start:
        # Si ninguna lógica asignó fechas (p.ej. patch sin 'start'), salimos
        return {}
        
    scan_result_package = calendar_functions.get_events(
        start_date=check_start, 
        end_date=check_end,
        max=5 
    )

    scan_response_str = scan_result_package.get("response", "")
    
    if "No se encontraron eventos" in scan_response_str:
        result = VerificationResult(conflict_found=False, conflicting_events=[])
        return {"verification_result": result, "pending_action": None}

    else:
        result = VerificationResult(conflict_found=True, conflicting_events=[{"summary": scan_response_str}])
        return {"verification_result": result, "pending_action": action}


def propose_node(state:AgentState) -> dict:
    """
    Tras un conflicto, llama a find_free_slots y propone alternativas.
    """
    pending_actions = state.get("pending_action")
    
    parameters = pending_actions.get("parameters", {})
    summary = parameters.get("summary")
    start_date_str = parameters.get("start_date") #string YYYY-MM-DD
    start_time_str = parameters.get("start_time")
    end_date_str = parameters.get("end_date")
    end_time_str = parameters.get("end_time")
    duration_minutes = 60 # Valor por defecto si falla el cálculo

    if start_date_str and start_time_str and end_date_str and end_time_str: # Evento con inicio y fin
        start_dt = datetime.strptime(f"{start_date_str} {start_time_str}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{end_date_str} {end_time_str}", "%Y-%m-%d %H:%M")
        duration_delta = end_dt - start_dt
        duration_minutes = int(duration_delta.total_seconds() / 60)
    
    elif start_date_str and start_time_str and not end_date_str and not end_time_str: # Evento con inicio (1h por defecto)
        start_dt = datetime.strptime(f"{start_date_str} {start_time_str}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(hours=1)
        #duracion 60 min
    
    elif start_date_str and not start_time_str and not end_date_str and not end_time_str: #Evento con fecha inicio (Todo el dia)
        start_dt = datetime.strptime(f"{start_date_str}", "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=1)
        duration_minutes = 1440
    
    
    # # Aseguramos una duración mínima
    # if duration_minutes <= 0:
    #     duration_minutes = 60

    duration = timedelta(minutes=duration_minutes)
    free_slots = calendar_functions.find_free_slots(duration=duration, datetime_min=start_dt.replace(tzinfo=LOCAL_TZ).isoformat())

    if not free_slots:
        msg = f"Conflicto detectado para '{summary}'. No he encontrado huecos libres cercanos. ¿Quieres 'forzar' el evento o 'cancelar'?"
        return {"api_response_list": [msg], "suggested_slots": []}
    else:
        suggestions = []
        for gap in free_slots:
            if len(suggestions) >= 5:
                break
            current_time = datetime.fromisoformat(gap['start'])
            gap_end = datetime.fromisoformat(gap['end'])

            while ((current_time + duration) <= gap_end):
                if len(suggestions) >= 5:
                    break
                slot_end = current_time + duration
                print("current_time.hour:", current_time.hour)
                print("slot_end.hour:", slot_end.hour)
                if ((8 <= current_time.hour < 20) and (8 <= slot_end.hour <= 20)):
                    suggestions.append({
                        "start": current_time.isoformat(),
                        "end": slot_end.isoformat()
                    })
                current_time = slot_end
                
        print('3')
    
        if not suggestions:
            msg = f"Conflicto detectado para '{summary}'. He encontrado huecos, pero ninguno es suficientemente largo para los {duration_minutes} min. ¿Quieres 'forzar' o 'cancelar'?"
            return {"api_response_list": [msg], "suggested_slots": []}
        else:
            msg = f"Conflicto detectado para '{summary}'. Ya hay un evento. He encontrado estos huecos alternativos:\n"

            for i, slot in enumerate(suggestions):
                friendly_time = (
                    f"{datetime.fromisoformat(slot['start']).strftime('%Y-%m-%d')} de {datetime.fromisoformat(slot['start']).strftime('%H:%M')} "
                    f"a {datetime.fromisoformat(slot['end']).strftime('%H:%M')}")
                msg += f"  {i+1}. {friendly_time}\n"

            msg += "Elige el número de la opción, 'forzar' (para añadirlo igualmente) o 'cancelar'."
            return {"api_response_list": [msg], "suggested_slots": suggestions} 







# ----------------------------------------------------------------------
# MONTAJE DEL GRAFO
# ----------------------------------------------------------------------

workflow = StateGraph(AgentState)
workflow.add_node("interpreter", interpret_command_node)
workflow.add_node("verifier", verification_node) 
workflow.add_node("executor", execute_calendar_node)
workflow.add_node("proposer", propose_node) 
workflow.add_node("confirmer", confirmation_node)

def decide_next_step(state: AgentState):
    verification = state.get("verification_result")
    if verification and verification["conflict_found"]:
        return "report_conflict"
    else:
        # Si verification_result está vacío (porque no se verificó) o no hay conflicto
        return "continue_execution"
    
workflow.set_entry_point("interpreter")
workflow.add_edge("interpreter", "verifier")
workflow.add_conditional_edges("verifier", decide_next_step,
    {
        "report_conflict": "proposer",
        "continue_execution": "executor"
    }
)
workflow.add_edge("executor", "confirmer")
workflow.add_edge("proposer", "confirmer")
workflow.add_edge("confirmer", "__end__")

conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
memory = SqliteSaver(conn=conn)
atexit.register(conn.close)
app = workflow.compile(checkpointer=memory)
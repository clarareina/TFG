import json
import re
from typing import Literal
from .prompts import tool_prompt, reasoning_prompt, analysis_prompt
from .services.gemini_client import generar_respuesta
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph
from app import calendar_tools
from .state import AgentState, VerificationResult
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo 
import sqlite3, atexit

LOCAL_TZ = ZoneInfo("Europe/Madrid")


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



FUNCTION_MAP = {
    "create_event": calendar_tools.create_event,
    "delete_event": calendar_tools.delete_event,
    "delete_date_events": calendar_tools.delete_date_events,
    "duplicate_event": calendar_tools.duplicate_event,
    "patch_event": calendar_tools.patch_event,
    "get_events": calendar_tools.get_events,
    "undo_last_action": calendar_tools.undo_last_action
}



RoutingDecision = Literal["tool_use", "reasoning", "chat"] 
def router_node(state: AgentState) -> dict:
    """
    Clasifica la intención del usuario.
    """
    raw_msg = state['input_user']
    
    message = raw_msg.lower().strip()

    
    strong_tool_keywords = [
        "crea", "borra", "elimina", "agenda", "pon ", "quita", "modifica", 
        "cambia", "duplica", "cancela", "reunión", "deshaz", "revierte", "muestra", "lista"]
    
    if any(w in message for w in strong_tool_keywords):
        print(f"[Router] (Tool)")
        return {"routing_decision": "tool_use"}
    
    if any(w in message for w in ["busca", "crees", "idea", "encuentra", "tardar", "hueco", "tengo", "resum", "dime", "cuanto", "cuánto", "estima"]):
        print(f"[Router] (Reasoning)")
        return {"routing_decision": "reasoning"}
    
    
    
    classification_prompt = f"""
    Eres un enrutador de sistema ciego. Clasifica el texto.

    CATEGORÍAS:
    1. tool_use: Acciones (crear, borrar, modificar, deshacer). REGLA DE ORO: Ante la duda de una acción, usa esta.
    2. reasoning: Consultas, análisis, búsquedas.
    3. chat: SOLO para saludos ("Hola"), despedidas ("Adiós", "Gracias"), o temas que NO tienen nada que ver con el calendario (chistes, el tiempo, política).
   
    Petición: "{raw_msg}" # Usamos el mensaje original con mayúsculas para el LLM
    
    Responde SOLO: tool_use, reasoning o chat.
    """
    
    response_obj = generar_respuesta(classification_prompt)
    decision = response_obj.content.strip().lower() if hasattr(response_obj, 'content') else str(response_obj).strip().lower()
    
    if "tool" in decision:
        return {"routing_decision": "tool_use"}
    elif "reason" in decision:
        return {"routing_decision": "reasoning"}
    elif "chat" in decision:
        return {"routing_decision": "chat"}
    
    return {"routing_decision": "chat"}


def tool_interpreter(state: dict) -> dict:
    """Envía el prompt al modelo Gemini y devuelve la estructura JSON de acciones."""
    user_input = state['input_user']
    prompt_final = f"{tool_prompt()}\n\nUsuario: {user_input}\n"
    response_text = generar_respuesta(prompt_final)
    json_object = interpret_response_json(response_text)

    actions_to_execute = []
    if isinstance(json_object, list):
        actions_to_execute = json_object
    elif isinstance(json_object, dict):
        actions_to_execute.append(json_object)
            
    return {"structured_json_list": actions_to_execute}


def reasoning_interpreter(state: dict) -> dict:
    """Envía el prompt al modelo Gemini y devuelve la estructura JSON de acciones."""
    user_input = state['input_user']
    prompt_final = f"{reasoning_prompt()}\n\nUsuario: {user_input}\n"
    response_text = generar_respuesta(prompt_final)
    json_object = interpret_response_json(response_text)

    actions_to_execute = []
    if isinstance(json_object, list):
        actions_to_execute = json_object
    elif isinstance(json_object, dict):
        actions_to_execute.append(json_object)
    
    # Fallback: si no hay acciones válidas, usar get_events para la semana actual
    if not actions_to_execute:
        now = datetime.now(LOCAL_TZ)
        start_week = now - timedelta(days=now.weekday())
        end_week = start_week + timedelta(days=6)
        actions_to_execute = [{
            "function": "get_events",
            "parameters": {
                "start_date": start_week.strftime("%Y-%m-%d"),
                "end_date": end_week.strftime("%Y-%m-%d")
            }
        }]
                
    return {
        "structured_json_list": actions_to_execute,
        "api_response_list": [] 
    }



def tool_executor(state: AgentState) -> dict:
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

def reasoning_executor(state: dict) -> dict:
    """
    Ejecuta herramientas de LECTURA (Reasoning).
    Mapea los parámetros JSON a los tipos de datos exactos que piden las funciones Python.
    """
    action_list = state.get('structured_json_list', [])
    execution_results = []

    for action in action_list:
        function_name = action.get("function")
        parameters = action.get("parameters", {})

        try:
            if function_name == "find_free_slots":
                mins = parameters.get("duration", 60)
                duration_td = timedelta(minutes=int(mins))

                start_date = parameters.get("start_date")
                start_time = parameters.get("start_time", "00:00")
                
                # Si no hay fecha fin, asumimos el mismo día
                end_date = parameters.get("end_date", start_date) 
                end_time = parameters.get("end_time", "23:59")

                start_dt_str = f"{start_date} {start_time}"
                end_dt_str = f"{end_date} {end_time}"
                
                dt_min = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ).isoformat()
                dt_max = datetime.strptime(end_dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ).isoformat()

                result = calendar_tools.find_free_slots(
                    duration=duration_td,
                    datetime_min=dt_min,
                    datetime_max=dt_max
                )
                execution_results.append(result)

            # CASO 2: OBTENER EVENTOS
            elif function_name == "get_events":
                result = calendar_tools.get_events(**parameters)
                execution_results.append(result)

            # CASO 3: ESTIMAR DURACIÓN
            elif function_name == "estimate_duration":
                # No hay función Python, pasamos el contexto al análisis
                execution_results.append(parameters)

            else:
                execution_results.append(f"Error: Función de razonamiento '{function_name}' no reconocida.")

        except Exception as e:
            print(f"Error ejecutando {function_name}: {e}")
            execution_results.append(f"Error al obtener datos: {str(e)}")

    return {
        "api_response_list": execution_results
    }

    
def confirmation_node(state: dict) -> dict:
    """Devuelve la respuesta final al usuario."""
    results = state.get("api_response_list", [])
    if not results:
        return {"final_response": "No se obtuvo respuesta del calendario."}
    return {"final_response": "\n".join(results)} 



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
                # Parsear el string naive (ej. "2025-11-08T12:00:00")
                naive_start = datetime.fromisoformat(start_str)
                naive_end = datetime.fromisoformat(end_str)

                # Asignar zona horaria local
                aware_start = naive_start.replace(tzinfo=LOCAL_TZ)
                aware_end = naive_end.replace(tzinfo=LOCAL_TZ)
                
                check_start = aware_start.isoformat()
                check_end = aware_end.isoformat()

            except ValueError as e:
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
        
    scan_result_package = calendar_tools.get_events(
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
    free_slots = calendar_tools.find_free_slots(duration=duration, datetime_min=start_dt.replace(tzinfo=LOCAL_TZ).isoformat())

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
                if ((8 <= current_time.hour < 20) and (8 <= slot_end.hour <= 20)):
                    suggestions.append({
                        "start": current_time.isoformat(),
                        "end": slot_end.isoformat()
                    })
                current_time = slot_end
                
    
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



#nodo de espera
def get_user_decision(state: AgentState) -> dict:
    """
    Imprime la propuesta Y LUEGO pausa el flujo.
    """    
    messages = state.get("api_response_list", [])
    if messages:
        print("\n" + messages[0]) 
    
    user_input = input("> ").strip().lower()
    state["user_choice"] = user_input
    
    return state

def process_user_decision(state: AgentState) -> dict:
    user_choice = state.get("user_choice", '').lower()
    suggested_slots = state.get("suggested_slots", [])
    pending_action = state.get("pending_action")

    if user_choice == "forzar":
        state['routing_decision'] = 'execute' 
        state['verification_result'] = VerificationResult(conflict_found=False)
   
    elif user_choice == "cancelar":
        state['api_response_list'] = ["Acción cancelada"]
        state['pending_action'] = None
        state['routing_decision'] = 'end'
        state['verification_result'] = VerificationResult(conflict_found=False)

    elif user_choice.isdigit():
        index = int(user_choice) - 1    # user_choice = "1" → int("1") pero se usa suggested_slots[0]
        if 0 <= index < len(suggested_slots):
            chosen_slot = suggested_slots[index]
            # Actualizar fechas en la acción pendiente
            start_dt = datetime.fromisoformat(chosen_slot["start"])
            end_dt = datetime.fromisoformat(chosen_slot["end"])

            parameters = pending_action.get("parameters", {})
            parameters["start_date"] = start_dt.strftime("%Y-%m-%d")
            parameters["start_time"] = start_dt.strftime("%H:%M")
            parameters["end_date"] = end_dt.strftime("%Y-%m-%d")
            parameters["end_time"] = end_dt.strftime("%H:%M")
            pending_action["parameters"] = parameters

            state['pending_action'] = pending_action
            state['routing_decision'] = 'execute'
            state['verification_result'] = VerificationResult(conflict_found=False)

        else:
            state['api_response_list'] = ['Opción inválida']
            state['routing_decision'] = 'invalid_choice'
    else:
        state['routing_decision'] = 'invalid_choice'
    return state


def analysis_node(state: dict) -> dict:
    actions = state.get("structured_json_list", [])
    if not actions:
        return {"api_response_list": ["Error: No se encontró el contexto de la acción."]}
    function_name = actions[0].get('function')
    raw_data_str = str(state.get('api_response_list', []))
    user_query = state.get('input_user', '')  

    prompt_final = analysis_prompt(function_name, raw_data_str, user_query)
    response_text = generar_respuesta(prompt_final).strip()
    return {"api_response_list": [response_text]}


def chat_node(state: dict) -> dict:
    user_input = state['input_user']    
    prompt = """
    Eres un asistente inteligente especializado en la gestión de Google Calendar.
    Tu objetivo en esta fase es conversar de forma amable, breve y servicial con el usuario.

    Reglas:
    1. Mantén un tono profesional pero cercano.
    2. Tus respuestas deben ser concisas (máximo 2 frases salvo que sea necesario más).
    3. Si el usuario te pregunta sobre temas que no tienen nada que ver con agenda, tiempo o productividad, recuérdale amablemente que tu especialidad es el calendario.
    4. NO generes JSON ni código. Solo texto plano.
    """
    final_prompt = f"{prompt}\n\nUsuario: {user_input}"
    response = generar_respuesta(final_prompt).strip()
    return {"api_response_list": [response]}


# GRAFO
workflow = StateGraph(AgentState)
workflow.add_node("router", router_node)
workflow.add_node("tool_interpreter", tool_interpreter)
workflow.add_node("reasoning_interpreter", reasoning_interpreter)
workflow.add_node("verifier", verification_node) 
workflow.add_node("tool_executor", tool_executor)
workflow.add_node("reasoning_executor", reasoning_executor)
workflow.add_node("proposer", propose_node) 
workflow.add_node("confirmer", confirmation_node)
workflow.add_node("get_user_decision", get_user_decision)
workflow.add_node("process_user_decision", process_user_decision)
workflow.add_node("analysis", analysis_node)
workflow.add_node("chat", chat_node)



def decide_next_step(state: AgentState):
    verification = state.get("verification_result")
    if verification and verification["conflict_found"]:
        return "report_conflict"
    else:
        return "continue_execution"
    
workflow.set_entry_point("router") # nodo inicial del flujo
workflow.add_conditional_edges(
    "router",
    lambda state: state.get("routing_decision"),
    {
        "tool_use": "tool_interpreter",
        "reasoning": "reasoning_interpreter",
        "chat": "chat"
    }
)
workflow.add_edge("tool_interpreter", "verifier")
workflow.add_edge("reasoning_interpreter", "reasoning_executor")
workflow.add_conditional_edges("verifier", decide_next_step,
    {
        "report_conflict": "proposer",
        "continue_execution": "tool_executor"
    }
)
workflow.add_edge("proposer", "get_user_decision")
workflow.add_edge("get_user_decision", "process_user_decision")
workflow.add_conditional_edges("process_user_decision",
    lambda state: state.get("routing_decision"),
    {
        "execute": "tool_executor",
        "end": "confirmer",
        "invalid_choice": "get_user_decision"
    }
)
workflow.add_edge("tool_executor", "confirmer")
workflow.add_edge("reasoning_executor", "analysis")
workflow.add_edge("analysis", "confirmer") 
workflow.add_edge("chat", "confirmer") 
workflow.add_edge("confirmer", "__end__")

conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
memory = SqliteSaver(conn=conn)
atexit.register(conn.close)
app = workflow.compile(checkpointer=memory)
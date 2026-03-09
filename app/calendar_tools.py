# from app.services.calendar_service import get_calendar_service(user_id)
from app.auth import get_calendar_service
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.state import UndoableAction
import uuid
from typing import Dict, Any


LOCAL_TZ = ZoneInfo("Europe/Madrid")


def _get_friendly_datetime(start_obj):
    """Devuelve un string legible de la fecha y hora de un objeto start de Google Calendar."""
    if not start_obj:
        return ""
    if "dateTime" in start_obj:
        # Google suele enviar la TZ o Z. Ajustamos a LOCAL_TZ para mostrar al usuario.
        dt = datetime.fromisoformat(start_obj["dateTime"].replace("Z", "+00:00")).astimezone(LOCAL_TZ)
        return dt.strftime("%d/%m/%Y a las %H:%M")
    elif "date" in start_obj:
        # Formato YYYY-MM-DD
        d = datetime.strptime(start_obj["date"], "%Y-%m-%d")
        return d.strftime("%d/%m/%Y") + " (todo el día)"
    return ""


def _resolve_calendar_id(user_id: str, calendar_id: str) -> str:
    """
    Resuelve un nombre de calendario a su ID real de Google Calendar.
    Si el calendar_id ya es válido (primary o email), lo devuelve tal cual.
    Si es un nombre (ej: "trabajo"), busca en los calendarios del usuario.
    """
    if not calendar_id or calendar_id == "primary":
        return "primary"
    
    # Si ya parece un email válido (contiene @), usarlo directamente
    if "@" in calendar_id:
        return calendar_id
    
    try:
        service = get_calendar_service(user_id)
        calendars = service.calendarList().list().execute().get('items', [])
        
        # Buscar por nombre (case insensitive)
        search_name = calendar_id.lower().strip()
        for cal in calendars:
            cal_summary = cal.get('summary', '').lower()
            if search_name in cal_summary or cal_summary in search_name:
                return cal.get('id')  # Devolver el ID real
        
        # Si no se encuentra, devolver "primary" como fallback
        print(f"[calendar] No se encontró calendario '{calendar_id}', usando 'primary'")
        return "primary"
    except Exception as e:
        print(f"[calendar] Error resolviendo calendar_id: {e}")
        return "primary"


# def create_event(
#     service=svc, summary=None,
#     start_date=None, end_date=None,
#     start_time=None, end_time=None,
#     description="", colorId="7",
#     visibility="default", transparency="opaque",
#     location="", attendees=None,
#     default_reminder=True, reminder=None,
#     zone="Europe/Madrid", recurrence=None,
#     calendar_id="primary", attachments=None,
#     conference=False, source=None,
#     send_updates="none"
# ):
#     try:
#         if not start_date:
#             start_date = datetime.now(LOCAL_TZ).date().isoformat()
        
#         event = {"summary": summary}

#         # Fechas y horas
#         if end_date and start_time and end_time:
#             start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)
#             end_dt = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)
#             event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Madrid"}
#             event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Madrid"}

#         elif start_time and not end_time and not end_date:
#             inicio = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)
#             fin = inicio + timedelta(hours=1)
#             event["start"] = {"dateTime": inicio.isoformat(), "timeZone": "Europe/Madrid"}
#             event["end"] = {"dateTime": fin.isoformat(), "timeZone": "Europe/Madrid"}

#         elif end_date and not start_time and not end_time:
#             event["start"] = {"date": start_date}
#             event["end"] = {"date": end_date}

#         else:
#             end_date = (datetime.fromisoformat(start_date) + timedelta(days=1)).date().isoformat()
#             event["start"] = {"date": start_date}
#             event["end"] = {"date": end_date}

#     except ValueError:
#             return {
#                 "response": f"Error: La fecha u hora indicada no es válida.",
#                 "undo_info": None
#             }

#     # Resto igual
#     if description: event["description"] = description
#     if location: event["location"] = location
#     if colorId: event["colorId"] = str(colorId)
#     if visibility: event["visibility"] = visibility
#     if transparency: event["transparency"] = transparency
#     if recurrence: event["recurrence"] = recurrence
#     if attendees: event["attendees"] = [{"email": m} for m in attendees]
#     event["reminders"] = (
#         {"useDefault": True} if default_reminder else
#         {"useDefault": False, "overrides": reminder or []}
#     )
#     if attachments: event["attachments"] = attachments
#     if conference:
#         event["conferenceData"] = {
#             "createRequest": {
#                 "requestId": str(uuid.uuid4()),
#                 "conferenceSolutionKey": {"type": "hangoutsMeet"}
#             }
#         }
#     if source: event["source"] = source

#     params_insert = {
#         "calendarId": calendar_id,
#         "body": event,
#         "sendUpdates": send_updates
#     }
#     if conference: params_insert["conferenceDataVersion"] = 1
#     if attachments: params_insert["supportsAttachments"] = True

#     try:
#         created = service.events().insert(**params_insert).execute()
#         event_id = created['id']

#         undo_info = UndoableAction(
#             operation="create_event", 
#             calendarId=calendar_id,
#             eventId=event_id,
#             previous_body=None
#         )

#         return {
#             "response": f"Se ha creado el evento “{summary}” correctamente.",
#             "undo_info": undo_info
#         }
#     except Exception as e:
#         print(f"[create_event] Error técnico: {e}")
#         return {"response": "Lo siento, no pude crear el evento. Por favor, inténtalo de nuevo.", "undo_info": None}
    
def create_event(
    user_id: str,
    summary=None, start_date=None, end_date=None, 
    start_time=None, end_time=None, description="", colorId="7", 
    visibility="default", transparency="opaque", location="", attendees=None, 
    default_reminder=True, reminder=None, zone="Europe/Madrid", recurrence=None, 
    calendar_id="primary", attachments=None, conference=False, source=None, 
    send_updates="none"
):
    try:
        # Resolver calendar_id si es un nombre en lugar de un ID
        calendar_id = _resolve_calendar_id(user_id, calendar_id)
        
        # 1. LÓGICA DE FECHAS 
        if not start_date:
            start_date = datetime.now(LOCAL_TZ).date().isoformat()
        
        event = {"summary": summary}

        # Estandarizamos: siempre crearemos start_dt y end_dt si es posible
        if end_date and start_time and end_time:
            start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)
            end_dt = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)
            event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Madrid"}
            event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Madrid"}

        elif start_time and not end_time and not end_date:
            # CORRECCIÓN TEST 5: Usamos 'start_dt' en vez de 'inicio'
            start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)
            end_dt = start_dt + timedelta(hours=1)
            event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Madrid"}
            event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Madrid"}

        elif end_date and not start_time and not end_time:
            # Validamos formato
            datetime.fromisoformat(start_date)
            datetime.fromisoformat(end_date)
            event["start"] = {"date": start_date}
            event["end"] = {"date": end_date}

        else:
            # Validamos start_date y calculamos end_date
            dt_start = datetime.fromisoformat(start_date)
            end_date_str = (dt_start + timedelta(days=1)).date().isoformat()
            event["start"] = {"date": start_date}
            event["end"] = {"date": end_date_str}

        # 2. PARÁMETROS 
        if description: event["description"] = description
        if location: event["location"] = location
        if colorId: event["colorId"] = str(colorId)
        if visibility: event["visibility"] = visibility
        if transparency: event["transparency"] = transparency
        if recurrence: event["recurrence"] = recurrence
        if attendees: event["attendees"] = [{"email": m} for m in attendees]
        
        event["reminders"] = (
            {"useDefault": True} if default_reminder else
            {"useDefault": False, "overrides": reminder or []}
        )
        
        if attachments: event["attachments"] = attachments
        if conference:
            event["conferenceData"] = {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        if source: event["source"] = source

        params_insert = {
            "calendarId": calendar_id,
            "body": event,
            "sendUpdates": send_updates
        }
        if conference: params_insert["conferenceDataVersion"] = 1
        if attachments: params_insert["supportsAttachments"] = True

        # --- 3. EJECUCIÓN API ---
        created = get_calendar_service(user_id).events().insert(**params_insert).execute()
        
        undo_info = UndoableAction(
            operation="create_event", 
            calendarId=calendar_id, 
            eventId=created['id'], 
            previous_body=None
        )
        friendly_time = _get_friendly_datetime(created.get("start"))
        
        # Añadir info de recurrencia al mensaje si existe
        recurrence_text = ""
        if recurrence:
            recurrence_str = recurrence[0] if isinstance(recurrence, list) else str(recurrence)
            recurrence_lower = recurrence_str.lower()
            if "daily" in recurrence_lower:
                recurrence_text = " (se repite cada día)"
            elif "weekly" in recurrence_lower:
                recurrence_text = " (se repite cada semana)"
            elif "monthly" in recurrence_lower:
                recurrence_text = " (se repite cada mes)"
            elif "yearly" in recurrence_lower:
                recurrence_text = " (se repite cada año)"
            else:
                recurrence_text = " (evento periódico)"
        
        return {
            "response": f"Se ha creado el evento “{summary}” para el {friendly_time}{recurrence_text} correctamente.",
            "undo_info": undo_info
        }
    
    except Exception as e:
        error_msg = str(e)
        if "out of range" in error_msg or "match format" in error_msg:
            return{"response": "La fecha u hora indicada no es válida.", "undo_info": None}
        else:
            return {"response": f"Hubo un error técnico al crear el evento, intentalo de nuevo.", "undo_info": None}
    

def get_id(user_id: str, summary, start_date=None, end_date=None, calendar_id="primary", find_recurring_parent=False):
    try:
        user_gave_date = start_date is not None
        original_start_date = start_date  # Guardar fecha original para comparación

        if not start_date:
            start_date = datetime.now(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif len(start_date) == 10:
            # Para incluir eventos de día completo, empezar desde el inicio del día
            start_date = datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0, tzinfo=LOCAL_TZ).isoformat()

        if not end_date:
            end_date = (datetime.now(LOCAL_TZ) + timedelta(days=365)).isoformat()
        elif len(end_date) == 10:
            # Para incluir eventos de día completo, incluir el día completo (hasta el día siguiente)
            end_date = (datetime.fromisoformat(end_date) + timedelta(days=1)).replace(hour=0, minute=0, second=0, tzinfo=LOCAL_TZ).isoformat()

        events_result = get_calendar_service(user_id).events().list(
            calendarId=calendar_id,
            timeMin=start_date,
            timeMax=end_date,
            maxResults=2500,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        
        # Normalizar texto (quitar tildes y minúsculas)
        import unicodedata
        def normalize(text):
            # Quitar tildes y convertir a minúsculas
            text = unicodedata.normalize('NFD', text)
            text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
            return text.lower()
        
        summary_normalized = normalize(summary)

        # Búsqueda exacta (ignorando mayúsculas y tildes)
        for e in events:
            event_start = e["start"].get("dateTime", e["start"].get("date"))
            event_summary = normalize(e.get("summary", ""))
            if event_summary == summary_normalized:
                if user_gave_date:
                    # Comparar con la fecha original (YYYY-MM-DD)
                    if event_start[:10] == original_start_date[:10]:
                        # Si se pide el padre recurrente, devolver recurringEventId
                        if find_recurring_parent and e.get("recurringEventId"):
                            return e["recurringEventId"]
                        return e["id"]
                else:
                    # Si se pide el padre recurrente, devolver recurringEventId
                    if find_recurring_parent and e.get("recurringEventId"):
                        return e["recurringEventId"]
                    return e["id"]

    except ValueError:
        print("[get_id] Error: Se intentó buscar con una fecha inválida.")
        return None
    
    return None  




def delete_event(user_id: str, summary, start_date=None, end_date=None, calendar_id="primary"):
    event_id = get_id(user_id, summary, start_date, end_date, calendar_id)
    if not event_id:
        return {
            "response": f"No se encontró el evento “{summary}”.",
            "undo_info": None 
        }
    
    try:
        event_before_delete = get_calendar_service(user_id).events().get(
            calendarId=calendar_id, 
            eventId=event_id
        ).execute()

        get_calendar_service(user_id).events().delete(calendarId=calendar_id, eventId=event_id).execute()

        undo_info = UndoableAction(
            operation="delete_event",
            calendarId=calendar_id,
            eventId=event_id,
            previous_body=event_before_delete 
        )

        friendly_time = _get_friendly_datetime(event_before_delete.get("start"))
        return {
            "response": f"He eliminado el evento “{summary}” del {friendly_time} correctamente.",
            "undo_info": undo_info
        }
    
    except Exception as e:
        print(f"[delete_event] Error técnico: {e}")
        return {"response": "Lo siento, no pude eliminar el evento. Por favor, inténtalo de nuevo.", "undo_info": None}


def delete_date_events(user_id: str, start_date, end_date, calendar_id="primary"):
    if not end_date:
        end_date = start_date
    # Convertir fechas a formato ISO con timezone
    if len(start_date) == 10:
        start_date_iso = datetime.fromisoformat(start_date).replace(tzinfo=LOCAL_TZ).isoformat()
    else:
        start_date_iso = start_date
    
    if len(end_date) == 10:
        end_dt = datetime.fromisoformat(end_date)
        end_date_iso = end_dt.replace(hour=23, minute=59, second=59, tzinfo=LOCAL_TZ).isoformat()
    else:
        end_date_iso = end_date

    # Obtener eventos directamente de la API (no usar get_events que devuelve un dict)
    events_result = get_calendar_service(user_id).events().list(
        calendarId=calendar_id,
        timeMin=start_date_iso,
        timeMax=end_date_iso,
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    events = events_result.get("items", [])
    
    if not events:
        return {
            "response": f"No se encontró ningún evento para el periodo indicado.",
            "undo_info": None 
        }
    
    deleted_count = 0
    deleted_summaries = []
    deleted_bodies = []  # Para el undo
    
    for event in events:
        try:
            event_id = event.get("id")
            event_summary = event.get("summary", "(Sin título)")
            
            # Guardar el evento completo antes de borrarlo (para undo)
            deleted_bodies.append(event)
            
            get_calendar_service(user_id).events().delete(calendarId=calendar_id, eventId=event_id).execute()
            deleted_count += 1
            deleted_summaries.append(event_summary)
        except Exception as e:
            print(f"[delete_date_events] Error eliminando evento: {e}")
    
    if deleted_count == 0:
        return {
            "response": "No se pudo eliminar ningún evento.",
            "undo_info": None
        }
    
    # Crear undo_info con la lista de eventos eliminados
    undo_info = UndoableAction(
        operation="delete_date_events",
        calendarId=calendar_id,
        eventId="",  # No aplica para eliminación múltiple
        previous_body=None,
        previous_bodies=deleted_bodies
    )
    
    if deleted_count == 1:
        return {
            "response": f"He eliminado el evento \"{deleted_summaries[0]}\" correctamente.",
            "undo_info": undo_info 
        }
    else:
        return {
            "response": f"He eliminado {deleted_count} eventos correctamente.",
            "undo_info": undo_info 
        }

def delete_some_events(user_id: str, summary, start_date=None, end_date=None, calendar_id="primary"):
    """
    Elimina todos los eventos que coincidan con un criterio de nombre (summary).
    El filtro es case-insensitive y busca coincidencia parcial.
    """
    import unicodedata
    
    def normalize(text):
        """Quitar tildes y convertir a minúsculas"""
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text.lower()
    
    # Normalizar el summary buscado
    summary_normalized = normalize(summary)
    
    # Configurar fechas
    if not start_date:
        start_date = datetime.now(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    elif len(start_date) == 10:
        start_date = datetime.fromisoformat(start_date).replace(tzinfo=LOCAL_TZ).isoformat()
    
    if end_date and len(end_date) == 10:
        end_dt = datetime.fromisoformat(end_date)
        end_date = end_dt.replace(hour=23, minute=59, second=59, tzinfo=LOCAL_TZ).isoformat()
    elif not end_date:
        end_date = (datetime.now(LOCAL_TZ) + timedelta(days=365)).isoformat()
    
    # Obtener eventos
    events_result = get_calendar_service(user_id).events().list(
        calendarId=calendar_id,
        timeMin=start_date,
        timeMax=end_date,
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    events = events_result.get("items", [])
    
    if not events:
        return {
            "response": f"No se encontró ningún evento para el periodo indicado.",
            "undo_info": None 
        }
    
    deleted_count = 0
    deleted_summaries = []
    deleted_bodies = []  # Para el undo
    
    for event in events:
        event_id = event.get("id")
        event_summary = event.get("summary", "")
        event_summary_normalized = normalize(event_summary)
        
        # Solo eliminar si el summary coincide (búsqueda parcial, case-insensitive)
        if summary_normalized not in event_summary_normalized:
            continue
        
        if not event_id:
            continue
        
        try:
            # Guardar el evento completo antes de borrarlo (para undo)
            deleted_bodies.append(event)
            
            get_calendar_service(user_id).events().delete(calendarId=calendar_id, eventId=event_id).execute()
            deleted_count += 1
            deleted_summaries.append(event_summary)
        except Exception as e:
            print(f"[delete_some_events] Error eliminando evento: {e}")
    
    if deleted_count == 0:
        return {
            "response": f"No se encontró ningún evento que coincida con \"{summary}\".",
            "undo_info": None
        }
    
    # Crear undo_info con la lista de eventos eliminados
    undo_info = UndoableAction(
        operation="delete_date_events",
        calendarId=calendar_id,
        eventId="",  # No aplica para eliminación múltiple
        previous_body=None,
        previous_bodies=deleted_bodies
    )
    
    if deleted_count == 1:
        return {
            "response": f"He eliminado el evento \"{deleted_summaries[0]}\" correctamente.",
            "undo_info": undo_info 
        }
    else:
        return {
            "response": f"He eliminado {deleted_count} eventos que coincidían con \"{summary}\".",
            "undo_info": undo_info 
        }


def patch_some_events(user_id: str, summary, changes=None, start_date=None, end_date=None, calendar_id="primary"):
    """
    Modifica TODOS los eventos que coincidan con un criterio de nombre (summary).
    El filtro es case-insensitive y busca coincidencia parcial.
    Si detecta un evento recurrente (con recurringEventId), parchea el evento padre
    para que el cambio aplique a TODA la serie.
    """
    import unicodedata
    
    if not changes:
        return {
            "response": "Error: No se proporcionaron cambios ('changes').",
            "undo_info": None
        }
    
    def normalize(text):
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text.lower()
    
    summary_normalized = normalize(summary)
    
    # Configurar fechas
    if not start_date:
        start_date = datetime.now(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    elif len(start_date) == 10:
        start_date = datetime.fromisoformat(start_date).replace(tzinfo=LOCAL_TZ).isoformat()
    
    if end_date and len(end_date) == 10:
        end_dt = datetime.fromisoformat(end_date)
        end_date = end_dt.replace(hour=23, minute=59, second=59, tzinfo=LOCAL_TZ).isoformat()
    elif not end_date:
        end_date = (datetime.now(LOCAL_TZ) + timedelta(days=365)).isoformat()
    
    # Obtener eventos expandidos (singleEvents=True)
    events_result = get_calendar_service(user_id).events().list(
        calendarId=calendar_id,
        timeMin=start_date,
        timeMax=end_date,
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    
    events = events_result.get("items", [])
    
    if not events:
        return {
            "response": f"No se encontró ningún evento para el periodo indicado.",
            "undo_info": None 
        }
    
    patched_count = 0
    patched_summaries = []
    previous_bodies = []
    patched_parent_ids = set()  # Para no parchear el mismo padre recurrente varias veces
    
    service = get_calendar_service(user_id)
    
    for event in events:
        event_id = event.get("id")
        event_summary = event.get("summary", "")
        event_summary_normalized = normalize(event_summary)
        
        # Solo modificar si el summary coincide de forma exacta
        if summary_normalized != event_summary_normalized:
            continue
        
        if not event_id:
            continue
        
        try:
            # Si es instancia de un evento recurrente, parchear el padre
            recurring_parent_id = event.get("recurringEventId")
            if recurring_parent_id:
                if recurring_parent_id in patched_parent_ids:
                    continue  # Ya parcheamos este padre, saltar
                
                # Guardar estado anterior del padre para undo
                parent_before = service.events().get(
                    calendarId=calendar_id, eventId=recurring_parent_id
                ).execute()
                previous_bodies.append(parent_before)
                
                # Parchear el padre (aplica a todas las instancias)
                service.events().patch(
                    calendarId=calendar_id, eventId=recurring_parent_id, body=changes
                ).execute()
                
                patched_parent_ids.add(recurring_parent_id)
                patched_count += 1
                patched_summaries.append(f"{event_summary} (serie completa)")
            else:
                # Evento individual: parchear directamente
                event_before = service.events().get(
                    calendarId=calendar_id, eventId=event_id
                ).execute()
                previous_bodies.append(event_before)
                
                service.events().patch(
                    calendarId=calendar_id, eventId=event_id, body=changes
                ).execute()
                
                patched_count += 1
                patched_summaries.append(event_summary)
        except Exception as e:
            print(f"[patch_some_events] Error modificando evento: {e}")
    
    if patched_count == 0:
        return {
            "response": f"No se encontró ningún evento que coincida con \"{summary}\".",
            "undo_info": None
        }
    
    # Crear undo_info para poder deshacer
    undo_info = UndoableAction(
        operation="patch_some_events",
        calendarId=calendar_id,
        eventId="",
        previous_body=None,
        previous_bodies=previous_bodies
    )
    
    if patched_count == 1:
        return {
            "response": f"He modificado el evento \"{patched_summaries[0]}\" correctamente.",
            "undo_info": undo_info 
        }
    else:
        return {
            "response": f"He modificado {patched_count} eventos que coincidían con \"{summary}\" correctamente.",
            "undo_info": undo_info 
        }
        
        

                
                


def get_events(user_id: str, summary=None, start_date=None, end_date=None, calendar_id="primary", max=2500):
    try:
        if not start_date:
            start_date = datetime.now(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif len(start_date) == 10:
            start_date = datetime.fromisoformat(start_date).replace(tzinfo=LOCAL_TZ).isoformat()
        

        if not end_date:
            end_date = (datetime.now(LOCAL_TZ) + timedelta(days=30)).isoformat()
        elif len(end_date) == 10:
            dt_end = datetime.fromisoformat(end_date)
            end_date = dt_end.replace(hour=23, minute=59, second=59, tzinfo=LOCAL_TZ).isoformat()

    except ValueError:
        return {
            "response": f"Error: La fecha indicada no es válida.",
            "undo_info": None
        }

    query = {"calendarId": calendar_id, "timeMin": start_date, "timeMax": end_date,
             "maxResults": max, "singleEvents": True, "orderBy": "startTime"}
    if summary:
        query["q"] = summary

    events_result = get_calendar_service(user_id).events().list(**query).execute()
    events = events_result.get("items", [])

    if not events:
        text = "No se encontraron eventos para ese periodo."
    else:
        text = "Próximos eventos:\n"
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date"))
            text += f"- {start} | {e.get('summary', '(Sin título)')}\n"
        text = text.strip()

    return {
        "response": text,
        "undo_info": None
    }

    


def patch_event(user_id: str, summary, start_date=None, changes=None):
    # Determinar si los cambios son "globales" (aplican a toda la serie recurrente)
    # o específicos de una instancia (cambio de fecha/hora)
    is_global_change = changes and "start" not in changes and "end" not in changes
    
    event_id = get_id(user_id, summary, start_date, None, "primary", find_recurring_parent=is_global_change)
    if not event_id:
        return {
            "response": f"No se encontró el evento “{summary}”.",
            "undo_info": None
        }
    
    if not changes:
        return {
            "response": f"Error: No se proporcionaron cambios ('changes').",
            "undo_info": None
        }
    
    if "start" in changes and changes["start"].get("dateTime"):
        naive_dt_str = changes["start"]["dateTime"]
        try:
            # Parsear naive, asignar zona local
            aware_dt = datetime.fromisoformat(naive_dt_str).replace(tzinfo=LOCAL_TZ)
            changes["start"]["dateTime"] = aware_dt.isoformat()
            changes["start"]["timeZone"] = "Europe/Madrid"
        except (ValueError, TypeError):
            print(f"[patch_event] Error parseando start: {naive_dt_str}")
            pass # Dejar que la API falle si el formato es incorrecto

    if "end" in changes and changes["end"].get("dateTime"):
        naive_dt_str = changes["end"]["dateTime"]
        try:
            # Parsear naive, asignar zona local
            aware_dt = datetime.fromisoformat(naive_dt_str).replace(tzinfo=LOCAL_TZ)
            changes["end"]["dateTime"] = aware_dt.isoformat()
            changes["end"]["timeZone"] = "Europe/Madrid"
        except (ValueError, TypeError):
            print(f"[patch_event] Error parseando end: {naive_dt_str}")
            pass # Dejar que la API falle si el formato es incorrecto

    try:
        event_before_patch = get_calendar_service(user_id).events().get(
            calendarId="primary", 
            eventId=event_id
        ).execute()

        updated_event = get_calendar_service(user_id).events().patch(calendarId="primary", eventId=event_id, body=changes).execute()

        undo_info = UndoableAction(
            operation="patch_event", 
            calendarId="primary",
            eventId=event_id,
            previous_body=event_before_patch 
        )
        
        # Indicar si se modificó toda la serie recurrente
        is_recurring = updated_event.get("recurrence") is not None
        recurring_suffix = " (todas las repeticiones)" if is_recurring else ""
        
        friendly_time = _get_friendly_datetime(updated_event.get("start"))
        return {
            "response": f"El evento “{summary}” se ha actualizado{recurring_suffix} para el {friendly_time} correctamente.",
            "undo_info": undo_info
        }
    except Exception as e:
        error_msg = str(e)
        if "out of range" in error_msg or "match format" in error_msg:
            return{"response": "La fecha u hora indicada no es válida.", "undo_info": None}
        else:
            return {"response": f"Hubo un error técnico al modificar el evento {summary}, intentalo de nuevo.", "undo_info": None}


def duplicate_event(user_id: str, summary=None, original_date=None, new_date=None, new_time=None, calendar_id="primary"):
    try:
        if not summary or not new_date:
            return {
                "response": "Debes indicar el nombre del evento original y la nueva fecha.",
                "undo_info": None
            }

        if not original_date:
            original_date = datetime.now(LOCAL_TZ).isoformat()
        elif len(original_date) == 10:
            original_date = datetime.fromisoformat(original_date).replace(tzinfo=LOCAL_TZ).isoformat()

        eventos = get_calendar_service(user_id).events().list(
            calendarId=calendar_id,
            timeMin=original_date,
            maxResults=5,
            singleEvents=True,
            orderBy="startTime",
            q=summary
        ).execute().get("items", [])
    
    
        if not eventos:
            return {
                "response": f"No se encontró el evento “{summary}” para duplicar.",
                "undo_info": None
            }

        original = eventos[0]
        if not new_time:
            new_time = original["start"].get("dateTime", original["start"].get("date", "00:00"))[11:16]

        result_package = create_event(
            user_id=user_id,
            summary=original.get("summary", "(sin título)"),
            start_date=new_date,
            start_time=new_time,
            description=original.get("description", ""),
            location=original.get("location", ""),
            colorId=original.get("colorId", "1"),
            attendees=[a["email"] for a in original.get("attendees", [])],
            recurrence=original.get("recurrence"),
            attachments=original.get("attachments"),
            source=original.get("source"),
            calendar_id=calendar_id
        )

        if result_package.get("undo_info"):
            resp = result_package.get("response", "")
            result_package["response"] = resp.replace("Se ha creado", "He duplicado")
    
    except ValueError:
        return {
            "response": f"Error: La fecha indicada no es válida.",
            "undo_info": None
        }
        
    return result_package


# FUNCIONES DE "DESHACER"
def _clean_body_for_restore(body: Dict[str, Any]) -> Dict[str, Any]:
    if not body:
        return {}
    
    # Campos de solo lectura que la API no acepta al crear/actualizar
    read_only_fields = [
        'id', 'status', 'htmlLink', 'created', 'updated', 'creator', 
        'organizer', 'iCalUID', 'sequence', 'etag', 'eventType',
        'kind', 'recurringEventId', 'originalStartTime'
    ]
    
    clean_body = body.copy()
    for field in read_only_fields:
        clean_body.pop(field, None)
    
    # Limpiar reminders vacíos
    if 'reminders' in clean_body and 'useDefault' in clean_body['reminders']:
        if not clean_body['reminders'].get('overrides'):
             clean_body.pop('reminders')
    
    # Limpiar attendees problemáticos (a veces vienen con campos extra)
    if 'attendees' in clean_body:
        clean_attendees = []
        for attendee in clean_body.get('attendees', []):
            clean_attendees.append({'email': attendee.get('email')})
        if clean_attendees:
            clean_body['attendees'] = clean_attendees
        else:
            clean_body.pop('attendees', None)

    return clean_body


def undo_last_action(user_id: str, action_to_undo):
    """
    Deshace la(s) última(s) acción(es) ejecutadas.
    Ahora soporta tanto una acción individual como una lista de acciones.
    """
    if not action_to_undo:
        return {
            "response": "No hay ninguna acción reciente que deshacer.",
            "undo_info": None
        }
    
    # Convertir a lista si es un solo elemento (compatibilidad)
    if isinstance(action_to_undo, dict):
        actions_list = [action_to_undo]
    else:
        actions_list = list(action_to_undo)
    
    # Invertir orden: deshacer último primero
    actions_list = list(reversed(actions_list))
    
    messages = []
    total_undone = 0
    
    for action in actions_list:
        operation = action.get('operation')
        event_id = action.get('eventId')
        calendar_id = action.get('calendarId')
        
        try:
            if operation == "create_event":
                get_calendar_service(user_id).events().delete(
                    calendarId=calendar_id,
                    eventId=event_id
                ).execute()
                total_undone += 1

            elif operation == "delete_event":
                body_to_restore = _clean_body_for_restore(action.get('previous_body'))
                get_calendar_service(user_id).events().insert(
                    calendarId=calendar_id,
                    body=body_to_restore
                ).execute()
                total_undone += 1

            elif operation == "patch_event":
                body_to_restore = _clean_body_for_restore(action.get('previous_body'))
                get_calendar_service(user_id).events().update(
                    calendarId=calendar_id,
                    eventId=event_id,
                    body=body_to_restore
                ).execute()
                total_undone += 1

            elif operation == "delete_date_events":
                # Restaurar todos los eventos eliminados
                previous_bodies = action.get('previous_bodies', [])
                for body in previous_bodies:
                    try:
                        body_to_restore = _clean_body_for_restore(body)
                        get_calendar_service(user_id).events().insert(
                            calendarId=calendar_id,
                            body=body_to_restore
                        ).execute()
                        total_undone += 1
                    except Exception as e:
                        print(f"[undo_last_action] Error restaurando evento: {e}")
            elif operation == "patch_some_events":
                # Restaurar estatus anterior de todos los eventos parcheados
                previous_bodies = action.get('previous_bodies', [])
                for body in previous_bodies:
                    try:
                        body_to_restore = _clean_body_for_restore(body)
                        event_id_to_restore = body.get('id')
                        get_calendar_service(user_id).events().update(
                            calendarId=calendar_id,
                            eventId=event_id_to_restore,
                            body=body_to_restore
                        ).execute()
                        total_undone += 1
                    except Exception as e:
                        print(f"[undo_last_action] Error restaurando evento (patch_some): {e}")

        except Exception as e:
            print(f"[undo_last_action] Error técnico deshaciendo {operation}: {e}")
            messages.append(f"Error deshaciendo una acción")
    
    # Generar mensaje final
    if total_undone == 0:
        final_message = "No se pudo deshacer ninguna acción."
    elif total_undone == 1:
        final_message = "Acción deshecha correctamente."
    else:
        final_message = f"Se han deshecho {total_undone} acciones correctamente."
    
    return {
        "response": final_message,
        "undo_info": None
    }
    

def find_free_slots(user_id: str, duration=None, datetime_min=None, datetime_max=None, calendar_id="primary"):

    if not duration:
        duration = timedelta(hours=1)

    if not datetime_min:
        datetime_min = datetime.now(LOCAL_TZ).isoformat() #string "2025-11-09T13:22:59+01:00"
    
    if not datetime_max:
        datetime_max = (datetime.now(LOCAL_TZ) + timedelta(days=30)).isoformat()

    datetime_max_dt = datetime.fromisoformat(datetime_max)

    body = {
        'timeMin': datetime_min, #debe recibir string
        'timeMax': datetime_max,
        'timeZone': 'Europe/Madrid', 
        'items': [{'id': calendar_id}]
    }

    busy_periods_response = get_calendar_service(user_id).freebusy().query(body=body).execute()
    busy_slots = busy_periods_response.get('calendars', {}).get(calendar_id, {}).get('busy', [])

    if not busy_slots:
        return [{"start": datetime_min, "end": datetime_max}]
    
    else:
        current_time = datetime.fromisoformat(datetime_min)
        free_slots = []

        for busy_slot in busy_slots:
            busy_start = datetime.fromisoformat(busy_slot['start'])
            busy_end = datetime.fromisoformat(busy_slot['end'])

            gap = busy_start - current_time

            # Si el hueco empieza antes de AHORA MISMO, lo saltamos
            if current_time < datetime.now(LOCAL_TZ):
                current_time = datetime.now(LOCAL_TZ)
                                            
            if gap >= duration:
                free_slots.append({
                    "start": current_time.isoformat(),
                    "end": busy_start.isoformat()
                })


            current_time = busy_end  # mantiene el tipo datetime

        # comprobar hueco final
        if datetime_max_dt - current_time >= duration:
            free_slots.append({
                "start": current_time.isoformat(),
                "end": datetime_max_dt.isoformat()
            })

    return free_slots



def find_group_free_slots(user_id: str, people, duration=None, datetime_min=None, datetime_max=None, calendar_id="primary"):
    free_slots = []
    busy_slots = []
    
    if not duration:
        duration = timedelta(hours=1)

    if not datetime_min:
        datetime_min = datetime.now(LOCAL_TZ).isoformat()
    
    if not datetime_max:
        datetime_max = (datetime.now(LOCAL_TZ) + timedelta(days=30)).isoformat()

    datetime_max_dt = datetime.fromisoformat(datetime_max)
    
    service = get_calendar_service(user_id)
    
    # lista de calendarios a consultar
    users = [{"id": user_id}]
    for p in people:
        if p != user_id:
            users.append({"id": p})

    body = {
        'timeMin': datetime_min, 
        'timeMax': datetime_max,
        'timeZone': 'Europe/Madrid',
        'items': users
    }

    result = service.freebusy().query(body=body).execute()
    
    # Verificar errores de permiso para cada calendario
    for user in users:
        u_id = user["id"]
        calendar_data = result.get('calendars', {}).get(u_id, {})
        errors = calendar_data.get('errors', [])
                
        if errors:
            return {"response": f"El usuario {u_id} no ha compartido su disponibilidad contigo. Pídele que comparta su calendario."}
        
        # Añadir los slots ocupados de este calendario
        p_busy_slots = calendar_data.get('busy', [])
        busy_slots.extend(p_busy_slots)
    
    busy_slots.sort(key=lambda x: x['start'])

    # Fusionar slots ocupados que se solapan
    merged_busy = []
    for slot in busy_slots:
        slot_start = datetime.fromisoformat(slot['start'])
        slot_end = datetime.fromisoformat(slot['end'])
        
        if not merged_busy:
            merged_busy.append({'start': slot_start, 'end': slot_end})
        else:
            last = merged_busy[-1]
            # Si el slot actual empieza antes o justo cuando termina el último, fusionar
            if slot_start <= last['end']:
                last['end'] = max(last['end'], slot_end)
            else:
                merged_busy.append({'start': slot_start, 'end': slot_end})

    if not merged_busy:
        return [{"start": datetime_min, "end": datetime_max}]
    
    else:
        current_time = datetime.fromisoformat(datetime_min)
        free_slots = []

        for busy_slot in merged_busy:
            busy_start = busy_slot['start']
            busy_end = busy_slot['end']

            # Si el hueco empieza antes de AHORA MISMO, lo saltamos
            if current_time < datetime.now(LOCAL_TZ):
                current_time = datetime.now(LOCAL_TZ)

            gap = busy_start - current_time
                                            
            if gap >= duration:
                free_slots.append({
                    "start": current_time.isoformat(),
                    "end": busy_start.isoformat()
                })

            # Avanzar al final del slot ocupado (solo si es mayor que current_time)
            if busy_end > current_time:
                current_time = busy_end

        # comprobar hueco final
        if datetime_max_dt - current_time >= duration:
            free_slots.append({
                "start": current_time.isoformat(),
                "end": datetime_max_dt.isoformat()
            })

    return free_slots


def get_events_for_analytics(user_id: str):
    """
    Obtiene los eventos CRUDOS (JSON) de los próximos días.
    """
    try:
        service = get_calendar_service(user_id)
        
        # 2. Calculamos fechas (Desde AHORA hasta FUTURO)
        start = datetime.now(LOCAL_TZ).isoformat() 
        end = (datetime.now(LOCAL_TZ) + timedelta(days=7)).isoformat()
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start,          
            timeMax=end,   
            maxResults=2500,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
        
    except Exception as e:
        print(f"Error obteniendo eventos para analytics: {e}")
        return []
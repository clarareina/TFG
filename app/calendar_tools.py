from app.services.calendar_service import get_service
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.state import UndoableAction
import uuid
from typing import Dict, Any

svc = get_service()

LOCAL_TZ = ZoneInfo("Europe/Madrid")

def create_event(
    service=svc, summary=None,
    start_date=None, end_date=None,
    start_time=None, end_time=None,
    description="", colorId="7",
    visibility="default", transparency="opaque",
    location="", attendees=None,
    default_reminder=True, reminder=None,
    zone="Europe/Madrid", recurrence=None,
    calendar_id="primary", attachments=None,
    conference=False, source=None,
    send_updates="none"
):
    if not start_date:
        start_date = datetime.now(LOCAL_TZ).date().isoformat()
    
    event = {"summary": summary}

    # Fechas y horas
    if end_date and start_time and end_time:
        start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)
        end_dt = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)
        event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Madrid"}
        event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Madrid"}

    elif start_time and not end_time and not end_date:
        inicio = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ)
        fin = inicio + timedelta(hours=1)
        event["start"] = {"dateTime": inicio.isoformat(), "timeZone": "Europe/Madrid"}
        event["end"] = {"dateTime": fin.isoformat(), "timeZone": "Europe/Madrid"}

    elif end_date and not start_time and not end_time:
        event["start"] = {"date": start_date}
        event["end"] = {"date": end_date}

    else:
        end_date = (datetime.fromisoformat(start_date) + timedelta(days=1)).date().isoformat()
        event["start"] = {"date": start_date}
        event["end"] = {"date": end_date}

    # Resto igual
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

    try:
        created = service.events().insert(**params_insert).execute()
        event_id = created['id']

        undo_info = UndoableAction(
            operation="create_event", 
            calendarId=calendar_id,
            eventId=event_id,
            previous_body=None
        )

        return {
            "response": f"Se ha creado el evento “{summary}” correctamente.",
            "undo_info": undo_info
        }
    except Exception as e:
        print(f"[create_event] Error técnico: {e}")
        return {"response": "Lo siento, no pude crear el evento. Por favor, inténtalo de nuevo.", "undo_info": None}




def get_id(summary, start_date=None, end_date=None, calendar_id="primary", service=svc):
    user_gave_date = start_date is not None

    if not start_date:
        start_date = datetime.now(LOCAL_TZ).isoformat()
    elif len(start_date) == 10:
        start_date = datetime.fromisoformat(start_date).replace(tzinfo=LOCAL_TZ).isoformat()

    if not end_date:
        end_date = (datetime.now(LOCAL_TZ) + timedelta(days=365)).isoformat()
    elif len(end_date) == 10:
        end_date = datetime.fromisoformat(end_date).replace(tzinfo=LOCAL_TZ).isoformat()

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_date,
        timeMax=end_date,
        maxResults=2500,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])

    for e in events:
        event_start = e["start"].get("dateTime", e["start"].get("date"))
        if e.get("summary", "").lower() == summary.lower():
            if user_gave_date:
                if event_start[:10] == start_date[:10]:
                    return e["id"]
            else:
                return e["id"]

    return None  




def delete_event(summary, start_date=None, end_date=None, calendar_id="primary", service=svc):
    event_id = get_id(summary, start_date, end_date, calendar_id, service)
    if not event_id:
        return {
            "response": f"No se encontró el evento “{summary}”.",
            "undo_info": None 
        }
    
    try:
        event_before_delete = service.events().get(
            calendarId=calendar_id, 
            eventId=event_id
        ).execute()

        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

        undo_info = UndoableAction(
            operation="delete_event",
            calendarId=calendar_id,
            eventId=event_id,
            previous_body=event_before_delete 
        )

        return {
            "response": f"He eliminado el evento “{summary}” correctamente.",
            "undo_info": undo_info
        }
    
    except Exception as e:
        print(f"[delete_event] Error técnico: {e}")
        return {"response": "Lo siento, no pude eliminar el evento. Por favor, inténtalo de nuevo.", "undo_info": None}


def delete_date_events(start_date, end_date, calendar_id="primary", service=svc):
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
    events_result = service.events().list(
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
            
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
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


def get_events(summary=None, start_date=None, end_date=None, calendar_id="primary", service=svc, max=2500):
    if not start_date:
        start_date = datetime.now(LOCAL_TZ).isoformat()
    elif len(start_date) == 10:
        start_date = datetime.fromisoformat(start_date).replace(tzinfo=LOCAL_TZ).isoformat()
    

    if not end_date:
        end_date = (datetime.now(LOCAL_TZ) + timedelta(days=30)).isoformat()
    elif len(end_date) == 10:
        dt_end = datetime.fromisoformat(end_date)
        end_date = dt_end.replace(hour=23, minute=59, second=59, tzinfo=LOCAL_TZ).isoformat()
        

    query = {"calendarId": calendar_id, "timeMin": start_date, "timeMax": end_date,
             "maxResults": max, "singleEvents": True, "orderBy": "startTime"}
    if summary:
        query["q"] = summary

    events_result = service.events().list(**query).execute()
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



def patch_event(summary, start_date=None, changes=None, service=svc):
    event_id = get_id(summary, start_date, None, "primary", service)
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
        event_before_patch = service.events().get(
            calendarId="primary", 
            eventId=event_id
        ).execute()

        svc.events().patch(calendarId="primary", eventId=event_id, body=changes).execute()

        undo_info = UndoableAction(
            operation="patch_event", 
            calendarId="primary",
            eventId=event_id,
            previous_body=event_before_patch 
        )
        
        return {
            "response": f"El evento “{summary}” se actualizó correctamente.",
            "undo_info": undo_info
        }
    except Exception as e:
        print(f"[patch_event] Error técnico: {e}")
        return {"response": "Lo siento, no pude actualizar el evento. Por favor, inténtalo de nuevo.", "undo_info": None}



def duplicate_event(service=svc, summary=None, original_date=None, new_date=None, new_time=None, calendar_id="primary"):
    if not summary or not new_date:
        return {
            "response": "Debes indicar el nombre del evento original y la nueva fecha.",
            "undo_info": None
        }

    if not original_date:
        original_date = datetime.now(LOCAL_TZ).isoformat()

    eventos = service.events().list(
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
        service=service,
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
        result_package["response"] = f"He duplicado el evento “{summary}” correctamente en la fecha {new_date}."
    
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


def undo_last_action(action_to_undo: UndoableAction, service=svc):
    if not action_to_undo:
        return {
            "response": "No hay ninguna acción reciente que deshacer.",
            "undo_info": None
        }

    operation = action_to_undo['operation'] 
    event_id = action_to_undo['eventId']
    calendar_id = action_to_undo['calendarId']

    try:    
        if operation == "create_event": 
            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            message = "Acción deshecha: El evento que se creó ha sido eliminado."

        elif operation == "delete_event":
            body_to_restore = _clean_body_for_restore(action_to_undo['previous_body'])
            service.events().insert(
                calendarId=calendar_id,
                body=body_to_restore
            ).execute()
            summary = body_to_restore.get('summary', event_id)
            message = f"Acción deshecha: El evento '{summary}' ha sido restaurado."

        elif operation == "patch_event":
            body_to_restore = _clean_body_for_restore(action_to_undo['previous_body'])
            service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=body_to_restore
            ).execute()
            summary = body_to_restore.get('summary', event_id)
            message = f"Acción deshecha: El evento '{summary}' ha vuelto a su estado anterior."

        elif operation == "delete_date_events":
            # Restaurar todos los eventos eliminados
            previous_bodies = action_to_undo.get('previous_bodies', [])
            restored_count = 0
            for body in previous_bodies:
                try:
                    body_to_restore = _clean_body_for_restore(body)
                    service.events().insert(
                        calendarId=calendar_id,
                        body=body_to_restore
                    ).execute()
                    restored_count += 1
                except Exception as e:
                    print(f"[undo_last_action] Error restaurando evento: {e}")
            
            if restored_count == 1:
                message = "Acción deshecha: Se ha restaurado 1 evento."
            else:
                message = f"Acción deshecha: Se han restaurado {restored_count} eventos."

        else:
            message = f"Operación de undo no reconocida: {operation}"

        return {
            "response": message,
            "undo_info": None 
        }

    except Exception as e:
        print(f"[undo_last_action] Error técnico: {e}")
        return {
            "response": "Lo siento, no pude deshacer la acción. Es posible que el evento ya haya sido modificado.",
            "undo_info": action_to_undo 
        }
    

def find_free_slots(duration=None, datetime_min=None, datetime_max=None, service=svc, calendar_id="primary"):

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

    busy_periods_response = service.freebusy().query(body=body).execute()
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



def get_events_json():
    """
    Obtiene TODOS los eventos (pasados y futuros) para el Frontend.
    """
    try:
        service = get_service()
        past_date = (datetime.now(LOCAL_TZ) - timedelta(days=365)).isoformat()
        
        events_result = service.events().list(
            calendarId='primary', 
            
            timeMin=past_date, # Pedimos desde hace 1 año
            maxResults=2500,   
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
    except Exception as e:
        print(f"Error obteniendo JSON: {e}")
        return []
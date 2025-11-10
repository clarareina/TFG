from calendar_service import get_service
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from state import UndoableAction
import uuid
from typing import Dict, Any

# Servicio autenticado
svc = get_service()

# Zona horaria fija (España)
LOCAL_TZ = ZoneInfo("Europe/Madrid")

# ----------------------------------------------------------------------
# CREATE EVENT (FIJO EN EUROPE/MADRID)
# ----------------------------------------------------------------------
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
        return {"response": f"Error al crear: {e}", "undo_info": None}


# ----------------------------------------------------------------------
# GET ID 
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
# DELETE EVENT 
# ----------------------------------------------------------------------
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
        return {"response": f"Error al eliminar: {e}", "undo_info": None}


# ----------------------------------------------------------------------
# GET EVENTS 
# ----------------------------------------------------------------------
def get_events(summary=None, start_date=None, end_date=None, calendar_id="primary", service=svc, max=2500):
    if not start_date:
        start_date = datetime.now(LOCAL_TZ).isoformat()
    elif len(start_date) == 10:
        start_date = datetime.fromisoformat(start_date).replace(tzinfo=LOCAL_TZ).isoformat()

    if not end_date:
        end_date = (datetime.now(LOCAL_TZ) + timedelta(days=30)).isoformat()
    elif len(end_date) == 10:
        end_date = datetime.fromisoformat(end_date).replace(tzinfo=LOCAL_TZ).isoformat()
        
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


# ----------------------------------------------------------------------
# PATCH EVENT 
# ----------------------------------------------------------------------
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

    # --- INICIO CORRECCIÓN DE ZONA HORARIA ---
    # Asignar zona horaria local a los 'dateTime' "naive" que vienen de Gemini
    
    # Revisar 'start'
    if "start" in changes and changes["start"].get("dateTime"):
        naive_dt_str = changes["start"]["dateTime"]
        try:
            # Parsear naive, asignar zona local
            aware_dt = datetime.fromisoformat(naive_dt_str).replace(tzinfo=LOCAL_TZ)
            # Actualizar 'changes' con el string ISO completo Y el timeZone
            changes["start"]["dateTime"] = aware_dt.isoformat()
            changes["start"]["timeZone"] = "Europe/Madrid"
        except (ValueError, TypeError):
            print(f"[patch_event] Error parseando start: {naive_dt_str}")
            pass # Dejar que la API falle si el formato es incorrecto

    # Revisar 'end'
    if "end" in changes and changes["end"].get("dateTime"):
        naive_dt_str = changes["end"]["dateTime"]
        try:
            # Parsear naive, asignar zona local
            aware_dt = datetime.fromisoformat(naive_dt_str).replace(tzinfo=LOCAL_TZ)
            # Actualizar 'changes' con el string ISO completo Y el timeZone
            changes["end"]["dateTime"] = aware_dt.isoformat()
            changes["end"]["timeZone"] = "Europe/Madrid"
        except (ValueError, TypeError):
            print(f"[patch_event] Error parseando end: {naive_dt_str}")
            pass # Dejar que la API falle si el formato es incorrecto
    # --- FIN CORRECCIÓN DE ZONA HORARIA ---

    try:
        event_before_patch = service.events().get(
            calendarId="primary", 
            eventId=event_id
        ).execute()

        # 'changes' ahora tiene la zona horaria correcta
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
        return {"response": f"Error al actualizar: {e}", "undo_info": None}


# ----------------------------------------------------------------------
# DUPLICATE EVENT 
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
# FUNCIONES DE "DESHACER"
# ----------------------------------------------------------------------
def _clean_body_for_restore(body: Dict[str, Any]) -> Dict[str, Any]:
    if not body:
        return {}
    
    read_only_fields = [
        'id', 'status', 'htmlLink', 'created', 'updated', 'creator', 
        'organizer', 'iCalUID', 'sequence', 'etag', 'eventType'
    ]
    
    clean_body = body.copy()
    for field in read_only_fields:
        clean_body.pop(field, None)
    
    if 'reminders' in clean_body and 'useDefault' in clean_body['reminders']:
        if not clean_body['reminders'].get('overrides'):
             clean_body.pop('reminders')

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

        return {
            "response": message,
            "undo_info": None 
        }

    except Exception as e:
        return {
            "response": f"Error al intentar deshacer la acción: {e}",
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
        return [(datetime_min, datetime_max)]
    
    else:
        current_time = datetime.fromisoformat(datetime_min)
        free_slots = []

        for busy_slot in busy_slots:
            busy_start = datetime.fromisoformat(busy_slot['start'])
            busy_end = datetime.fromisoformat(busy_slot['end'])

            gap = busy_start - current_time

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

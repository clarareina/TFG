from calendar_service import get_service

from datetime import datetime, timedelta, timezone
from dateutil import tz
import uuid

# Obtenemos el servicio autenticado
svc = get_service()


#CREATE EVENT ------------------------------------------------------------
def create_event(
    service = svc, name = None,
    start_date = None,
    end_date = None, start_time=None, end_time=None,
    description="",
    color_id="7",                 # Azul
    visibility="default",         # "default" | "public" | "private"
    transparency="opaque",        # "opaque" (ocupa) | "transparent" (no bloquea)
    location="",
    attendees=None,                  # lista de emails
    default_reminder = True,
    reminder=None,                # lista de dicts [{"method":"popup","minutes":10}]
    zone="Europe/Madrid",
    recurrence=None,              # lista de strings tipo ["RRULE:..."]
    calendar_id="primary",
    attachments=None,             # lista de dicts [{"fileUrl":"...","title":"..."}]
    conference = False,            
    source=None,                  # dict {"url":"...","title":"..."}
    send_updates="none"           # "none" | "all" | "externalOnly"

):
      
    if not start_date: start_date = datetime.now().date().isoformat()
    
    event = {"summary": name}

    #----------CAMPOS DE FECHA Y HORA----------

    #si dice fecha y hora inicio y fin
    if end_date and start_time and end_time:
        start_dt = f"{start_date}T{start_time}:00"
        end_dt   = f"{end_date}T{end_time}:00"
        event["start"] = {"dateTime": start_dt, "timeZone": zone}
        event["end"]   = {"dateTime": end_dt,   "timeZone": zone}

    #si dice fecha y hora inicio (sin fin) -> 1h por defecto
    elif start_time and not end_time and not end_date:
        # Construir datetime con fecha y hora de inicio
        inicio = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        fin = inicio + timedelta(hours=1)

        # Convertir a string ISO para Calendar
        start_dt = inicio.isoformat()
        end_dt   = fin.isoformat()

        event["start"] = {"dateTime": start_dt, "timeZone": zone}
        event["end"]   = {"dateTime": end_dt,   "timeZone": zone}


    #si dice fecha inicio y fin sin hora (varios dia completo)
    elif end_date and not start_time and not end_time:
        event["start"] = {"date": start_date}
        event["end"]   = {"date": end_date}

    #si dice fecha inicio sin hora (1 dia completo)
    else:
        end_date = (datetime.fromisoformat(start_date) + timedelta(days=1)).date().isoformat()
        event["start"] = {"date": start_date}
        event["end"]   = {"date": end_date}


    #----------CAMPOS DE CONTENIDO----------

    if description: event["description"] = description
    if location:   event["location"]    = location
    if color_id:    event["colorId"]     = str(color_id)    
    if visibility: event["visibility"]  = visibility      
    if transparency: event["transparency"] = transparency


    #--------------------
    if recurrence: event["recurrence"] = recurrence   # Ejemplo: ["RRULE:FREQ=WEEKLY;BYDAY=MO", "EXDATE:20251006T100000Z"]

    if attendees: event["attendees"] = [{"email": m} for m in attendees]

    if default_reminder:
        event["reminders"] = {"useDefault": True}
    else:
        event["reminders"] = {
            "useDefault": False,
            "overrides": reminder or []  # [{"method":"popup","minutes":10}, {"method":"email","minutes":1440}]
        }
    
    if attachments: event["attachments"] = attachments

    if conference: event["conferenceData"] = {
            "createRequest": {
                "requestId": str(uuid.uuid4()),              # id único por petición
                "conferenceSolutionKey": {"type": "hangoutsMeet"}
            }
        }
    
    if source: event["source"] = source

# ---------- 9) Llamada a la API ----------
    # Param extras: sendUpdates (emails a invitados) y supportsAttachments
    params_insert = {
        "calendarId": calendar_id,
        "body": event
    }
    if conference:
        params_insert["conferenceDataVersion"] = 1
    if attachments:
        params_insert["supportsAttachments"] = True
    # Envío de correos a invitados
    params_insert["sendUpdates"] = send_updates  # "none" (por defecto), "all", "externalOnly"

    created = service.events().insert(**params_insert).execute()

    print("✅ Evento creado:", created.get("htmlLink"))
    if created.get("hangoutLink"):
        print("🔗 Meet:", created["hangoutLink"])
    print("🆔 ID:", created["id"])
    return created



#GET ID ------------------------------------------------------------
def get_id(name, start_date = None, end_date = None, calendar_id = "primary", service = svc):
    user_gave_date = start_date is not None  # <--- Flag
    print('gave date: ', user_gave_date)

    if not start_date:
        start_date = datetime.now(timezone.utc).isoformat()
    else:
        # Si el usuario pasa 'YYYY-MM-DD', convertir a ISO completo
        if len(start_date) == 10:
            start_date = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc).isoformat()

    if not end_date:
        end_date = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    else:
        if len(end_date) == 10:
            end_date = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc).isoformat()

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

        # Coincide el nombre del evento
        if e["summary"].lower() == name.lower():
            if user_gave_date:  # usuario pasó fecha explícita
                if event_start[:10] == start_date[:10]:
                    return e["id"]
            else:  # no pasó fecha → basta con nombre
                return e["id"]
    print("No se encontró el evento")


#DELETE EVENT ------------------------------------------------------------
def delete_event(name, start_date = None, end_date = None, 
                    calendar_id = "primary", service = svc):

    event_id = get_id(name, start_date, end_date, calendar_id, service)
    if event_id:
        svc.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()

        return "Evento eliminado ✅"
    else:
        return None
    


#GET EVENTS ------------------------------------------------------------
def get_events(name =  None,
        start_date = None, end_date = None, calendar_id = "primary",
        service = svc, max = 2500
):
    #por defecto una semana
    if not start_date: start_date = datetime.now(timezone.utc).isoformat()
    if not end_date: end_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    
    #busqueda por nombre
    if name:
         events_result = svc.events().list(
        calendarId=calendar_id,
        timeMin=start_date,
        timeMax=end_date,
        q=name,
        maxResults = max,
        singleEvents=True,
        orderBy='startTime'
        ).execute()
         
    else:   
        events_result = svc.events().list(
            calendarId=calendar_id,
            timeMin=start_date,
            timeMax=end_date,
            maxResults = max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
    
    events = events_result.get('items', [])

    if not events:
        print("No se encontraron próximos eventos.")
    else:
        print("Próximos eventos:")
        for e in events:
            start = e['start'].get('dateTime', e['start'].get('date'))  # puede ser con hora o todo el día
            print(f"- {start} | {e['summary']} | id={e['id']}")
    return events



#PATCH EVENT ------------------------------------------------------------
def patch_event(name, start_date = None, changes = None, service = svc):
    # changes puede ser {"summary": "nuevo título", "description": "texto"}
    # o {"start": {...}, "end": {...}}

    #Modificar un evento con PATCH
    event_id = get_id(name, start_date, end_date = None, calendar_id = "primary", service = svc)
    if not event_id:
        return None

    # Cambiamos título, descripción y ubicación de una sola vez
    patched_event = svc.events().patch(
        calendarId='primary',
        eventId=event_id,
        body=changes
    ).execute()

    print("Evento actualizado con PATCH ✅:",
           patched_event.get('htmlLink'))
    



#DUPLICATE EVENT ------------------------------------------------------------
def duplicate_event(
    service=svc,
    name=None,
    original_date=None,
    new_date=None,
    new_time=None,
    calendar_id="primary"
):
    if not name or not new_date:
        print("Debes indicar el nombre del evento original y la nueva fecha")
        return None

    # Normalizar original_date a ISO, si no dice fecha bussca el evento desde la fecha actual
    if not original_date:
        original_date = datetime.now(timezone.utc).isoformat()

    # Buscar evento original
    eventos = get_events(name=name, start_date=original_date,
                          calendar_id=calendar_id, service=service)

    if not eventos:
        print("No se encontró el evento para duplicar")
        return None

    original = eventos[0]
    if not new_time: 
        new_time = original["start"].get("dateTime", original["start"]
                                         .get("date", "00:00"))[11:16]


    # Crear el duplicado copiando directamente los datos
    nuevo = create_event(
        service=service,
        name=original.get("summary", "(sin título)"),
        start_date=new_date,
        start_time=new_time,
        description=original.get("description", ""),
        location=original.get("location", ""),
        color_id=original.get("colorId", "1"),
        attendees=[a["email"] for a in original.get("attendees", [])],
        recurrence=original.get("recurrence"),
        attachments=original.get("attachments"),
        source=original.get("source"),
        calendar_id=calendar_id
    )

    print(f"Evento duplicado: {nuevo.get('htmlLink')}")
    return nuevo

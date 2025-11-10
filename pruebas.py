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

def find_free_slots(datetime_min=None, datetime_max=None, service=svc, calendar_id="primary"):

    if not datetime_min:
        datetime_min = datetime.now(LOCAL_TZ).isoformat()
    
    if not datetime_max:
        datetime_max = (datetime.now(LOCAL_TZ) + timedelta(days=30)).isoformat()

    body = {
    'timeMin': datetime_min,
    'timeMax': datetime_max,
    'timeZone': 'Europe/Madrid', 
    'items': [{'id': calendar_id}]
    }

    busy_periods_response = service.freebusy().query(body=body).execute() #llamada a la api freebusy
    print(busy_periods_response)

    
    return None

find_free_slots()
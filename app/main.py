from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from .auth import get_calendar_service, startup_check_all_sessions
from .database import init_db
from .flow import run_agent
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/Madrid")


# 1. LIFESPAN (Ciclo de vida)
# Se asegura de crear la base de datos antes de que la API acepte peticiones.
@asynccontextmanager
async def lifespan(app: FastAPI): # Define la función del ciclo de vida
    # FASE DE ARRANQUE (Antes de abrir) 
    init_db()  #Crea la base de datos y tablas AHORA, antes de que entre nadie
    startup_check_all_sessions()    
    # FASE DE FUNCIONAMIENTO (Abierta) 
    yield  # PAUSA: La app se queda aquí "congelada" atendiendo peticiones mientras esté encendida


app = FastAPI(
    title="TFG CLARA",
    description="Backend del Agente con Auth OAuth2 y Base de Datos",
    version="2.0.0",
    lifespan=lifespan 
)

# 2. CONFIGURACIÓN CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. LOGS 
def registrar_log(user: str, pregunta: str, respuesta: str):
    """Guarda la interacción en logs.json para análisis posterior."""
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user,
        "input": pregunta,
        "output": str(respuesta)
    }
    with open("logs.json", "a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(log_data, ensure_ascii=False) + "\n")

# 4. MODELOS DE DATOS 
class UserRequest(BaseModel):
    query: str
    user_id: str


class AgentResponse(BaseModel):
    status: str
    response: str
    suggested_slots: Optional[list] = None

# 5. ENDPOINTS 
@app.get("/")
def check():
    return {"status": "online", "system": "Agent Backend v2"}

@app.get("/api/auth/login")
def login(user_id: str = Query(..., description="Email del usuario para autenticar")):
    """
    Endpoint para inicializar la sesión.
    Si el usuario no está en la BD, abrirá el navegador en el servidor (flujo local).
    Si ya está, devuelve OK inmediatamente.
    """
    try:
        # Llama a toda la lógica de auth.py (DB check -> Refresh -> Login)
        service = get_calendar_service(user_id)
        return {"status": "success", "message": f"Sesión activa para {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=AgentResponse)
async def chat_endpoint(request: UserRequest):
    """
    Recibe instrucción, verifica credenciales internamente en el agente y ejecuta.
    """
    try:
        agent_result = run_agent(request.query, request.user_id) 
        registrar_log(request.user_id, request.query, agent_result)

        result = (
            agent_result.get("response") or 
            agent_result.get("message") or 
            agent_result.get("messages") or 
            "Sin respuesta."
        )

        return AgentResponse(
            status=agent_result.get("status", "complete"),
            response=str(result)
        )
        

    except Exception as e:
        print(f"[API Error] {e}")
        return AgentResponse(
            status="error",
            response="Lo siento, ha ocurrido un problema al procesar tu solicitud. Por favor, inténtalo de nuevo."
        )

@app.get("/api/calendar/events")
async def api_get_events(user_id: str = Query(..., description="Email del usuario")):
    """
    Obtiene los eventos REALES usando el token guardado en la base de datos.
    """
    if not user_id:
        return [] # Devolvemos lista vacía y "limpia"

    try:
        # 1. Recuperamos el servicio autenticado desde la BD
        service = get_calendar_service(user_id)
        past_date = (datetime.now(LOCAL_TZ) - timedelta(days=365)).isoformat()

        # 2. Hacemos la petición a Google Calendar
        events_result = service.events().list(
            calendarId='primary',
            timeMin=past_date, # Pedimos desde hace 1 año
            maxResults=2500, singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Error de autenticación o conexión: {str(e)}")
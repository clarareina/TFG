from app.calendar_tools import get_events_json 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware  
import json                 
from datetime import datetime 

from .flow import run_agent

app = FastAPI(
    title="TFG",
    description="Backend",
    version="1.0.0"
)


# LOGS 
def registrar_log(usuario: str, pregunta: str, respuesta: str):
    """
    Guarda la interacción en un archivo de texto (logs.json).
    """
    # Datos en un diccionario
    log_data = {
        "timestamp": datetime.now().isoformat(), 
        "user_id": usuario,                      
        "input": pregunta,                       
        "output": str(respuesta)                 
    }
    
    # 'w', borraría el archivo cada vez. 'a' añade al final.
    with open("logs.json", "a", encoding="utf-8") as archivo:
        # ensure_ascii=False permite guardar tildes y ñ correctamente
        archivo.write(json.dumps(log_data, ensure_ascii=False) + "\n")



# CONFIGURACIÓN DE CORS (Permisos de acceso)
# Para hablar con el servidor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # dejar pasar a todos
    allow_credentials=True,
    allow_methods=["*"], # Permitir todos los métodos (GET, POST...)
    allow_headers=["*"],
)

# Modelos de Datos
class UserRequest(BaseModel):
    query: str
    user_id: Optional[str] = "default_user"  # Para futura memoria por usuario

class AgentResponse(BaseModel):
    status: str
    response: str


# Endpoints (Rutas)
@app.get("/")
def check():
    """
    Endpoint de diagnóstico para verificar que el servidor está activo.
    """
    return {"status": "online", "service": "Agent Backend"}

@app.post("/api/chat", response_model=AgentResponse)
# async para que el servidor sea multitarea y no se quede congelado esperando, si tarda 10s en pensar para el Usuario A, aprovecha ese tiempo para atender al Usuario B.
async def chat_endpoint(request: UserRequest):
    """
    Recibe una instrucción en lenguaje natural, invoca al agente
    y ejecuta acciones en Google Calendar.
    """
    try:
        agent_result = run_agent(request.query)
        
        registrar_log(request.user_id, request.query, agent_result) 

        return AgentResponse(
            status="success",
            response=str(agent_result)
        )

    except Exception as e:
        print(f"[API] Error técnico: {e}")
        return AgentResponse(
            status="error",
            response="Lo siento, ha ocurrido un problema al procesar tu solicitud. Por favor, inténtalo de nuevo."
        )
    

@app.get("/api/calendar/events")
async def api_get_events():
    events = get_events_json()
    return events
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from app.auth import get_calendar_service, startup_check_all_sessions
from app.database import init_db
from app.flow import run_agent
from zoneinfo import ZoneInfo

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

LOCAL_TZ = ZoneInfo("Europe/Madrid")

# 1. LIFESPAN (Ciclo de vida)
@asynccontextmanager
async def lifespan(app: FastAPI): 
    init_db()   # Crea el archivo de base de datos si no existe.    
    startup_check_all_sessions()  # Revisa si los tokens guardados siguen vivos y los refresca.
    yield 


app = FastAPI(
    title="TFG CLARA",
    description="Backend del Agente con Auth OAuth2 y Base de Datos",
    version="2.0.0",
    lifespan=lifespan 
)

# 2. CONFIGURACIÓN CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Acepta peticiones desde cualquier sitio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # 3. LOGS 
# def registrar_log(user: str, pregunta: str, respuesta: str):
#     """Guarda lo que pasa en un archivo de texto para que puedas revisarlo luego."""
#     log_data = {
#         "timestamp": datetime.now().isoformat(),
#         "user_id": user,
#         "input": pregunta,
#         "output": str(respuesta)
#     }
#     with open("logs.json", "a", encoding="utf-8") as archivo:
#         archivo.write(json.dumps(log_data, ensure_ascii=False) + "\n")

# 4. MODELOS DE DATOS (Esquemas)
class UserRequest(BaseModel):
    query: str
    user_id: str

class AgentResponse(BaseModel):
    status: str
    response: str
    suggested_slots: Optional[list] = None


# 5. ENDPOINTS 
# @app.get("/")
# def check():
#     """Para saber si el servidor está encendido."""
#     return {"status": "online", "system": "Agent Backend v2"}

@app.get("/api/auth/url")
def get_login_url(redirect_uri: str = Query(..., description="URL donde volverá Google"), login_hint: str = Query(None, description="Email sugerido")):
    """
    Paso 1 del Login:
    Genera el enlace largo de Google para que el usuario acepte permisos.
    """
    from .auth import get_auth_url
    url = get_auth_url(redirect_uri, login_hint)
    return {"url": url}

class CallbackRequest(BaseModel):
    code: str
    redirect_uri: str

@app.post("/api/auth/callback")
def auth_callback(req: CallbackRequest):
    """
    Paso 2 del Login:
    Recibe el código temporal de Google y lo cambia por el token
    """
    from .auth import exchange_code
    try:
        user_email = exchange_code(req.code, req.redirect_uri)
        return {"status": "success", "user_id": user_email}
    except Exception as e:
        print(f"[Auth Error] {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/auth/login")
def login(user_id: str = Query(..., description="Email del usuario")):
    """
    Verificador de sesión:
    Comprueba si ya tenemos un token válido guardado para no pedir login otra vez.
    """
    try:
        get_calendar_service(user_id) # Si esto funciona, el token es bueno.
        return {"status": "success", "message": "Sesión activa"}
    except Exception:
        return {"status": "error", "message": "Requiere login"}

@app.post("/api/reset")
def reset_user_conversation(user_id: str = Query(..., description="Email del usuario")):
    """
    Resetea el estado de la conversación del usuario.
    Útil cuando el agente se queda pillado esperando una respuesta.
    """
    import sqlite3
    try:
        thread_id = f"conversation_{user_id}"
        conn = sqlite3.connect("checkpoints.db")
        cursor = conn.cursor()
        # Eliminar checkpoints de este usuario
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        # También eliminar writes si existe la tabla
        try:
            cursor.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        except:
            pass
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Conversación reseteada. Puedes empezar de nuevo."}
    except Exception as e:
        print(f"[Reset Error] {e}")
        return {"status": "error", "message": "No se pudo resetear la conversación."}

@app.post("/api/chat", response_model=AgentResponse)
async def chat_endpoint(request: UserRequest):
    """
    1. Recibe el texto del usuario.
    2. Se lo pasa al Agente.
    3. Devuelve la respuesta o pide más información.
    """
    try:
        # Ejecuta la lógica inteligente (flow.py)
        agent_result = run_agent(request.query, request.user_id) 
        
        # Protección contra resultado None
        if agent_result is None:
            return AgentResponse(
                status="error",
                response="No se pudo procesar la solicitud. Inténtalo de nuevo."
            )
        
        # Guarda la conversación en un archivo
        # registrar_log(request.user_id, request.query, agent_result)

        # Limpia la respuesta para enviarla al frontend
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
        return AgentResponse(
            status="error",
            response="Lo siento, ha ocurrido un problema, intentalo de nuevo."
        )

@app.get("/api/calendar/events")
async def api_get_events(user_id: str = Query(..., description="Email del usuario")):
    """
    CALENDARIO:
    Obtiene los eventos directamente de Google.
    Se usa para 'pintar' la agenda en la pantalla, sin pasar por la IA.
    """
    if not user_id:
        return []

    try:
        service = get_calendar_service(user_id)
        past_date = (datetime.now(LOCAL_TZ) - timedelta(days=365)).isoformat()  # Fecha desde hace 1 año

        events_result = service.events().list(
            calendarId='primary',
            timeMin=past_date,
            maxResults=2500, singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Error auth: {str(e)}")


@app.get("/api/recommendations")
async def get_recommendations(user_id: str = Query(..., description="Email del usuario")):
    """
    RECOMENDADOR:
    Lee tu agenda y le pide un consejo rápido a Gemini.
    NO usa la memoria del chat para no mezclar temas.
    """
    from .services.gemini_client import generar_respuesta
    
    if not user_id:
        return {"recommendation": "Inicia sesión para ver recomendaciones."}
    
    try:
        # Obtener eventos de los próximos 7 días
        service = get_calendar_service(user_id)
        now = datetime.now(LOCAL_TZ)
        end_date = (now + timedelta(days=7)).isoformat()
        
        events_result = service.events().list(
            calendarId='primary', timeMin=now.isoformat(), timeMax=end_date,
            maxResults=50, singleEvents=True, orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Prepara texto para preguntar a Gemini
        if events:
            events_text = "\n".join([
                f"- {e.get('summary', 'Sin título')}: {e['start'].get('dateTime', '')}"
                for e in events
            ])
        else:
            events_text = "No hay eventos."
        
        prompt = f"""Eres un experto en productividad. 
        Mira estos eventos de la semana:
        {events_text}
        
        Dame una recomendación breve o resumen para los próximos 7 días por puntos. Responde directamente con la recomendación, sin introducciones, aclaraciones ni referencias a fuentes. Máximo 3 líneas.   """
        
        response = generar_respuesta(prompt)
        recommendation = response.strip() if isinstance(response, str) else str(response).strip()
        
        return {"recommendation": recommendation}
        
    except Exception as e:
        return {"recommendation": "No pude generar recomendaciones."}
    


# 1. Definimos la ruta de los archivos estáticos (la carpeta dist)
static_path = os.path.join(os.path.dirname(__file__), "../frontend/dist")

# 2. Verificamos si existe la carpeta (para que no falle en local si no has hecho build)
if os.path.exists(static_path):
    # Montamos la carpeta para que cargue CSS y JS
    app.mount("/assets", StaticFiles(directory=f"{static_path}/assets"), name="assets")

    # 3. Ruta RAÍZ: Cuando entras a la web, devuelve el index.html
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # Si piden algo de la API, no interferimos (ya lo manejan los endpoints de arriba)
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")

        # Para cualquier otra cosa, devolvemos el archivo index.html (React)
        return FileResponse(f"{static_path}/index.html")
else:
    print("⚠️ No se encontró la carpeta frontend/dist. Ejecuta 'npm run build' primero.")
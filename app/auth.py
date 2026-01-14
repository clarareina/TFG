import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from .database import SessionLocal, User, init_db

# Configuración
CREDENTIALS_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service(user_email: str):
    """
    Función ÚNICA para obtener el servicio.
    Se encarga de buscar en BD, refrescar si hace falta, o pedir login.
    """
    init_db() # Aseguramos que la BD existe
    db = SessionLocal()
    creds = None
    
    # 1. BUSCAR EN BASE DE DATOS
    user = db.query(User).filter(User.email == user_email).first()

    if user and user.google_token:
        try:
            # Convertimos el texto JSON de la BD a objeto Credentials
            token_data = json.loads(user.google_token)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception:
            creds = None # Si el JSON estaba corrupto, lo ignoramos

    # 2. VERIFICAR SI VALE (O SI HAY QUE REFRESCAR / LOGUEAR)
    if not creds or not creds.valid:
        
        # CASO A: Token caducado pero renovable
        if creds and creds.expired and creds.refresh_token:
            try:
                print(f"🔄 Refrescando token para {user_email}...")
                creds.refresh(Request())
            except RefreshError:
                print("❌ Token revocado. Toca login manual.")
                creds = None # Forzamos login abajo

        # CASO B: No tenemos token válido (Nuevo usuario o falló el refresh)
        if not creds:
            print(f"🌍 Abriendo navegador para loguear a {user_email}...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # 3. GUARDAR EL RESULTADO EN BD (Siempre guardamos la versión más nueva)
        creds_json = creds.to_json()
        
        if not user:
            # Usuario nuevo
            user = User(email=user_email, google_token=creds_json)
            db.add(user)
        else:
            # Usuario existente, actualizamos su token
            user.google_token = creds_json
        
        db.commit()
        print(f"💾 Credenciales guardadas/actualizadas para {user_email}")

    db.close()
    
    # 4. DEVOLVER EL SERVICIO LISTO
    return build('calendar', 'v3', credentials=creds)

# --- (Opcional) La función de limpieza al arrancar ---
def startup_check_all_sessions():
    """Recorre la BD al inicio para refrescar tokens automáticamente."""
    print("🕵️  [STARTUP] Revisando sesiones guardadas...")
    db = SessionLocal()
    users = db.query(User).all()

    if not users:
        print("⚠️  Base de datos vacía. Esperando primer login web.")
        db.close()
        return

    for user in users:
        if not user.google_token: continue
        try:
            data = json.loads(user.google_token)
            creds = Credentials.from_authorized_user_info(data, SCOPES)
            
            # Solo refrescamos si es necesario
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                user.google_token = creds.to_json()
                db.commit()
                print(f"✅ Token refrescado para {user.email}")
                
        except Exception:
            print(f"❌ Token inválido para {user.email} (se arreglará en el próximo login)")
            user.google_token = None
            db.commit()

    db.close()
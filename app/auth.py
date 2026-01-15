import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow 
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from .database import SessionLocal, User, init_db

# Configuración
CREDENTIALS_FILE = "credentials.json"
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

def get_auth_url(redirect_uri: str, login_hint: str = None):
    """Genera la URL para que el usuario se loguee en Google."""
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    
    kwargs = {'prompt': 'consent'}
    if login_hint:
        kwargs['login_hint'] = login_hint
        
    auth_url, _ = flow.authorization_url(**kwargs)
    return auth_url

def exchange_code(code: str, redirect_uri: str):
    """Canjea el código devuelto por Google por credenciales y guarda el usuario."""
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Obtenemos email del usuario logueado usando la API de Google (userinfo)
    # Necesitamos un servicio 'oauth2' temporal para saber quién se ha logueado
    user_info_service = build('oauth2', 'v2', credentials=creds)
    user_info = user_info_service.userinfo().get().execute()
    user_email = user_info['email']

    # Guardamos en BD
    init_db()
    db = SessionLocal()
    
    user = db.query(User).filter(User.email == user_email).first()
    creds_json = creds.to_json()

    if not user:
        user = User(email=user_email, google_token=creds_json)
        db.add(user)
    else:
        user.google_token = creds_json
    
    db.commit()
    db.close()
    
    print(f"💾 Login WEB completado para {user_email}")
    return user_email

def get_calendar_service(user_email: str):
    """
    Recupera el servicio solo si ya existe token válido en BD.
    Si no, lanza error para que el frontend pida login.
    """
    init_db()
    db = SessionLocal()
    creds = None
    
    user = db.query(User).filter(User.email == user_email).first()

    if user and user.google_token:
        try:
            token_data = json.loads(user.google_token)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                # print(f"🔄 Refrescando token para {user_email}...")
                creds.refresh(Request())
                # Actualizar en BD
                user.google_token = creds.to_json()
                db.commit()
            except RefreshError:
                creds = None
        
    db.close()

    if not creds:
        # AQUÍ ESTÁ EL CAMBIO: Ya no abrimos navegador. 
        # Si no hay credenciales, devolvemos None o lanzamos error.
        raise ValueError(f"Usuario {user_email} no autenticado. Requiere login Web.")

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
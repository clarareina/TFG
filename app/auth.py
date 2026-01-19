import json
import os  
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow 
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from app.database import SessionLocal, User, init_db

# Configuración
CREDENTIALS_FILE = "credentials.json" 
ENV_CREDENTIALS_VAR = "GOOGLE_CREDENTIALS_JSON" # Nombre de la variable en Cloud Run

SCOPES = [
    'https://www.googleapis.com/auth/calendar',       
    'https://www.googleapis.com/auth/userinfo.email', 
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

def get_flow(redirect_uri: str):
    """
    Función auxiliar que decide de dónde sacar las credenciales:
    1. Si existe la variable de entorno (Cloud Run), usa eso.
    2. Si no, busca el archivo local (Localhost).
    """
    
    # 1. INTENTO NUBE: Leer de variable de entorno
    env_creds = os.environ.get(ENV_CREDENTIALS_VAR)
    if env_creds:
        try:
            client_config = json.loads(env_creds)
            # from_client_config lee un diccionario, no un archivo
            return Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )
        except json.JSONDecodeError as e:
            print(f"Error al leer el JSON de la variable de entorno: {e}")
            raise

    # 2. INTENTO LOCAL: Leer de archivo
    if os.path.exists(CREDENTIALS_FILE):
        return Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )

    # 3. Si todo falla
    raise ValueError("No se encontraron credenciales. Configura GOOGLE_CREDENTIALS_JSON o pon el archivo credentials.json")


def get_auth_url(redirect_uri: str, login_hint: str = None):
    """Genera la URL para que el usuario se loguee en Google."""
    
    # Usamos nuestra nueva función auxiliar
    flow = get_flow(redirect_uri)
    
    kwargs = {'prompt': 'consent'}
    if login_hint:
        kwargs['login_hint'] = login_hint 
        
    auth_url, _ = flow.authorization_url(**kwargs)
    return auth_url

def exchange_code(code: str, redirect_uri: str):
    """Canjea el código devuelto por Google por credenciales y guarda el usuario."""
    
    # Usamos nuestra nueva función auxiliar
    flow = get_flow(redirect_uri)
    
    flow.fetch_token(code=code)
    creds = flow.credentials 

    user_info_service = build('oauth2', 'v2', credentials=creds)
    user_info = user_info_service.userinfo().get().execute()
    user_email = user_info['email']

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
    
    return user_email

def get_calendar_service(user_email: str):
    """
    Recupera el servicio solo si ya existe token válido en BD.
    Gestiona la renovación automática del token (refresh).
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
                creds.refresh(Request())
                user.google_token = creds.to_json()
                db.commit()
            except RefreshError:
                creds = None
        
    db.close()

    if not creds:
        raise ValueError(f"Usuario {user_email} no autenticado. Requiere login Web.")

    return build('calendar', 'v3', credentials=creds)

def startup_check_all_sessions():
    """Recorre la BD al inicio para refrescar tokens automáticamente."""
    db = SessionLocal()
    users = db.query(User).all()

    if not users:
        print("Base de datos vacía. Esperando primer login web.")
        db.close()
        return

    for user in users:
        if not user.google_token: continue
        try:
            data = json.loads(user.google_token)
            creds = Credentials.from_authorized_user_info(data, SCOPES)
            
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                user.google_token = creds.to_json()
                db.commit()
                
        except Exception:
            user.google_token = None
            db.commit()

    db.close()
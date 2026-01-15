import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow 
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from .database import SessionLocal, User, init_db

# Configuración
CREDENTIALS_FILE = "credentials.json" # 💡 Archivo descargado de Google Cloud Console con Client ID y Secret.

SCOPES = [
    'https://www.googleapis.com/auth/calendar',       # Permiso para leer/escribir calendario
    'https://www.googleapis.com/auth/userinfo.email', # Para saber quién es el usuario
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

def get_auth_url(redirect_uri: str, login_hint: str = None):
    """Genera la URL para que el usuario se loguee en Google."""
    
    # Inicializa el flujo OAuth 
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri # Debe coincidir exactamente con lo configurado en Google Cloud.
    )
    
    # Fuerza a Google a preguntar permisos siempre, para que devuelva refresh_token (necesario para mantener la sesión viva sin pedir login diario).
    kwargs = {'prompt': 'consent'}
    
    if login_hint:
        kwargs['login_hint'] = login_hint # Pre-rellena el email si ya lo sabemos.
        
    # Genera la URL larga de Google donde el usuario hace clic.
    auth_url, _ = flow.authorization_url(**kwargs)
    return auth_url

def exchange_code(code: str, redirect_uri: str):
    """Canjea el código devuelto por Google por credenciales y guarda el usuario."""
    
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    
    # Canjea el código temporal (URL) por los tokens reales (access y refresh).
    flow.fetch_token(code=code)
    creds = flow.credentials # Llaves de acceso.

    # OAuth solo da tokens, oauth2 para preguntar a Google el email del dueño del token.
    user_info_service = build('oauth2', 'v2', credentials=creds)
    user_info = user_info_service.userinfo().get().execute()
    user_email = user_info['email']

    init_db()
    db = SessionLocal()
    
    # Si el usuario ya existe en nuestra BD
    user = db.query(User).filter(User.email == user_email).first()
    
    creds_json = creds.to_json()

    if not user:
        # Si es nuevo, lo creamos.
        user = User(email=user_email, google_token=creds_json)
        db.add(user)
    else:
        # Si ya existe, actualizamos el token ya que caducan
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
            # Reconstruimos Credentials de Google desde el json guardado en BD.
            token_data = json.loads(user.google_token)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception:
            creds = None

    # validez del token
    if not creds or not creds.valid:
        # si está caducado pero tenemos un refresh_token, intentamos renovarlo.
        if creds and creds.expired and creds.refresh_token:
            try:
                # pide un nuevo access token a Google sin que el usuario haga nada.
                creds.refresh(Request())
                
                # guardamos el token renovado en la BD para la próxima vez.
                user.google_token = creds.to_json()
                db.commit()
            except RefreshError:
                # Si falla anulamos credenciales.
                creds = None
        
    db.close()

    if not creds:
        # Si no hay manera de obtener credenciales válidas, error para forzar nuevo login.
        raise ValueError(f"Usuario {user_email} no autenticado. Requiere login Web.")

    return build('calendar', 'v3', credentials=creds)

def startup_check_all_sessions():
    """Recorre la BD al inicio para refrescar tokens automáticamente."""
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
            
            # Si el token ya caducó, lo renovamos ahora al arrancar la app.
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                user.google_token = creds.to_json()
                db.commit()
                
        except Exception:
            # Si el token está corrupto, lo borramos para obligar a reloguear.
            user.google_token = None
            db.commit()

    db.close()
from __future__ import print_function
import pickle                     # Para guardar y leer el token de sesión
from datetime import datetime
from dateutil import tz            # Para manejar zonas horarias
from googleapiclient.discovery import build   # Cliente de la API de Google
from google_auth_oauthlib.flow import InstalledAppFlow  # Para el login OAuth
from google.auth.transport.requests import Request      # Para refrescar credenciales
import os

CREDENTIALS_PATH = "credentials.json"
# Archivo donde se guardará el token una vez nos autentiquemos la primera vez (para no tener que iniciar sesión en cada ejecución)
TOKEN_PATH = "token.pickle"

# Alcance (scope) de los permisos que pedimos: en este caso, acceso completo al calendario
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_service():
    """
    Esta función:
    1. Comprueba si ya tenemos un token guardado (para no volver a loguear).
    2. Si no hay token válido, abre una ventana de login en el navegador.
    3. Devuelve un objeto 'service' que nos permite interactuar con la API de Google Calendar.
    """

    creds = None

    # Si ya existe un token guardado, lo cargamos
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as f:
            creds = pickle.load(f)

    # Si no hay credenciales válidas, pedimos login al usuario
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Si el token está caducado pero tiene refresh_token, se renueva automáticamente
            creds.refresh(Request())
        else:
            # Si no hay token, iniciamos el flujo de autorización OAuth
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)  # Abre navegador para login con tu cuenta de Google

        # Guardamos el token en disco para la próxima vez
        with open(TOKEN_PATH, 'wb') as f:
            pickle.dump(creds, f)

    # Creamos el objeto 'service' para trabajar con la API de Calendar
    return build('calendar', 'v3', credentials=creds)

print("Funciones cargadas. Listo para autenticar.")

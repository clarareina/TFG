from __future__ import print_function
import pickle
import os
from datetime import datetime
from dateutil import tz
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

CREDENTIALS_PATH = "credentials.json"
TOKEN_PATH = "token.pickle"
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_service():
    """
    Devuelve un objeto 'service' para interactuar con Google Calendar.
    Si el token está caducado o revocado, se elimina y se inicia sesión de nuevo automáticamente.
    """

    creds = None

    # 1. Si existe un token, lo cargamos
    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, 'rb') as f:
                creds = pickle.load(f)
        except Exception:
            creds = None

    # 2. Si no hay credenciales válidas o el token falla, intentamos refrescar o regenerar
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                # Token inválido: se borra y se solicita login de nuevo
                print("Token expirado o revocado. Regenerando credenciales...")
                if os.path.exists(TOKEN_PATH):
                    os.remove(TOKEN_PATH)
                creds = None
        else:
            creds = None

        # Si seguimos sin credenciales válidas, pedimos inicio de sesión nuevo
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)  # abre el navegador para login

        # Guardar el nuevo token
        with open(TOKEN_PATH, 'wb') as f:
            pickle.dump(creds, f)

    # 3. Crear el servicio
    service = build('calendar', 'v3', credentials=creds)
    return service
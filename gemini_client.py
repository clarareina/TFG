# gemini_client.py
from dotenv import load_dotenv
import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, PermissionDenied


# Carga la variable GEMINI_API_KEY desde el archivo .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("No se encontró GEMINI_API_KEY en el archivo .env")

# Configura la conexión con Gemini
genai.configure(api_key=api_key)


def generar_respuesta(prompt):
    """
    Envía un prompt a Gemini y devuelve la respuesta generada.
    Usa 'gemini-2.5-pro' y cambia a 'gemini-2.5-flash' si se excede el límite.
    """

    # Crea el modelo que usarás en todo el proyecto
    try:
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(prompt)
    except (ResourceExhausted, PermissionDenied):
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
    return response.text

print(generar_respuesta("Responde solo: OK"))

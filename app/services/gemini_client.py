from dotenv import load_dotenv
import google.generativeai as genai
import os
from google.api_core.exceptions import ResourceExhausted, PermissionDenied


# Carga la variable GEMINI_API_KEY desde el archivo .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("No se encontró GEMINI_API_KEY en el archivo .env")

# Configura la conexión con Gemini
genai.configure(api_key=api_key)


def generar_respuesta(prompt, temp=0.2):
    """
    Envía un prompt a Gemini y devuelve la respuesta generada.
    Usa 'gemini-2.5-pro' y cambia a 'gemini-2.5-flash' si se excede el límite.
    """

    try:
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(prompt, stream=True, generation_config={"temperature": temp})
    except (ResourceExhausted, PermissionDenied):
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt, stream=True, generation_config={"temperature": temp})

    full_text = ""
    try:
        for chunk in response:
            if hasattr(chunk, 'text') and chunk.text:
                full_text += chunk.text
    except Exception as e:
        if not full_text:
            return "No pude generar una respuesta. Por favor, inténtalo de nuevo."
    
    return full_text if full_text else "No pude generar una respuesta. Por favor, inténtalo de nuevo."
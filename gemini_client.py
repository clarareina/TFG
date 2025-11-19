from dotenv import load_dotenv
import google.generativeai as genai
import os
from google.api_core.exceptions import ResourceExhausted, PermissionDenied

from google.generativeai.types import HarmCategory, HarmBlockThreshold


# Carga la variable GEMINI_API_KEY desde el archivo .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("No se encontró GEMINI_API_KEY en el archivo .env")

# Configura la conexión con Gemini
genai.configure(api_key=api_key)


# def generar_respuesta(prompt, temp=0.2):
#     """
#     Envía un prompt a Gemini y devuelve la respuesta generada.
#     Usa 'gemini-2.5-pro' y cambia a 'gemini-2.5-flash' si se excede el límite.
#     """

#     # Crea el modelo que usarás en todo el proyecto
#     try:
#         model = genai.GenerativeModel("gemini-2.5-pro")
#         response = model.generate_content(prompt, stream=True)
#     except (ResourceExhausted, PermissionDenied):
#         model = genai.GenerativeModel("gemini-2.5-flash")
#         response = model.generate_content(prompt, stream=True)


#     full_text = ""
#     # 1. Itera sobre el 'response_iterator' (sea el Pro o el Flash)
#     for chunk in response:
#         # 2. Imprime cada trozo en la consola (el streaming)
#         print(chunk.text, end="", flush=True)
#         # 3. Acumula el texto para el return final
#         full_text += chunk.text

#     return full_text # 4. Devuelve el texto completo acumulado

#     # return response.text

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

def generar_respuesta(prompt, temp=0.0):
    """
    Envía un prompt a Gemini y devuelve la respuesta completa como texto.
    Maneja la seguridad y el fallback de modelos automáticamente.
    """
    
    # Configuración de generación (Temperatura)
    generation_config = {
        "temperature": temp,
        "max_output_tokens": 8192,
    }

    # Definimos los modelos (ajusta los nombres si usas versiones preview/exp)
    # Nota: "gemini-2.5" no es estándar aún, uso 1.5 que es el estable actual.
    # Si tienes acceso a 2.0 o experimental, cambia los nombres aquí.
    primary_model_name = "gemini-2.5-pro"   
    fallback_model_name = "gemini-2.5-flash"

    try:
        # INTENTO 1: Modelo Potente (Pro)
        model = genai.GenerativeModel(
            model_name=primary_model_name,
            safety_settings=SAFETY_SETTINGS, # <--- ESTO ARREGLA EL BLOQUEO
            generation_config=generation_config
        )
        # Usamos stream=False para evitar errores de 'chunk' vacíos
        response = model.generate_content(prompt, stream=False)
        return response.text

    except (ResourceExhausted, PermissionDenied) as e:
        print(f"[Gemini] Límite excedido en Pro, cambiando a Flash... ({e})")
        
        # INTENTO 2: Modelo Rápido (Flash)
        try:
            model = genai.GenerativeModel(
                model_name=fallback_model_name,
                safety_settings=SAFETY_SETTINGS,
                generation_config=generation_config
            )
            response = model.generate_content(prompt, stream=False)
            return response.text
            
        except Exception as e_flash:
            return f"Error crítico en Gemini Flash: {e_flash}"

    except ValueError:
        # Si a pesar de la configuración salta el bloqueo (muy raro con BLOCK_NONE)
        return "Error: La respuesta fue bloqueada por seguridad incluso con filtros bajos."
        
    except Exception as e:
        return f"Error inesperado en Gemini: {e}"
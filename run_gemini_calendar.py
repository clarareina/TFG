import json
import re
import inspect

from prompt import prompt
from gemini_client import generar_respuesta
from calendar_functions import create_event, delete_event, duplicate_event, patch_event, get_events

FUNCTION_MAP = {
    "create_event": create_event,
    "delete_event": delete_event,
    "duplicate_event": duplicate_event,
    "patch_event": patch_event,
    "get_events": get_events
}

def limpiar_json(texto):
    if not texto:
        return ""
    return re.sub(r"```json|```", "", texto, flags=re.IGNORECASE).strip()


# Función para convertir el texto JSON en un diccionario Python
def interpretar_respuesta_json(texto):
    limpio = limpiar_json(texto)
    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        print("Error: Gemini devolvió un JSON inválido:\n", limpio)
        return None


#Función que ejecuta la función real del calendario según el JSON devuelto por Gemini.
def ejecutar_funcion(obj):
    fn_name = obj.get("function")           # Nombre de la función (ej. "create_event")
    params = obj.get("parameters", {})      # Parámetros a pasar (ej. {"name": "Reunión", ...})

    # Verifica que la función exista en tu mapa
    if fn_name not in FUNCTION_MAP:
        print(f"Función desconocida: {fn_name}")
        return

    fn = FUNCTION_MAP[fn_name]  # Asigna la función real (ej. create_event)

    # Verifica que los parámetros coincidan con los que la función admite
    sig = inspect.signature(fn)
    valid_args = list(sig.parameters.keys())
    extras = [k for k in params.keys() if k not in valid_args]
    if extras:
        print(f"Aviso: hay parámetros desconocidos que se ignorarán: {extras}")

    # Ejecuta la función con los parámetros recibidos
    try:
        print(f"➡️ Ejecutando {fn_name}(**{params})...")
        resultado = fn(**params)
        print("✅ Ejecución correcta:", resultado)
    except Exception as e:
        print(f"❌ Error ejecutando {fn_name}: {e}")


# Función principal — ciclo interactivo
def main():
    print("🧠 Agente gestor de calendario iniciado.")
    print("Escribe una instrucción (o 'salir' para terminar):")

    while True:
        user_input = input("\n> ").strip()
        if user_input.lower() in ("salir", "exit", "q"):
            print("👋 Fin del programa.")
            break

        # Combina tu prompt largo con la frase del usuario
        prompt_final = f"{prompt}\n\nUsuario: {user_input}\n"

        # Envía el texto a Gemini
        respuesta = generar_respuesta(prompt_final)
        print("\n🤖 Gemini respondió:\n", respuesta)

        # Convierte la respuesta en JSON
        obj = interpretar_respuesta_json(respuesta)
        if not obj:
            continue

        # Si Gemini devuelve una lista (varias instrucciones), ejecuta todas
        if isinstance(obj, list):
            for accion in obj:
                ejecutar_funcion(accion)
        else:
            ejecutar_funcion(obj)


if __name__ == "__main__":
    main()

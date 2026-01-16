import os
from dotenv import load_dotenv

# override=True obliga a machacar lo que haya en memoria con lo que hay en el archivo
load_dotenv(override=True)

from langsmith import traceable
import time

try:
    from app.flow import run_agent 
except ImportError:
    print("Error importing app.flow. Run this from the project root.")
    exit()

# Usuario de prueba (cambia por tu email si es necesario)
TEST_USER_ID = "santiclaragpt@gmail.com"

# ============================================
# TESTS SECUENCIALES - PARTIENDO DE CALENDARIO VACÍO
# Cada test construye sobre los anteriores
# ============================================
TEST_CASES = [
    # --- SALUDO INICIAL ---
    "Hola, ¿cómo estás?",
    "¿Qué día es hoy?",
    
    # --- VERIFICAR CALENDARIO VACÍO ---
    "¿Qué tengo en la agenda para hoy?",
    "Muestra los eventos de esta semana.",
    
    # --- CREAR EVENTOS BASE ---
    "Crea una reunión mañana a las 10:00.",
    "Agendar cita con el dentista el viernes a las 16:00.",
    "Pon una comida de trabajo el lunes de 13:00 a 15:00.",
    "Apunta clase de yoga el miércoles a las 19:30.",
    "Crea un evento llamado 'Cumpleaños Ana' el 25 de enero todo el día.",
    "Pon una entrevista de trabajo el jueves a las 11:00.",
    
    # --- VERIFICAR QUE SE CREARON ---
    "¿Qué tengo mañana?",
    "Muestra los eventos de esta semana.",
    "¿Tengo algo el viernes?",
    
    # --- MODIFICAR EVENTOS EXISTENTES ---
    "Cambia la reunión de mañana a las 11:00.",
    "Mueve la cita del dentista a las 17:00.",
    "Alarga la clase de yoga 30 minutos más.",
    "Renombra la comida de trabajo a 'Almuerzo con clientes'.",
    "Cambia la entrevista del jueves al viernes a las 10:00.",
    
    # --- VERIFICAR CAMBIOS ---
    "¿A qué hora tengo la reunión mañana?",
    "¿Qué tengo el viernes?",
    
    # --- DUPLICAR EVENTOS ---
    "Duplica la clase de yoga para el viernes.",
    "Duplica la reunión de mañana para el jueves.",
    
    # --- BUSCAR HUECOS CON EVENTOS YA EXISTENTES ---
    "¿Tengo algún hueco libre mañana por la tarde?",
    "Busca un hueco de 2 horas el jueves.",
    "¿Cuándo podría meter una cena esta semana?",
    
    # --- CREAR EVENTOS EN HORARIOS OCUPADOS (CONFLICTOS) ---
    "Crea una cita mañana a las 11:00.",  # Conflicto con la reunión
    "Pon algo el viernes a las 17:00.",  # Conflicto con dentista modificado
    
    # --- BORRAR EVENTOS ESPECÍFICOS ---
    "Borra la clase de yoga del miércoles.",
    "Elimina la entrevista del viernes.",
    
    # --- VERIFICAR BORRADO ---
    "¿Tengo yoga esta semana?",
    "¿Qué tengo el viernes ahora?",
    
    # --- DESHACER ACCIÓN ---
    "Deshaz la última acción.",
    
    # --- CONSULTAS SOBRE EVENTOS EXISTENTES ---
    "¿Cuántas reuniones tengo esta semana?",
    "Resume mi semana.",
    "¿Cuál es mi día más ocupado?",
    
    # --- BORRAR EVENTOS QUE NO EXISTEN (ERROR) ---
    "Borra la reunión con el presidente.",
    "Elimina el evento de natación.",
    
    # --- MODIFICAR EVENTOS QUE NO EXISTEN (ERROR) ---
    "Cambia la cita con el abogado a las 18:00.",
    "Mueve el partido de fútbol al sábado.",
    
    # --- CASOS EDGE / ERRORES ---
    "Agendar cita el 30 de febrero.",
    "Crea una reunión a las 32:00.",
    "Agenda algo para el 31 de noviembre.",
    "Pon un evento con duración negativa.",
    
    # --- LENGUAJE INFORMAL Y ERRORES ---
    "ke tengo mñana??",
    "ponme algo pa el finde",
    "borra tooodo",
    "LISTA MIS EVENTOS",
    
    # --- EMOJIS Y CARACTERES ESPECIALES ---
    "Crea una fiesta 🎉 el sábado a las 21:00",
    "¿Qué tengo hoy? 🤔",
    
    # --- FUERA DE CONTEXTO ---
    "¿Cuál es la capital de Francia?",
    "Manda un correo a Daniela.",
    "Cuéntame un chiste.",
    
    # --- MÚLTIPLES ACCIONES ---
    "Crea una reunión mañana a las 9 y otra a las 15.",
    "Borra el dentista y pon una cita nueva el lunes a las 10.",
    
    # --- FECHAS RELATIVAS ---
    "Pon una reunión dentro de 2 horas.",
    "Agénda algo para pasado mañana a mediodía.",
    "Crea un evento para la próxima semana.",
    
    # --- DURACIONES EXTRAÑAS ---
    "Crea evento de 5 minutos mañana.",
    "Agenda reunión de 8 horas el lunes.",
    
    # --- CONSULTAS ESPECÍFICAS ---
    "¿Tengo libre mañana de 14:00 a 15:00?",
    "¿Cuánto tiempo libre tengo el viernes?",
    
    # --- BORRAR TODO (LIMPIEZA) ---
    "Borra todos los eventos del lunes.",
    "Elimina todo lo de mañana.",
    
    # --- MENSAJES RAROS ---
    "asdfghjkl",
    "123456789",
    "...",
    "???",
    "",
    
    # --- DESPEDIDA ---
    "Gracias por tu ayuda.",
    "Adiós.",
]

# ============================================
# TESTS MULTI-PASO (COMENTADOS DE MOMENTO)
# ============================================
# MULTI_STEP_TESTS = [
#     {
#         "name": "Crear evento → Conflicto → Elegir opción 1",
#         "steps": [
#             "Crea una reunión mañana a las 10:00.",
#             "Crea otra reunión mañana a las 10:00.",
#             "1",
#         ]
#     },
#     # ... más tests multi-paso
# ]

# "Test Suite" agrupa todas las pruebas
@traceable(name="Test Suite", run_type="chain")
def run_test_suite():
    total_tests = len(TEST_CASES)
    
    print(f"Starting Sequential Test Suite...")
    print(f"  - Total tests: {total_tests}")
    print(f"Test User: {TEST_USER_ID}")
    print(f"\n⚠️  IMPORTANTE: Asegúrate de partir de un calendario VACÍO")
    print("=" * 60)
    
    successful_runs = 0
    failed_runs = 0
    
    for test_num, prompt in enumerate(TEST_CASES, 1):
        display = prompt[:60] + "..." if len(prompt) > 60 else prompt
        print(f"\n🔹 Test [{test_num}/{total_tests}]: {display}")
        print("-" * 50)
        try:
            response = run_agent(prompt, TEST_USER_ID)
            
            if isinstance(response, dict):
                status = response.get("status", "unknown")
                resp_text = response.get("response", "Sin respuesta")
                print(f"   Status: {status}")
                print(f"   Response: {resp_text[:150]}..." if len(str(resp_text)) > 150 else f"   Response: {resp_text}")
            else:
                print(f"   Response: {str(response)[:150]}...")
            
            successful_runs += 1
            
        except Exception as e:
            print(f"   ❌ CRITICAL ERROR: {e}")
            failed_runs += 1
        
        time.sleep(1)
    
    # RESUMEN
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE RESULTADOS")
    print("=" * 60)
    print(f"✅ Ejecuciones exitosas: {successful_runs}/{total_tests}")
    print(f"❌ Errores críticos: {failed_runs}/{total_tests}")
    print(f"📈 Tasa de éxito: {(successful_runs/total_tests)*100:.1f}%")
    print("\n💡 Revisa LangSmith para trazas detalladas.")

if __name__ == "__main__":
    run_test_suite()
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


TEST_CASES = [
    # Nivel 1: Basic
    # "Agendar una reunión con el tutor mañana a las 10:00.",
    # "Apunta comida de empresa mañana de 14 a 17",
    # "¿Qué tengo en la agenda para hoy?",
    # "Borrar la comida de empresa.",
    
    # # Nivel 2: Logic
    # "Duplica la reunión con el tutor mañana a las 12:00.",
    # "Mueve la reunión con el tutor a las 11:00.",
    # "Programa un descanso de 30 minutos dentro de 2 horas.",
    
    # # Nivel 3: Reasoning / Edge Cases
    # "¿Tengo algún hueco libre el martes por la tarde?",
    "Agendar cita el 30 de febrero.", 
    "Agendar una reunión con el tutor mañana a las 32:00.",
    "Busca el mejor hueco para cena con mis padres esta semana.",
    "Busca un hueco para una cena el 30 de febrero",
    "¿Qué día es hoy?",
    "¿Cuántos días quedan para el 30 de enero?",
    "Manda un correo a Daniela"
]

# "Test Suite" agrupa todas las pruebas
@traceable(name="Test Suite", run_type="chain")
def run_test_suite():
    print(f"Starting Test Suite with {len(TEST_CASES)} cases...\n")
    
    successful_runs = 0
    
    for i, prompt in enumerate(TEST_CASES):
        print(f"🔹 Test [{i+1}]: {prompt}")
        try:
            # Llamada al agente
            response = run_agent(prompt)
            
            # Imprimir inicio de respuesta para verificar
            print(f"Agent Response: {str(response)[:100]}...") 
            successful_runs += 1
            
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
        
        print("-" * 50)
        time.sleep(1) 

    print(f"\nTechnical Results: {successful_runs}/{len(TEST_CASES)} runs without crashing.")
    print("Check LangSmith for detailed traces and JSON outputs.")

if __name__ == "__main__":
    run_test_suite()
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
    "Agendar una reunión con el tutor mañana a las 10:00.",
    "¿Qué tengo en la agenda para hoy?",
    "Borrar la reunión con el tutor.",
    
    # Nivel 2: Logic
    "Mueve la reunión del tutor a las 12:00.",
    "Programa un descanso de 30 minutos dentro de 2 horas.",
    
    # Nivel 3: Reasoning / Edge Cases
    "¿Tengo algún hueco libre el martes por la tarde?",
    "Agendar cita el 30 de febrero.", 
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
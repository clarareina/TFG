import pandas as pd 
import json
from datetime import datetime
from app.prompts import classifier_prompt
from app.services.gemini_client import generar_respuesta


def calculate_time_analytics(events_list: list):
    """
    Recibe la lista de eventos de Google Calendar y devuelve
    los porcentajes de tiempo gastado en cada categoría.
    """
    
    if not events_list:
        return {"status": "empty", "data": []}

    # Convertimos la lista de diccionarios en una tabla con columnas: 'summary', 'start', 'end', etc.
    df = pd.DataFrame(events_list)
    

    # LIMPIEZA DE DATOS (Fechas)
    # Google nos da las fechas en ISO format, Pandas necesita entender que son fechas reales para poder restar.
    df['start_dt'] = df['start'].apply(lambda x: x.get('dateTime') or x.get('date'))
    df['end_dt'] = df['end'].apply(lambda x: x.get('dateTime') or x.get('date'))

    # Convertimos esas columnas a formato FECHA de Pandas
    # format='mixed' para manejar tanto eventos con hora (ISO8601) como eventos de día completo (solo fecha)
    df['start_dt'] = pd.to_datetime(df['start_dt'], utc=True, format='mixed')
    df['end_dt'] = pd.to_datetime(df['end_dt'], utc=True, format='mixed')

    # CALCULAR DURACIÓN
    df['duration_minutes'] = (df['end_dt'] - df['start_dt']).dt.total_seconds() / 60

    # Clasificación
    # Sacamos los títulos únicos (para no preguntar 2 veces por "Gimnasio")
    unique_titles = df['summary'].unique().tolist()
    
    prompt = classifier_prompt(unique_titles)
    
    try:
        response_json = generar_respuesta(prompt) 
        
        response_json = response_json.replace("```json", "").replace("```", "").strip()

        category_map = json.loads(response_json)
        
    except Exception as e:
        print(f"Error clasificando con IA: {e}")
        category_map = {} # Si falla, se quedará vacío

    # ASIGNAR CATEGORÍAS 
    # Creamos una columna nueva 'category', Pandas mira el 'summary', busca en el mapa y si no está, pone 'Otros'.
    df['category'] = df['summary'].map(category_map).fillna('Otros')

    # RESUMIR 
    # Agrupamos por categoría y sumamos los minutos
    stats = df.groupby('category')['duration_minutes'].sum().reset_index()

    # category      | duration_minutes
    # Deporte       | 120
    # Trabajo       | 400

    #CALCULAR PORCENTAJES Y FORMATO FINAL
    total_minutes = stats['duration_minutes'].sum()
    result_data = []
    
    for index, row in stats.iterrows():
        percentage = round((row['duration_minutes'] / total_minutes) * 100, 1)
        result_data.append({
            "name": f"{row['category']} ({percentage}%)",   
            "value": percentage,       
            "minutes": int(row['duration_minutes']) 
        })

    # Ordenamos de mayor a menor porcentaje
    result_data.sort(key=lambda x: x['value'], reverse=True)

    return result_data
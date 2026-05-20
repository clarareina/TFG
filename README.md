# Trabajo Fin de Grado: Agente Autónomo para Gestión Inteligente de Calendarios

**Autor/a:** Clara Reina Romero  
**Titulación:** Grado en Ingeniería Informática - Tecnologías Informáticas  
**Universidad:** Universidad de Sevilla (ETSII)  

---

## Descripción del Proyecto

Este repositorio contiene el código fuente del Trabajo Fin de Grado titulado "Agente autónomo para gestión inteligente de calendarios". 

El proyecto consiste en un asistente inteligente que permite la transición de las interfaces gráficas tradicionales (GUI) hacia las interfaces de lenguaje natural (LUI). El sistema permite interactuar con Google Calendar de forma conversacional, delegando en un agente autónomo (impulsado por modelos fundacionales y la arquitectura LangGraph) la complejidad de interpretar intenciones, manejar expresiones temporales y resolver conflictos de agenda utilizando una arquitectura *Human-in-the-loop*.

---

## Tecnologías Utilizadas

* **Backend:** Python, FastAPI, LangGraph, SQLite (para persistencia del agente).
* **Frontend:** React, Vite, TypeScript.
* **APIs Externas:** Google Calendar API, Google Gemini API.

---

## Requisitos Previos

Para ejecutar este proyecto en un entorno local, es necesario tener instalado:
* Python 3.10 o superior.
* Node.js (versión 18 o superior) y npm.
* Credenciales válidas de la API de Google Cloud y Gemini (Variables de entorno).

---

## Guía de Instalación y Ejecución

Para evaluar el sistema, por favor, clone este repositorio y siga estos pasos abriendo dos terminales distintas.

### 1. Configuración y Arranque del Backend (FastAPI)

Abra una terminal en la carpeta raíz del proyecto (donde se encuentra el archivo `requirements.txt`):

```bash
# 1. Instalar las dependencias de Python
pip install -r requirements.txt

# 2. Arrancar el servidor local
uvicorn app.main:app --reload

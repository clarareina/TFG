import { useState, useEffect } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import CalendarView from './components/CalendarInterface'
import UpcomingEvents from './components/EventsInterface'
import StatsInterface from './components/StatsInterface'

import { GoogleLogin } from '@react-oauth/google'
import type { CredentialResponse } from '@react-oauth/google'

const API_URL = 'http://localhost:8000'

function App() {
  // 1. ESTADO: Inicializamos mirando directamente en la memoria del navegador
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(() => {
    return localStorage.getItem('google_logged_in') === 'true'
  })
  const [errorMessage, setErrorMessage] = useState<string>('')

  // 2. VERIFICAR AUTENTICACIÓN AL CARGAR (si dice que está logueado, verificar con backend)
  useEffect(() => {
    if (isLoggedIn) {
      checkAuthStatus()
    }
  }, [])

  const checkAuthStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/auth/status/default_user`)
      const data = await response.json()
      if (!data.authenticated) {
        // Backend dice que no está autenticado
        setErrorMessage('USUARIO NO AUTENTICADO')
        localStorage.removeItem('google_logged_in')
        setIsLoggedIn(false)
      }
    } catch (error) {
      console.error('Error verificando autenticación:', error)
    }
  }

  // 3. FUNCIÓN LOGIN: Cuando Google nos da el OK
  const handleLoginSuccess = (credentialResponse: CredentialResponse) => {
    console.log("Login Éxito:", credentialResponse)
    // Guardamos la "marca" en el navegador para que no se olvide al recargar
    localStorage.setItem('google_logged_in', 'true')
    setErrorMessage('')
    setIsLoggedIn(true)
  }

  // 4. FUNCIÓN LOGOUT: Para poder salir y probar de nuevo
  const handleLogout = () => {
    localStorage.removeItem('google_logged_in') // Borramos la marca
    setIsLoggedIn(false) // Actualizamos la pantalla
  }

  // 5. PANTALLA DE LOGIN (Si NO estamos logueados)
  if (!isLoggedIn) {
    return (
      <div style={{
        height: '100vh', display: 'flex', flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center', backgroundColor: '#f3f4f6'
      }}>
        <div className="card" style={{ maxWidth: '400px', textAlign: 'center', padding: '40px' }}>
          <h2>Bienvenido</h2>
          <p style={{ marginBottom: '20px', color: '#666' }}>Inicia sesión para continuar</p>

          {/* Mensaje de error si no está autenticado */}
          {errorMessage && (
            <p style={{ color: '#ef4444', marginBottom: '15px', fontWeight: 'bold' }}>
              {errorMessage}
            </p>
          )}

          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <GoogleLogin
              onSuccess={handleLoginSuccess}
              onError={() => console.log('Login Fallido')}
              useOneTap
            />
          </div>
        </div>
      </div>
    )
  }

  // 6. PANTALLA PRINCIPAL (DASHBOARD) 
  return (
    <div className="layout-dashboard">

      {/* COLUMNA 1: CHAT */}
      <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Asistente</h3>
          <button
            onClick={handleLogout}
            style={{
              background: '#ef4444',
              color: 'white',
              border: 'none',
              padding: '6px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: 'bold'
            }}
          >
            Salir
          </button>
        </div>
        <ChatInterface />
      </div>

      {/* COLUMNA 2: CALENDARIO */}
      <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>

        {/* CABECERA: TÍTULO Y BOTÓN JUNTOS */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '15px'
        }}>
          <h3 style={{ margin: 0 }}>Calendario</h3>

          {/* Botón de Google Calendar (Ahora vive aquí arriba) */}
          <button
            onClick={() => window.open('https://calendar.google.com', '_blank')}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              background: 'white', border: '1px solid #ddd',
              padding: '6px 12px', borderRadius: '20px',
              cursor: 'pointer', color: '#555', fontWeight: 600, fontSize: '0.85rem'
            }}
          >
            📅 Google Calendar
          </button>
        </div>

        {/* EL CALENDARIO (Ahora ocupará el resto del espacio) */}
        <div style={{ flex: 1, minHeight: 0 }}>
          <CalendarView />
        </div>
      </div>

      {/* COLUMNA 3: PRÓXIMOS EVENTOS + ESTADÍSTICAS */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--separacion)', overflow: 'hidden' }}>

        {/* PRÓXIMOS EVENTOS */}
        <div className="card" style={{ flex: 5, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 15px 0', flexShrink: 0 }}>Próximos Eventos</h3>
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            <UpcomingEvents />
          </div>
        </div>

        {/* ESTADÍSTICAS */}
        <div className="card" style={{ flex: 5, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 10px 0', flexShrink: 0 }}>Recomendaciones</h3>
          <StatsInterface />
        </div>

      </div>
    </div>
  )
}

export default App

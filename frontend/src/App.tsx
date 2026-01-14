import { useState, useEffect } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import CalendarView from './components/CalendarInterface'
import UpcomingEvents from './components/EventsInterface'
import StatsInterface from './components/StatsInterface'

// Definimos el usuario que usaremos (esto simula el login)
// IMPORTANTE: Asegúrate de que este email coincide con el que usaste en el Backend
// const USUARIO_SESION = "usuario_demo@gmail.com"
const USUARIO_SESION = "user"

function App() {
  const [isCalendarLoading, setIsCalendarLoading] = useState(true)
  
  // Estado para guardar el usuario actual.
  // Inicialmente es null, pero en cuanto carga la app, le asignamos el usuario.
  const [userId, setUserId] = useState<string | null>(null)

  useEffect(() => {
    // Simulamos que el usuario inicia sesión al entrar
    setUserId(USUARIO_SESION)
  }, [])

  // PANTALLA PRINCIPAL (DASHBOARD)
  return (
    <div className="layout-dashboard">

      {/* COLUMNA 1: CHAT */}
      <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Asistente</h3>
        </div>
        {/* Pasamos el userId al Chat para que sepa quién habla */}
        <ChatInterface userId={userId} />
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

          {/* Texto de carga centrado */}
          {isCalendarLoading && (
            <span style={{ color: '#9CA3AF', flex: 1, textAlign: 'center' }}>Cargando calendario...</span>
          )}

          {/* Botón de Google Calendar */}
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

        {/* EL CALENDARIO */}
        {/* Pasamos userId también al calendario */}
        <div style={{ flex: 1, minHeight: 0 }}>
          <CalendarView 
             userId={userId} 
             onLoadingChange={setIsCalendarLoading} 
          />
        </div>
      </div>

      {/* COLUMNA 3: PRÓXIMOS EVENTOS + ESTADÍSTICAS */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--separacion)', overflow: 'hidden' }}>

        {/* PRÓXIMOS EVENTOS */}
        <div className="card" style={{ flex: 5, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 15px 0', flexShrink: 0 }}>Próximos Eventos</h3>
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            {/* Pasamos userId a la lista de eventos */}
            <UpcomingEvents userId={userId} />
          </div>
        </div>

        {/* ESTADÍSTICAS */}
        <div className="card" style={{ flex: 5, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 10px 0', flexShrink: 0 }}>Recomendaciones</h3>
          {/* AQUI ESTÁ LA CLAVE: Conectamos Stats con el usuario */}
          <StatsInterface userId={userId} />
        </div>

      </div>
    </div>
  )
}

export default App
import { useState } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import CalendarView from './components/CalendarInterface'
import UpcomingEvents from './components/EventsInterface'
import StatsInterface from './components/StatsInterface'

function App() {
  const [isCalendarLoading, setIsCalendarLoading] = useState(true)

  // PANTALLA PRINCIPAL (DASHBOARD)
  return (
    <div className="layout-dashboard">

      {/* COLUMNA 1: CHAT */}
      <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Asistente</h3>
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
        <div style={{ flex: 1, minHeight: 0 }}>
          <CalendarView onLoadingChange={setIsCalendarLoading} />
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

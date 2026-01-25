import { useState, useEffect } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import CalendarView from './components/CalendarInterface'
import UpcomingEvents from './components/EventsInterface'
import StatsInterface from './components/StatsInterface'

// 1. Detección de entorno (Local vs Nube)
const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
export const API_BASE_URL = isLocal
  ? "http://localhost:8000"
  : "https://tgf-v1-11980723519.europe-southwest1.run.app";


const LoginScreen = ({ onLogin }: { onLogin: () => void }) => {
  const [email, setEmail] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = async () => {
    if (!email) return alert("Por favor introduce un usuario")
    setIsLoading(true)

    const fullEmail = `${email}@gmail.com`

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login?user_id=${fullEmail}`)
      const data = await res.json()

      if (data.status === "success") {
        localStorage.setItem("tfg_user_id", fullEmail)
        onLogin()
      } else {
        const redirectUri = window.location.origin
        const urlRes = await fetch(`${API_BASE_URL}/api/auth/url?redirect_uri=${redirectUri}&login_hint=${fullEmail}`)
        const urlData = await urlRes.json()
        window.location.href = urlData.url
      }
    } catch (e) {
      console.error(e)
      alert("Error conectando con el servidor.")
      setIsLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center',
      backgroundColor: '#f3f4f6', flexDirection: 'column', gap: '20px'
    }}>
      <div className="card" style={{ width: '400px', alignItems: 'center', gap: '20px' }}>
        <h2>TFG</h2>
        <p style={{ color: '#666', textAlign: 'center' }}>Inicia sesión con una cuenta de google</p>
        <div style={{ display: 'flex', width: '100%' }}>
          <input
            type="text" placeholder="usuario" value={email}
            onChange={e => setEmail(e.target.value)}
            style={{ flex: 1, padding: '10px', borderRadius: '8px 0 0 8px', border: '1px solid #ddd', borderRight: 'none' }}
          />
          <span style={{
            padding: '10px 12px', background: '#f3f4f6', border: '1px solid #ddd',
            borderRadius: '0 8px 8px 0', color: '#666', whiteSpace: 'nowrap'
          }}>@gmail.com</span>
        </div>
        <button
          onClick={handleLogin} disabled={isLoading}
          style={{
            width: '100%', padding: '12px', background: '#2563eb', color: 'white',
            border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold'
          }}
        >
          {isLoading ? "Verificando..." : "Iniciar Sesión"}
        </button>
      </div>
    </div>
  )
}

function App() {
  const [isCalendarLoading, setIsCalendarLoading] = useState(true)
  const [userId, setUserId] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(true)

  // --- ESTADOS PARA PREFERENCIAS ---
  const [showPrefs, setShowPrefs] = useState(false)
  const [prefsText, setPrefsText] = useState("") // Aquí se guarda el texto cargado
  const [isSavingPrefs, setIsSavingPrefs] = useState(false)

  // --- ESTADO PARA PESTAÑAS EN MÓVIL ---
  const [activeTab, setActiveTab] = useState<'chat' | 'calendar' | 'stats'>('chat')

  // 1. Auth inicial
  useEffect(() => {
    const checkAuth = async () => {
      const params = new URLSearchParams(window.location.search)
      const code = params.get("code")

      if (code) {
        try {
          const body = JSON.stringify({
            code,
            redirect_uri: window.location.origin
          })
          const headers = { "Content-Type": "application/json" }

          const res = await fetch(`${API_BASE_URL}/api/auth/callback`, {
            method: "POST", headers, body
          })
          const data = await res.json()

          if (data.status === "success") {
            const user = data.user_id
            localStorage.setItem("tfg_user_id", user)
            setUserId(user)
            window.history.replaceState({}, document.title, "/")
          } else {
            alert("Error login Google")
          }
        } catch (e) {
          alert("Error de conexión callback")
        }
        setIsProcessing(false)
        return
      }

      const savedUser = localStorage.getItem("tfg_user_id")
      if (savedUser) {
        // Verificar que el usuario tiene credenciales válidas en el backend
        try {
          const res = await fetch(`${API_BASE_URL}/api/auth/login?user_id=${savedUser}`)
          const data = await res.json()
          if (data.status === "success") {
            setUserId(savedUser)
          } else {
            // Token expirado o inválido, limpiar y pedir login
            localStorage.removeItem("tfg_user_id")
          }
        } catch (e) {
          // Error de conexión, intentar usar el usuario guardado de todos modos
          setUserId(savedUser)
        }
      }
      setIsProcessing(false)
    }

    checkAuth()
  }, [])

  // 2. CARGAR PREFERENCIAS ANTIGUAS
  useEffect(() => {
    if (userId) {
      fetch(`${API_BASE_URL}/api/preferences?user_id=${userId}`)
        .then(res => res.json())
        .then(data => {
          setPrefsText(data.preferences || "")
        })
        .catch(err => console.error("Error cargando prefs", err))
    }
  }, [userId])

  // 3. GUARDAR
  const handleSavePrefs = async () => {
    if (!userId) return
    setIsSavingPrefs(true)
    try {
      await fetch(`${API_BASE_URL}/api/preferences`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, text: prefsText })
      })
      setShowPrefs(false)
      alert("Preferencias actualizadas")
    } catch (e) {
      alert("Error al guardar preferencias.")
    }
    setIsSavingPrefs(false)
  }

  const handleLogout = () => {
    localStorage.removeItem("tfg_user_id")
    setUserId(null)
  }

  if (isProcessing) return <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center' }}>Cargando...</div>

  if (!userId) {
    return <LoginScreen onLogin={() => {
      const u = localStorage.getItem("tfg_user_id")
      if (u) setUserId(u)
    }} />
  }

  return (
    <div className="layout-dashboard">

      {/* PREFERENCIAS */}
      {showPrefs && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
          backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 9999,
          display: 'flex', justifyContent: 'center', alignItems: 'center'
        }}>
          <div className="card" style={{
            width: '500px',
            maxWidth: '95%',
            padding: '30px',
            display: 'flex', flexDirection: 'column', gap: '18px',
            boxShadow: '0 25px 50px rgba(0,0,0,0.25)',
            borderRadius: '16px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 600 }}>⚙️ Preferencias</h3>
              <button
                onClick={() => setShowPrefs(false)}
                style={{
                  background: '#f3f4f6',
                  border: 'none',
                  fontSize: '1rem',
                  cursor: 'pointer',
                  color: '#6b7280',
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >✕</button>
            </div>

            <p style={{ fontSize: '0.9rem', color: '#6b7280', lineHeight: '1.5', margin: 0 }}>
              Define instucciones y preferencias que el asistente tendrá en cuenta al gestionar tu agenda.
            </p>

            <textarea
              rows={6}
              value={prefsText}
              onChange={(e) => setPrefsText(e.target.value)}
              placeholder="Ejemplos de preferencias:&#10;&#10; - Trabajo de 9:00 a 18:00&#10; - Prefiero gimnasio por la tarde&#10; - No reuniones los viernes&#10; - Descansos de 15 min entre eventos"
              style={{
                width: '100%',
                padding: '14px',
                borderRadius: '10px',
                border: '2px solid #e5e7eb',
                resize: 'vertical',
                fontFamily: 'inherit',
                fontSize: '0.95rem',
                lineHeight: '1.6',
                transition: 'border-color 0.2s',
                outline: 'none',
                boxSizing: 'border-box'
              }}
              onFocus={(e) => e.currentTarget.style.borderColor = '#93c5fd'}
              onBlur={(e) => e.currentTarget.style.borderColor = '#e5e7eb'}
            />

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowPrefs(false)}
                style={{
                  padding: '10px 20px',
                  background: 'transparent',
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  color: '#4b5563',
                  fontWeight: 500
                }}>
                Cancelar
              </button>
              <button
                onClick={handleSavePrefs}
                disabled={isSavingPrefs}
                style={{
                  padding: '10px 24px',
                  background: '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  opacity: isSavingPrefs ? 0.7 : 1,
                  boxShadow: '0 2px 4px rgba(37,99,235,0.3)'
                }}
              >
                {isSavingPrefs ? "Guardando..." : "Guardar"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CHAT */}
      <div className={`card ${activeTab === 'chat' ? 'active-mobile' : 'hidden-mobile'}`} style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Asistente</h3>

          <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
            <button
              onClick={() => setShowPrefs(true)}
              title="Configurar Preferencias"
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.4rem' }}
            >
              ⚙️
            </button>
            <button
              onClick={handleLogout}
              title="Cerrar Sesión"
              style={{
                border: '1px solid #e5e7eb',
                background: '#f9fafb',
                cursor: 'pointer',
                fontSize: '0.75rem',
                color: '#6b7280',
                padding: '6px 12px',
                borderRadius: '6px',
                fontWeight: 500,
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#fee2e2';
                e.currentTarget.style.borderColor = '#fca5a5';
                e.currentTarget.style.color = '#dc2626';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#f9fafb';
                e.currentTarget.style.borderColor = '#e5e7eb';
                e.currentTarget.style.color = '#6b7280';
              }}
            >
              Cerrar Sesión
            </button>
          </div>

        </div>
        <ChatInterface userId={userId} />
      </div>

      {/* CALENDARIO */}
      <div className={`card ${activeTab === 'calendar' ? 'active-mobile' : 'hidden-mobile'}`} style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h3 style={{ margin: 0 }}>Calendario</h3>
          {isCalendarLoading && (
            <span style={{ color: '#9CA3AF', flex: 1, textAlign: 'center' }}>Cargando...</span>
          )}
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
        <div style={{ flex: 1, minHeight: 0 }}>
          <CalendarView
            userId={userId}
            onLoadingChange={setIsCalendarLoading}
          />
        </div>
      </div>

      {/* EVENTOS Y ESTADÍSTICAS  */}
      <div className={`right-column ${activeTab === 'stats' ? 'active-mobile' : 'hidden-mobile'}`} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--separacion)', overflow: 'hidden' }}>
        <div className="card" style={{ flex: 5, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 15px 0', flexShrink: 0 }}>Próximos Eventos</h3>
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            <UpcomingEvents userId={userId} />
          </div>
        </div>

        <div className="card" style={{ flex: 5, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 10px 0', flexShrink: 0 }}>Recomendaciones semana</h3>
          <StatsInterface userId={userId} />
        </div>
      </div>

      {/* NUEVO: BARRA DE NAVEGACIÓN MÓVIL */}
      <nav className="mobile-nav">
        <button onClick={() => setActiveTab('chat')} className={activeTab === 'chat' ? 'active' : ''}>
          💬 <span>Asistente</span>
        </button>
        <button onClick={() => setActiveTab('calendar')} className={activeTab === 'calendar' ? 'active' : ''}>
          📅 <span>Calendario</span>
        </button>
        <button onClick={() => setActiveTab('stats')} className={activeTab === 'stats' ? 'active' : ''}>
          📊 <span>Stats</span>
        </button>
      </nav>

    </div>
  )
}

export default App
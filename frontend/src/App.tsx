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
    if (!email) return alert("Por favor introduce un email")
    setIsLoading(true)

    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login?user_id=${email}`)
      const data = await res.json()
      
      if (data.status === "success") {
        localStorage.setItem("tfg_user_id", email)
        onLogin()
      } else {
        const redirectUri = window.location.origin 
        const urlRes = await fetch(`${API_BASE_URL}/api/auth/url?redirect_uri=${redirectUri}&login_hint=${email}`)
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
        <p style={{ color: '#666', textAlign: 'center' }}>Inicia sesión</p>
        <input
          type="email" placeholder="email@gmail.com" value={email}
          onChange={e => setEmail(e.target.value)}
          style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #ddd' }}
        />
        <button
          onClick={handleLogin} disabled={isLoading}
          style={{
            width: '100%', padding: '12px', background: '#2563eb', color: 'white',
            border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold'
          }}
        >
          {isLoading ? "Verificando..." : "Iniciar Sesión con Google"}
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

  // --- NUEVO: ESTADO PARA PESTAÑAS EN MÓVIL ---
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
      if (savedUser) setUserId(savedUser)
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
      alert("✅Preferencias actualizadas")
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
            width: '600px', 
            maxWidth: '95%', 
            padding: '40px', 
            display: 'flex', flexDirection: 'column', gap: '15px',
            boxShadow: '0 20px 50px rgba(0,0,0,0.3)',
            borderRadius: '12px'
          }}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                <h3 style={{margin:0, fontSize:'1.3rem'}}>⚙️ Mis Preferencias</h3>
                <button onClick={() => setShowPrefs(false)} style={{background:'none', border:'none', fontSize:'1.5rem', cursor:'pointer', color:'#666'}}>✕</button>
            </div>
            
            <p style={{fontSize: '0.95rem', color: '#555', lineHeight:'1.5'}}>
              Escribe aquí tus preferencias e instrucciones fijas para el asistente
            </p>
            
            <textarea
              rows={8}
              value={prefsText}
              onChange={(e) => setPrefsText(e.target.value)}
              placeholder="Ejemplo:&#10;- Trabajo de 9:00 a 18:00&#10;- Los viernes salgo a las 15:00&#10;- No me pongas reuniones los viernes&#10;- Prefiero ir al gimnasio por la tarde&#10;- ..."
              style={{ 
                width: '100%', padding: '10px', borderRadius: '8px', 
                border: '1px solid #ccc', resize: 'vertical', fontFamily: 'inherit',
                fontSize: '1rem', lineHeight: '1.5'
              }}
            />

            <div style={{ display: 'flex', gap: '15px', justifyContent: 'flex-end', marginTop: '10px' }}>
              <button 
                onClick={() => setShowPrefs(false)} 
                style={{ padding: '10px 20px', background: 'transparent', border: '1px solid #ccc', borderRadius: '6px', cursor: 'pointer', fontSize:'0.95rem' }}>
                Cancelar
              </button>
              <button 
                onClick={handleSavePrefs}
                disabled={isSavingPrefs}
                style={{ 
                  padding: '10px 20px', background: '#2563eb', color: 'white', 
                  border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight:'bold', 
                  fontSize:'0.95rem', opacity: isSavingPrefs ? 0.7 : 1 
                }}
              >
                {isSavingPrefs ? "Guardando..." : "Guardar Cambios"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CHAT - Clases añadidas para móvil */}
      <div className={`card ${activeTab === 'chat' ? 'active-mobile' : 'hidden-mobile'}`} style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Asistente</h3>
          
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button 
                onClick={() => setShowPrefs(true)}
                title="Configurar Preferencias"
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.4rem' }}
            >
                ⚙️
            </button>
            <button onClick={handleLogout} style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: '0.8rem', color: '#ef4444' }}>
                Cerrar Sesión
            </button>
          </div>

        </div>
        <ChatInterface userId={userId} />
      </div>

      {/* CALENDARIO - Clases añadidas para móvil */}
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

      {/* EVENTOS Y ESTADÍSTICAS - Clases añadidas para móvil */}
      <div className={`right-column ${activeTab === 'stats' ? 'active-mobile' : 'hidden-mobile'}`} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--separacion)', overflow: 'hidden' }}>
        <div className="card" style={{ flex: 5, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 15px 0', flexShrink: 0 }}>Próximos Eventos</h3>
          <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
            <UpcomingEvents userId={userId} />
          </div>
        </div>

        <div className="card" style={{ flex: 5, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ margin: '0 0 10px 0', flexShrink: 0 }}>Recomendaciones</h3>
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
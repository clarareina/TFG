import { useState, useEffect } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import CalendarView from './components/CalendarInterface'
import UpcomingEvents from './components/EventsInterface'
import StatsInterface from './components/StatsInterface'

// 1. Miramos si en el navegador pone "localhost"
const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

// 2. Elegimos la URL correcta automáticamente
// exportamos esta variable para otros archivos
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
        // Si no tiene sesión, pedimos la URL de Google
        // window.location.origin detecta automáticamente si es localhost:5173 o tu web en la nube
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
        <p style={{ color: '#666', textAlign: 'center' }}>
          Inicia sesión
        </p>

        <input
          type="email"
          placeholder="email@gmail.com"
          value={email}
          onChange={e => setEmail(e.target.value)}
          style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #ddd' }}
        />

        <button
          onClick={handleLogin}
          disabled={isLoading}
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

  useEffect(() => {
    const checkAuth = async () => {
      const params = new URLSearchParams(window.location.search)
      const code = params.get("code")

      if (code) {
        try {
          const body = JSON.stringify({
            code,
            redirect_uri: window.location.origin // Esto vale para local y nube
          })
          
          const headers = { "Content-Type": "application/json" }
          
          // USAMOS LA URL AUTOMÁTICA
          const res = await fetch(`${API_BASE_URL}/api/auth/callback`, {
            method: "POST",
            headers,
            body
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
        setUserId(savedUser)
      }
      setIsProcessing(false)
    }

    checkAuth()
  }, [])

  const handleLogout = () => {
    localStorage.removeItem("tfg_user_id")
    setUserId(null)
  }

  if (isProcessing) {
    return <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center' }}>Cargando...</div>
  }

  if (!userId) {
    return <LoginScreen onLogin={() => {
      const u = localStorage.getItem("tfg_user_id")
      if (u) setUserId(u)
    }} />
  }

  return (
    <div className="layout-dashboard">

      {/* CHAT */}
      <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Asistente</h3>
          <button onClick={handleLogout} style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: '0.8rem', color: '#ef4444' }}>Cerrar Sesión</button>
        </div>
        <ChatInterface userId={userId} />
      </div>

      {/* CALENDARIO */}
      <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
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

      {/* EVENTOS Y ESTADÍSTICAS */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--separacion)', overflow: 'hidden' }}>
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
    </div>
  )
}

export default App
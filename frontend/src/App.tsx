import { useState, useEffect } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import CalendarView from './components/CalendarInterface'
import UpcomingEvents from './components/EventsInterface'
import StatsInterface from './components/StatsInterface'



const LoginScreen = ({ onLogin }: { onLogin: () => void }) => {
  const [email, setEmail] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleLogin = async () => {
    if (!email) return alert("Por favor introduce un email")
    setIsLoading(true)

    try {
      // 1. Verificar si ya existe sesión
      const res = await fetch(`http://localhost:8000/api/auth/login?user_id=${email}`)
      const data = await res.json()

      if (data.status === "success") {
        // Ya tiene sesión válida
        localStorage.setItem("tfg_user_id", email)
        onLogin()
      } else {
        // 2. No tiene sesión, iniciar OAuth
        const redirectUri = window.location.origin // http://localhost:5173
        const urlRes = await fetch(`http://localhost:8000/api/auth/url?redirect_uri=${redirectUri}&login_hint=${email}`)
        const urlData = await urlRes.json()

        // Redirigir a Google
        window.location.href = urlData.url
      }
    } catch (e) {
      alert("Error conectando con el servidor")
      setIsLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center',
      backgroundColor: '#f3f4f6', flexDirection: 'column', gap: '20px'
    }}>
      <div className="card" style={{ width: '400px', alignItems: 'center', gap: '20px' }}>
        <h2>TFG Agent 🤖</h2>
        <p style={{ color: '#666', textAlign: 'center' }}>
          Inicia sesión para gestionar tu calendario
        </p>

        <input
          type="email"
          placeholder="tu_email@gmail.com"
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
  const [isProcessing, setIsProcessing] = useState(true) // Cargando inicial

  useEffect(() => {
    const checkAuth = async () => {
      // 1. Verificar si venimos de Google con un code
      const params = new URLSearchParams(window.location.search)
      const code = params.get("code")

      if (code) {
        // Estamos volviendo de Google
        try {
          const res = await fetch("http://localhost:8000/api/auth/callback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              code,
              redirect_uri: window.location.origin
            })
          })
          const data = await res.json()

          if (data.status === "success") {
            const user = data.user_id
            localStorage.setItem("tfg_user_id", user)
            setUserId(user)
            // Limpiar URL
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

      // 2. Si no hay code, mirar si tenemos usuario guardado en LocalStorage
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

  // PANTALLA PRINCIPAL (DASHBOARD)
  return (
    <div className="layout-dashboard">

      {/* COLUMNA 1: CHAT */}
      <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Asistente</h3>
          <button onClick={handleLogout} style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: '0.8rem', color: '#ef4444' }}>Cerrar Sesión</button>
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
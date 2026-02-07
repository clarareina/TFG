import { useState, useRef, useEffect } from 'react'
import type { KeyboardEvent } from 'react'
import { API_BASE_URL } from '../App'

interface ChatProps {
  userId: string | null;
}

interface Message {
  id: number
  text: string
  sender: 'user' | 'bot'
}

const ChatInterface = ({ userId }: ChatProps) => {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, text: 'Hola. ¿En qué puedo ayudarte?', sender: 'bot' }
  ])

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  // Formateador simple de negritas y saltos de línea
  const formatMarkdown = (text: string): string => {
    return text
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>') // Negrita
      .replace(/\*(.+?)\*/g, '<em>$1</em>')             // Cursiva
      .replace(/\n/g, '<br>')                            // Saltos de línea
  }

  useEffect(scrollToBottom, [messages])

  // Estado para el mensaje de carga dinámico
  const [loadingMessage, setLoadingMessage] = useState("Pensando...")

  const handleSend = async () => {
    if (!input.trim() || !userId) return

    // 1. Guardamos y mostramos el mensaje del usuario
    const userText = input
    setInput('')

    const userMsg: Message = { id: Date.now(), text: userText, sender: 'user' }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)
    setLoadingMessage("Pensando...") // Mensaje inicial

    try {
      // STREAMING CON SERVER-SENT EVENTS (SSE)
      // En lugar de esperar toda la respuesta, recibimos actualizaciones
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userText,
          user_id: userId
        })
      })

      if (!response.ok) throw new Error('Error en el servidor')
      if (!response.body) throw new Error('No hay body en la respuesta')

      // Leer el stream de respuestas
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let finalData: { status?: string; response?: string; calendar_modified?: boolean } | null = null

      // Bucle para leer cada chunk del stream
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // Decodificar el chunk de bytes a texto
        const text = decoder.decode(value)

        // Puede haber múltiples líneas "data: {...}" en un chunk
        const lines = text.split('\n').filter(line => line.startsWith('data: '))

        for (const line of lines) {
          try {
            // Parsear el JSON (quitar "data: " del inicio)
            const jsonStr = line.replace('data: ', '')
            const update = JSON.parse(jsonStr)

            if (update.type === 'progress') {
              // Actualizar el mensaje de carga con el progreso actual
              setLoadingMessage(update.message)
            } else if (update.type === 'response') {
              // Respuesta final del agente
              finalData = update.data
            }
          } catch (e) {
            // Ignorar líneas que no son JSON válido
          }
        }
      }

      // Mostrar la respuesta del bot
      if (finalData) {
        const botMsg: Message = {
          id: Date.now() + 1,
          text: finalData.response || 'Sin respuesta',
          sender: 'bot'
        }
        setMessages(prev => [...prev, botMsg])

        // Recargar calendario si el backend indica que hubo modificación
        if (finalData.calendar_modified) {
          setTimeout(() => {
            window.dispatchEvent(new CustomEvent('calendarUpdated', { bubbles: true }))
          }, 100)
        }
      }

    } catch (error) {
      console.error(error)
      const errorMsg: Message = {
        id: Date.now() + 1,
        text: 'Error: No puedo conectar con el servidor.',
        sender: 'bot'
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
      setLoadingMessage("Pensando...") // Reset para la próxima vez
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isLoading) handleSend()
  }

  return (
    <div className="chat-container">

      {/* ZONA DE MENSAJES */}
      <div className="messages-area">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`message-bubble ${msg.sender === 'user' ? 'user' : 'bot'}`}
          >
            {msg.sender === 'bot' ? (
              <span dangerouslySetInnerHTML={{ __html: formatMarkdown(msg.text) }} />
            ) : (
              msg.text
            )}
          </div>
        ))}

        {/* Sugerencias rápidas cuando el chat está vacío */}
        {messages.length === 1 && !isLoading && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            marginTop: '20px',
            alignItems: 'flex-end',
            paddingRight: '10px'
          }}>
            {[
              '📅 Crear evento',
              '🔍 Buscar hueco libre',
              '✏️ Modificar evento',
              '🗑️ Eliminar evento',
              '📊 Resumen semanal'
            ].map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => {
                  const queries = [
                    'Crea un evento ',
                    'Busca un hueco para ',
                    'Modifica el evento ',
                    'Elimina el evento ',
                    'Resúmeme la semana'
                  ];
                  setInput(queries[idx]);
                }}
                style={{
                  padding: '10px 16px',
                  fontSize: '0.85rem',
                  background: '#2563eb',
                  border: 'none',
                  borderRadius: '18px',
                  cursor: 'pointer',
                  color: 'white',
                  fontWeight: 500,
                  transition: 'all 0.2s',
                  boxShadow: '0 2px 4px rgba(37,99,235,0.3)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#1d4ed8';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 4px 8px rgba(37,99,235,0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#2563eb';
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 2px 4px rgba(37,99,235,0.3)';
                }}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {isLoading && (
          <div className="message-bubble bot" style={{ opacity: 0.7 }}>
            {loadingMessage}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ZONA DE INPUT */}
      <div className="input-wrapper">
        <input
          type="text"
          placeholder={isLoading ? "Esperando respuesta..." : "Escribe un mensaje..."}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading || !userId}
        />
        <button onClick={handleSend} disabled={isLoading || !userId}>
          ➤
        </button>
      </div>

    </div>
  )
}

export default ChatInterface
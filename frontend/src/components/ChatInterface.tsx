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
  const [loadingMessage, setLoadingMessage] = useState("Pensando...")
  const [streamText, setStreamText] = useState("")
  const [dotCount, setDotCount] = useState(1)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const formatMarkdown = (text: string): string => {
    return text
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>')
  }

  useEffect(scrollToBottom, [messages])
  useEffect(scrollToBottom, [streamText, loadingMessage])

  // Animar los puntos suspensivos mientras carga
  useEffect(() => {
    if (!isLoading) return
    const interval = setInterval(() => {
      setDotCount(prev => prev >= 3 ? 1 : prev + 1)
    }, 400)
    return () => clearInterval(interval)
  }, [isLoading])

  const handleSend = async () => {
    if (!input.trim() || !userId) return

    const userText = input
    setInput('')

    const userMsg: Message = { id: Date.now(), text: userText, sender: 'user' }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)
    setLoadingMessage("Pensando...")
    setStreamText("")
    setDotCount(1)

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userText, user_id: userId })
      })

      if (!response.ok) throw new Error('Error en el servidor')
      if (!response.body) throw new Error('No hay body en la respuesta')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let finalData: { status?: string; response?: string; calendar_modified?: boolean } | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n').filter(line => line.startsWith('data: '))

        for (const line of lines) {
          try {
            const update = JSON.parse(line.replace('data: ', ''))

            if (update.type === 'progress') {
              setLoadingMessage(update.message)
              setStreamText("")
            } else if (update.type === 'stream_chunk') {
              setStreamText(prev => update.text === "\n" ? "" : prev + update.text)
            } else if (update.type === 'response') {
              finalData = update.data
            }
          } catch (e) {
            // ignorar líneas no JSON
          }
        }
      }

      if (finalData) {
        const botMsg: Message = {
          id: Date.now() + 1,
          text: finalData.response || 'Sin respuesta',
          sender: 'bot'
        }
        setMessages(prev => [...prev, botMsg])

        if (finalData.calendar_modified) {
          setTimeout(() => {
            window.dispatchEvent(new CustomEvent('calendarUpdated', { bubbles: true }))
          }, 100)
        }
      }

    } catch (error) {
      console.error(error)
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: 'Error: No puedo conectar con el servidor.',
        sender: 'bot'
      }])
    } finally {
      setIsLoading(false)
      setLoadingMessage("Pensando...")
      setStreamText("")
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isLoading) handleSend()
  }

  return (
    <div className="chat-container">

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
          <>
            {/* Bocadillo con puntos animados */}
            <div className="message-bubble bot" style={{ opacity: 0.85 }}>
              {loadingMessage.replace(/\.+$/, '')}{'.'.repeat(dotCount)}
            </div>

            {/* Espacio fijo reservado para el typewriter — no colapsa aunque esté vacío */}
            <div style={{ minHeight: '20px', paddingLeft: '8px', marginTop: '4px' }}>
              {streamText && (
                <span style={{ fontSize: '0.75rem', opacity: 0.5 }}>
                  {streamText}
                </span>
              )}
            </div>
          </>
        )}

        <div ref={messagesEndRef} />
      </div>

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
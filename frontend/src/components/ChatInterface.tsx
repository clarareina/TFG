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

  const handleSend = async () => {
    if (!input.trim() || !userId) return

    // 1. Guardamos y mostramos el mensaje del usuario
    const userText = input
    setInput('')

    const userMsg: Message = { id: Date.now(), text: userText, sender: 'user' }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userText,
          user_id: userId
        })
      })

      if (!response.ok) throw new Error('Error en el servidor')

      const data = await response.json()

      // 3. Mostrar respuesta del Bot
      const botMsg: Message = {
        id: Date.now() + 1,
        text: data.response,
        sender: 'bot'
      }
      setMessages(prev => [...prev, botMsg])

      // 4. Actualizar el calendario SOLO si el asistente hizo cambios
      if (data.calendar_modified) {
        setTimeout(() => {
          window.dispatchEvent(new CustomEvent('calendarUpdated', { bubbles: true }))
        }, 100)
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

        {isLoading && (
          <div className="message-bubble bot" style={{ opacity: 0.7 }}>
            Pensando...
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
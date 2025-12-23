import { useState, useRef, useEffect } from 'react'
import type { KeyboardEvent } from 'react'

interface Message {
  id: number
  text: string
  sender: 'user' | 'bot'
}

const ChatInterface = () => {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false) // Para saber si está "pensando"
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, text: 'Hola. ¿En qué puedo ayudarte?', sender: 'bot' }
  ])

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  // Función para formatear Markdown básico a HTML
  const formatMarkdown = (text: string): string => {
    return text
      // Convertir **texto** a negrita
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // Convertir *texto* a cursiva
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      // Convertir saltos de línea a <br>
      .replace(/\n/g, '<br>')
  }

  useEffect(scrollToBottom, [messages])

  const handleSend = async () => {
    if (!input.trim()) return

    // 1. Guardamos el texto y limpiamos el input
    const userText = input
    setInput('')

    // 2. Pintamos TU mensaje 
    const userMsg: Message = { id: Date.now(), text: userText, sender: 'user' }
    setMessages(prev => [...prev, userMsg])

    // 3. Activamos modo "cargando"
    setIsLoading(true)

    try {
      // 4. LLAMADA AL BACKEND 
      const response = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userText,
          user_id: "user"
        }),
      })

      if (!response.ok) {
        throw new Error('Error en la conexión con el servidor')
      }

      const data = await response.json()

      // 5. Pintamos la respuesta del ASISTENTE
      const botMsg: Message = {
        id: Date.now() + 1,
        text: data.response,
        sender: 'bot'
      }
      setMessages(prev => [...prev, botMsg])

      // 6. Notificar a otros componentes que se actualizó el calendario
      // Usar setTimeout para asegurar que el estado del backend esté actualizado
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('calendarUpdated', { bubbles: true }))
      }, 100)

    } catch (error) {
      console.error(error)
      const errorMsg: Message = {
        id: Date.now() + 1,
        text: 'Error: No puedo conectar con el servidor (Backend apagado o error de red).',
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
        {/* Indicador de "Escribiendo..." */}
        {isLoading && (
          <div className="message-bubble bot" style={{ opacity: 0.7 }}>
            Thinking...
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
          disabled={isLoading} // Bloqueamos input mientras piensa
        />
        <button onClick={handleSend} disabled={isLoading}>
          ➤
        </button>
      </div>

    </div>
  )
}

export default ChatInterface
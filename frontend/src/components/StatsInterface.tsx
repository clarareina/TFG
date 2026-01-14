import { useEffect, useRef, useState } from 'react'

interface CalendarEvent {
    id: string
    summary: string
    start: { dateTime?: string; date?: string }
    end: { dateTime?: string; date?: string }
}

interface Stats {
    occupiedPercent: number
    freePercent: number
    freeSlots: number
}

// 1. Definimos que este componente NECESITA recibir el ID del usuario
interface StatsInterfaceProps {
    userId: string | null; // Puede ser null si aún no se ha logueado
}

const StatsInterface = ({ userId }: StatsInterfaceProps) => {
    const [stats, setStats] = useState<Stats>({
        occupiedPercent: 0,
        freePercent: 100,
        freeSlots: 0
    })
    const [recommendation, setRecommendation] = useState<string>('Esperando inicio de sesión...')
    const [isLoading, setIsLoading] = useState(false) // Empezamos en false hasta que haya usuario

    // Función para formatear Markdown básico a HTML
    const formatMarkdown = (text: string): string => {
        return text
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>')
    }

    const DIAS = 7
    const HORAS_POR_DIA = 13
    const TOTAL_HORAS = DIAS * HORAS_POR_DIA

    // Calcular estadísticas
    const calculateStats = () => {
        // Si no hay usuario, no pedimos nada para evitar error 422
        if (!userId) return 

        // Pasamos el userId en la URL
        fetch(`http://localhost:8000/api/calendar/events?user_id=${userId}`)
            .then(res => res.json())
            .then((data: CalendarEvent[]) => {
                // ... (Toda tu lógica matemática sigue igual) ...
                const now = new Date()
                now.setHours(0, 0, 0, 0)
                const endDate = new Date(now)
                endDate.setDate(now.getDate() + DIAS)
                endDate.setHours(23, 59, 59, 999)

                const upcomingEvents = data.filter(evt => {
                    if (!evt.start.dateTime) return false
                    const eventStart = new Date(evt.start.dateTime)
                    return eventStart >= now && eventStart <= endDate
                })

                let occupiedMinutes = 0
                upcomingEvents.forEach(evt => {
                    if (evt.start.dateTime && evt.end.dateTime) {
                        const start = new Date(evt.start.dateTime)
                        const end = new Date(evt.end.dateTime)
                        occupiedMinutes += (end.getTime() - start.getTime()) / (1000 * 60)
                    }
                })

                const occupiedHours = Math.round(occupiedMinutes / 60 * 10) / 10
                const freeHours = Math.max(0, TOTAL_HORAS - occupiedHours)
                const occupiedPercent = Math.min(100, Math.round((occupiedHours / TOTAL_HORAS) * 100))
                const freePercent = Math.max(0, 100 - occupiedPercent)
                const freeSlots = Math.floor(freeHours)

                setStats({ occupiedPercent, freePercent, freeSlots })
            })
            .catch(() => { })
    }

    const fetchRecommendation = async () => {
        if (!userId) return

        setIsLoading(true)
        setRecommendation('Generando resumen personalizado...')
        try {
            const response = await fetch('http://127.0.0.1:8000/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: 'Dame una recomendación o resumen para los próximos 7 días por puntos. Responde directamente con la recomendación, sin introducciones, aclaraciones ni referencias a fuentes. Máximo 4 líneas.',
                    // 2. AQUÍ ESTÁ LA CLAVE: Usamos el prop userId dinámico
                    user_id: userId 
                })
            })

            if (response.ok) {
                const data = await response.json()
                setRecommendation(data.response)
            } else {
                setRecommendation('No se pudo obtener el resumen.')
            }
        } catch {
            setRecommendation('Error al conectar con el agente.')
        } finally {
            setIsLoading(false)
        }
    }

    const requestCount = useRef(0)
    
    // 3. El useEffect ahora vigila 'userId'. Si cambia el usuario, recarga todo.
    useEffect(() => {
        if (userId) {
            calculateStats()
            fetchRecommendation()
        } else {
            setRecommendation("Por favor, inicia sesión para ver tus estadísticas.")
            setStats({ occupiedPercent: 0, freePercent: 100, freeSlots: 0 })
        }

        const handleUpdate = () => {
            if (userId) {
                console.log('[Stats] Actualizando estadísticas...')
                calculateStats()
                requestCount.current += 1
                if (requestCount.current % 5 === 0) {
                    fetchRecommendation()
                }
            }
        }

        window.addEventListener('calendarUpdated', handleUpdate)

        return () => {
            window.removeEventListener('calendarUpdated', handleUpdate)
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [userId]) // <--- Importante: Si userId cambia, se ejecuta esto de nuevo

    // SVG Donut Chart logic (sin cambios)
    const radius = 40
    const circumference = 2 * Math.PI * radius
    const occupiedDash = (stats.occupiedPercent / 100) * circumference

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '12px' }}>
            {/* Gráfico y leyenda */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px', marginTop: '10px' }}>
                <svg width="100" height="100" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r={radius} fill="none" stroke="#60A5FA" strokeWidth="12" />
                    <circle
                        cx="50" cy="50" r={radius}
                        fill="none" stroke="#EF4444" strokeWidth="12"
                        strokeDasharray={`${occupiedDash} ${circumference}`}
                        strokeLinecap="round" transform="rotate(-90 50 50)"
                    />
                </svg>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#EF4444' }}></div>
                        <span style={{ fontSize: '0.8rem', color: '#374151' }}>Ocupado {stats.occupiedPercent}%</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#60A5FA' }}></div>
                        <span style={{ fontSize: '0.8rem', color: '#374151' }}>Libre {stats.freePercent}%</span>
                    </div>
                </div>
            </div>

            {/* Resumen del agente */}
            <div style={{
                fontSize: '0.85rem', color: '#4B5563', lineHeight: '1.4',
                padding: '15px 10px', backgroundColor: '#F9FAFB',
                borderRadius: '8px', overflow: 'auto', flex: 1, minHeight: '80px'
            }}>
                {isLoading ? (
                    <span style={{ color: '#9CA3AF' }}>Generando resumen...</span>
                ) : (
                    <span dangerouslySetInnerHTML={{ __html: formatMarkdown(recommendation) }} />
                )}
            </div>
        </div>
    )
}

export default StatsInterface
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

const StatsInterface = () => {
    const [stats, setStats] = useState<Stats>({
        occupiedPercent: 0,
        freePercent: 100,
        freeSlots: 0
    })
    const [recommendation, setRecommendation] = useState<string>('Cargando resumen...')
    const [isLoading, setIsLoading] = useState(true)

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

    // Calcular estadísticas del gráfico
    const calculateStats = () => {
        fetch('http://localhost:8000/api/calendar/events')
            .then(res => res.json())
            .then((data: CalendarEvent[]) => {
                const now = new Date()
                const startOfWeek = new Date(now)
                startOfWeek.setDate(now.getDate() - now.getDay() + 1)
                startOfWeek.setHours(9, 0, 0, 0)

                const endOfWeek = new Date(startOfWeek)
                endOfWeek.setDate(startOfWeek.getDate() + 4)
                endOfWeek.setHours(18, 0, 0, 0)

                const weekEvents = data.filter(evt => {
                    if (!evt.start.dateTime) return false
                    const eventStart = new Date(evt.start.dateTime)
                    return eventStart >= startOfWeek && eventStart <= endOfWeek
                })

                let occupiedMinutes = 0
                weekEvents.forEach(evt => {
                    if (evt.start.dateTime && evt.end.dateTime) {
                        const start = new Date(evt.start.dateTime)
                        const end = new Date(evt.end.dateTime)
                        occupiedMinutes += (end.getTime() - start.getTime()) / (1000 * 60)
                    }
                })

                const totalHours = 40
                const occupiedHours = Math.round(occupiedMinutes / 60 * 10) / 10
                const freeHours = Math.max(0, totalHours - occupiedHours)
                const occupiedPercent = Math.min(100, Math.round((occupiedHours / totalHours) * 100))
                const freePercent = Math.max(0, 100 - occupiedPercent)
                const freeSlots = Math.floor(freeHours)

                setStats({ occupiedPercent, freePercent, freeSlots })
            })
            .catch(() => { })
    }

    const fetchRecommendation = async () => {
        setIsLoading(true)
        try {
            const response = await fetch('http://127.0.0.1:8000/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: 'Dame una única recomendación para esta semana por puntos. Responde directamente con la recomendación, sin introducciones, aclaraciones ni referencias a fuentes. Máximo 4 líneas.',
                    user_id: 'stats_widget'
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
    useEffect(() => {
        calculateStats()
        fetchRecommendation()

        // Escuchar cuando el chat hace cambios en el calendario
        const handleUpdate = () => {
            console.log('[Stats] Actualizando estadísticas y recomendaciones...')
            calculateStats()
            requestCount.current += 1
            if (requestCount.current % 5 === 0) {
                fetchRecommendation()
            }
        }

        window.addEventListener('calendarUpdated', handleUpdate)

        return () => {
            window.removeEventListener('calendarUpdated', handleUpdate)
        }
    }, [])

    // SVG Donut Chart
    const radius = 40
    const circumference = 2 * Math.PI * radius
    const freeDash = (stats.freePercent / 100) * circumference

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '12px' }}>

            {/* Gráfico y leyenda */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px', marginTop: '10px' }}>

                <svg width="100" height="100" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r={radius} fill="none" stroke="#EF4444" strokeWidth="12" />
                    <circle
                        cx="50" cy="50" r={radius}
                        fill="none" stroke="#60A5FA" strokeWidth="12"
                        strokeDasharray={`${freeDash} ${circumference}`}
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
                fontSize: '0.85rem',
                color: '#4B5563',
                lineHeight: '1.4',
                padding: '15px 10px',
                backgroundColor: '#F9FAFB',
                borderRadius: '8px',
                overflow: 'auto',
                flex: 1,
                minHeight: '80px'
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

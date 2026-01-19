import { useEffect, useState } from 'react'
import { API_BASE_URL } from '../App'

interface EventsProps {
    userId: string | null;
}

interface CalendarEvent {
    id: string
    summary: string
    start: { dateTime?: string; date?: string }
    end: { dateTime?: string; date?: string }
    colorId?: string
}

const UpcomingEvents = ({ userId }: EventsProps) => {
    const [events, setEvents] = useState<CalendarEvent[]>([])
    const [isLoading, setIsLoading] = useState(false)

    // Mapa de colores de Google Calendar
    const googleColors: { [key: string]: string } = {
        '1': '#7986CB', '2': '#33B679', '3': '#8E24AA', '4': '#E67C73',
        '5': '#F6BF26', '6': '#F4511E', '7': '#039BE5', '8': '#616161',
        '9': '#3F51B5', '10': '#0B8043', '11': '#D50000',
    }

    const fetchEvents = async () => {
        if (!userId) {
            setEvents([])
            return
        }

        setIsLoading(true)

        try {
            const res = await fetch(`${API_BASE_URL}/api/calendar/events?user_id=${userId}`)
            
            if (!res.ok) throw new Error("Error al cargar eventos")
            
            const data: CalendarEvent[] = await res.json()

            // PROCESAMIENTO DE DATOS (Igual que antes)
            const now = new Date()
            now.setHours(0, 0, 0, 0)

            const endDate = new Date(now)
            endDate.setDate(now.getDate() + 7)
            endDate.setHours(23, 59, 59, 999)

            const upcomingEvents = data.filter(evt => {
                const eventStart = new Date(evt.start.dateTime || evt.start.date || '')
                return eventStart >= now && eventStart <= endDate
            })

            upcomingEvents.sort((a, b) => {
                const dateA = new Date(a.start.dateTime || a.start.date || '')
                const dateB = new Date(b.start.dateTime || b.start.date || '')
                return dateA.getTime() - dateB.getTime()
            })

            setEvents(upcomingEvents)

        } catch (error) {
            console.error("Error cargando eventos:", error)
            setEvents([])
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        fetchEvents()

        const handleCalendarUpdate = () => {
            console.log('[UpcomingEvents] Actualizando eventos...')
            fetchEvents()
        }

        window.addEventListener('calendarUpdated', handleCalendarUpdate)

        return () => {
            window.removeEventListener('calendarUpdated', handleCalendarUpdate)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [userId])

    const formatDate = (evt: CalendarEvent) => {
        const date = new Date(evt.start.dateTime || evt.start.date || '')
        const options: Intl.DateTimeFormatOptions = { weekday: 'short', day: 'numeric', month: 'short' }
        const dateStr = date.toLocaleDateString('es-ES', options)

        if (evt.start.dateTime) {
            const timeStr = date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
            return `${dateStr} · ${timeStr}`
        }
        return `${dateStr} · Todo el día`
    }

    const getColor = (colorId?: string) => {
        return colorId ? (googleColors[colorId] || '#039BE5') : '#039BE5'
    }

    if (!userId) {
        return (
            <div style={{ padding: '20px', textAlign: 'center', color: '#9CA3AF', fontSize: '0.9rem' }}>
                Esperando inicio de sesión...
            </div>
        )
    }

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            overflowY: 'auto',
            height: '100%',
            minHeight: 0
        }}>
            {isLoading ? (
                <p style={{ color: '#9CA3AF', textAlign: 'center', marginTop: '20px', fontSize: '0.9rem' }}>
                    Cargando eventos...
                </p>
            ) : events.length === 0 ? (
                <p style={{ color: '#888', textAlign: 'center', marginTop: '20px', fontSize: '0.9rem' }}>
                    No hay eventos en los próximos 7 días
                </p>
            ) : (
                events.map((evt, index) => (
                    <div
                        key={evt.id || index}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            padding: '10px 12px',
                            backgroundColor: '#f9fafb',
                            borderRadius: '10px',
                            borderLeft: `4px solid ${getColor(evt.colorId)}`,
                        }}
                    >
                        <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#1f2937' }}>
                                {evt.summary || 'Sin título'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '2px' }}>
                                {formatDate(evt)}
                            </div>
                        </div>
                    </div>
                ))
            )}
        </div>
    )
}

export default UpcomingEvents
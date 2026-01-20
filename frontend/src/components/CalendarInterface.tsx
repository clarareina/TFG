import { useEffect, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import { API_BASE_URL } from '../App'

interface CalendarViewProps {
  userId: string | null;
  onLoadingChange?: (isLoading: boolean) => void
}

const CalendarView = ({ userId, onLoadingChange }: CalendarViewProps) => {
  const [events, setEvents] = useState([])

  const googleColors: { [key: string]: string } = {
    '1': '#7986CB', '2': '#33B679', '3': '#8E24AA', '4': '#E67C73',
    '5': '#F6BF26', '6': '#F4511E', '7': '#039BE5', '8': '#616161',
    '9': '#3F51B5', '10': '#0B8043', '11': '#D50000',
  }

  const fetchEvents = async () => {
    // Si no hay userId eliminar eventos y parar
    if (!userId) {
      setEvents([])
      return
    }

    onLoadingChange?.(true)

    try {
      const res = await fetch(`${API_BASE_URL}/api/calendar/events?user_id=${userId}`)

      if (!res.ok) throw new Error("Error al obtener eventos")

      const data = await res.json()

      // 3. FORMATEAR DATOS
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const formattedEvents = data.map((evt: any) => {
        const colorId = evt.colorId
        const defaultColor = '#036ce5ff'
        const bgColor = colorId ? (googleColors[colorId] || defaultColor) : defaultColor

        return {
          title: evt.summary || 'Evento',
          start: evt.start.dateTime || evt.start.date,
          end: evt.end.dateTime || evt.end.date,
          backgroundColor: bgColor,
          borderColor: 'transparent',
          textColor: 'white'
        }
      })
      setEvents(formattedEvents)

    } catch (error) {
      console.error("Error cargando calendario:", error)
      setEvents([])
    } finally {
      onLoadingChange?.(false)
    }
  }

  useEffect(() => {
    fetchEvents()

    const handleUpdate = () => {
      console.log('[Calendar] Actualizando eventos...')
      fetchEvents()
    }
    window.addEventListener('calendarUpdated', handleUpdate)

    return () => {
      window.removeEventListener('calendarUpdated', handleUpdate)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId])

  return (
    <div style={{ height: '100%', width: '100%', background: 'white' }}>

      <style>{`
        /* 1. CABECERA CENTRADA CON FLECHAS FIJAS */
        .fc-header-toolbar > div:first-child {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 10px !important;
            width: 100% !important;
        }

        /* 2. TÍTULO CON ANCHO FIJO */
        .fc-toolbar-title {
          font-size: 1.1rem !important;
          font-weight: 700 !important;
          color: #374151;
          margin: 0 !important;
          white-space: nowrap !important;
          width: 160px !important;
          text-align: center !important;
        }

        /* 3. FLECHAS */
        .fc-button-primary {
          display: inline-flex !important;
          background: transparent !important;
          border: 1px solid #e5e7eb !important;
          color: #555 !important;
          width: 28px !important;
          height: 28px !important;
          border-radius: 50% !important; 
          padding: 0 !important;
          align-items: center !important;
          justify-content: center !important;
          margin: 0 !important;
        }
        .fc-button-primary:hover {
          background-color: #f3f4f6 !important;
          color: black !important;
          border-color: #d1d5db !important;
        }
        .fc-button:focus { box-shadow: none !important; }

        /* --- 4. ESTILO DE LOS EVENTOS --- */
        .fc-event {
            cursor: pointer;
            font-size: 0.7rem !important;
            line-height: 1.2 !important;
            border-radius: 4px !important;
            padding: 1px 3px !important;
            font-weight: 500 !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
        }
        
        .fc-event:hover {
            transform: scale(1.02);
            box-shadow: 0 2px 4px rgba(0,0,0,0.15) !important;
        }
        
        .fc-event-title {
            font-weight: 600 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }

        /* Números de día más grandes y visibles */
        .fc-daygrid-day-number {
            font-size: 1rem !important;
            font-weight: 600 !important;
            color: #374151 !important;
            padding: 8px !important;
        }
        
        /* Día actual resaltado */
        .fc-day-today .fc-daygrid-day-number {
            background: #2563eb !important;
            color: white !important;
            border-radius: 50% !important;
            width: 28px !important;
            height: 28px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        /* Ajustes generales cabecera */
        .fc-header-toolbar {
          margin-bottom: 15px !important;
          padding-top: 5px;
          display: flex !important;
          justify-content: space-between !important;
          align-items: center !important;
        }
        .fc-col-header-cell-cushion { font-weight: 700; color: #6b7280; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.5px; }
        .fc-theme-standard td, .fc-theme-standard th { border-color: #e5e7eb !important; }
        
        /* Altura uniforme para todas las filas */
        .fc-daygrid-body tr {
          height: 16.66% !important; 
        }
        .fc-daygrid-day-frame {
          min-height: auto !important;
          height: 100% !important;
        }
        .fc-daygrid-day-events {
          overflow: hidden !important;
          padding: 2px !important;
        }
        
        /* Tooltip para eventos cortados */
        .fc-event[title] {
          position: relative;
        }
        
      `}</style>

      <FullCalendar
        plugins={[dayGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        firstDay={1}
        locale="es"
        height="100%"
        eventDisplay="block"
        dayMaxEvents={2}
        headerToolbar={{ left: 'prev title next', center: '', right: '' }}
        buttonText={{ prev: '‹', next: '›' }}
        fixedWeekCount={false}
        showNonCurrentDates={false}
        events={events}
      />
    </div>
  )
}

export default CalendarView
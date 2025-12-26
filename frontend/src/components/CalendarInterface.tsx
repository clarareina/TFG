import { useEffect, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'

interface CalendarViewProps {
  onLoadingChange?: (isLoading: boolean) => void
}

const CalendarView = ({ onLoadingChange }: CalendarViewProps) => {
  const [events, setEvents] = useState([])

  // Mapa de colores de Google Calendar (colorId -> hex)
  const googleColors: { [key: string]: string } = {
    '1': '#7986CB',
    '2': '#33B679',
    '3': '#8E24AA',
    '4': '#E67C73',
    '5': '#F6BF26',
    '6': '#F4511E',
    '7': '#039BE5',
    '8': '#616161',
    '9': '#3F51B5',
    '10': '#0B8043',
    '11': '#D50000',
  }

  const fetchEvents = () => {
    onLoadingChange?.(true)
    fetch('http://localhost:8000/api/calendar/events')
      .then(res => res.json())
      .then(data => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const formattedEvents = data.map((evt: any) => {
          // Usar el color original de Google Calendar si existe
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
      })
      .catch(() => { })
      .finally(() => {
        onLoadingChange?.(false)
      })
  }

  useEffect(() => {
    fetchEvents()

    // Escuchar cuando el chat hace cambios en el calendario
    const handleUpdate = () => {
      console.log('[Calendar] Actualizando eventos...')
      fetchEvents()
    }
    window.addEventListener('calendarUpdated', handleUpdate)

    return () => {
      window.removeEventListener('calendarUpdated', handleUpdate)
    }
  }, [])

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
            font-size: 0.75rem !important; /* <--- TAMAÑO DE LETRA (0.75rem es pequeño) */
            line-height: 1.2 !important;    /* Altura de línea compacta */
            border-radius: 3px !important;  /* Bordes un poco redondeados */
            padding: 1px 2px !important;    /* Menos relleno interno */
        }
        
        /* Ajuste opcional para el título dentro del evento */
        .fc-event-title {
            font-weight: 500 !important;
            white-space: nowrap !important;     /* Que no salte de línea si es largo */
            overflow: hidden !important;        /* Cortar si es muy largo */
            text-overflow: ellipsis !important; /* Poner puntos suspensivos (...) */
        }

        /* Ajustes generales cabecera */
        .fc-header-toolbar {
          margin-bottom: 15px !important;
          padding-top: 5px;
          display: flex !important;
          justify-content: space-between !important;
          align-items: center !important;
        }
        .fc-col-header-cell-cushion { font-weight: 600; color: #888; text-transform: capitalize; font-size: 0.8rem; }
        .fc-theme-standard td, .fc-theme-standard th { border-color: #f3f4f6 !important; }
        
        /* Altura uniforme para todas las filas */
        .fc-daygrid-body tr {
          height: 16.66% !important; /* 100% / 6 filas máximo */
        }
        .fc-daygrid-day-frame {
          min-height: auto !important;
          height: 100% !important;
        }
        .fc-daygrid-day-events {
          overflow: hidden !important;
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
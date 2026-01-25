// @ts-nocheck
import { useEffect, useRef, useState } from 'react'
import { API_BASE_URL } from '../App'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

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

interface DistributionData {
    name: string
    value: number
    minutes: number
    [key: string]: any;
}

interface StatsInterfaceProps {
    userId: string | null;
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6B7280', '#14B8A6'];

const StatsInterface = ({ userId }: StatsInterfaceProps) => {
    const [stats, setStats] = useState<Stats>({
        occupiedPercent: 0,
        freePercent: 100,
        freeSlots: 0
    })
    const [recommendation, setRecommendation] = useState<string>('Esperando inicio de sesión...')
    const [isLoading, setIsLoading] = useState(false)

    const [showModal, setShowModal] = useState(false)
    const [distributionData, setDistributionData] = useState<DistributionData[]>([])
    const [isLoadingDist, setIsLoadingDist] = useState(false)

    const requestCount = useRef(0)

    // Formatear Markdown básico
    const formatMarkdown = (text: string): string => {
        return text
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<span>$1</span>')
            .replace(/^- /gm, '• ')
            .replace(/\n/g, '<br>')
    }

    const DIAS = 7
    const HORAS_POR_DIA = 13
    const TOTAL_HORAS = DIAS * HORAS_POR_DIA

    // Calcular estadísticas 
    const calculateStats = async () => {
        if (!userId) return

        try {
            const res = await fetch(`${API_BASE_URL}/api/calendar/events?user_id=${userId}`)
            if (!res.ok) return

            const data: CalendarEvent[] = await res.json()

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

        } catch (error) {
            console.error("Error calculando estadísticas:", error)
        }
    }

    const fetchDistribution = async () => {
        if (!userId) return
        // Si ya hay datos, no los pedimos de nuevo a menos que se fuerce la limpieza
        if (distributionData.length > 0) return

        setIsLoadingDist(true)
        try {
            const res = await fetch(`${API_BASE_URL}/api/stats/distribution?user_id=${userId}`)
            const data = await res.json()
            setDistributionData(data)
        } catch (error) {
            console.error("Error cargando distribución:", error)
        } finally {
            setIsLoadingDist(false)
        }
    }

    const handleOpenModal = () => {
        setShowModal(true)
        fetchDistribution()
    }

    const fetchRecommendation = async () => {
        if (!userId) return

        setIsLoading(true)
        try {
            const response = await fetch(`${API_BASE_URL}/api/recommendations?user_id=${userId}`)
            if (!response.ok) throw new Error("Error obteniendo recomendaciones")
            const data = await response.json()
            setRecommendation(data.recommendation || 'Sin recomendación.')
        } catch (error) {
            setRecommendation('No se pudo obtener el resumen.')
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        if (userId) {
            calculateStats()
            fetchRecommendation()
        } else {
            setRecommendation("Por favor, inicia sesión para ver tus estadísticas.")
            setStats({ occupiedPercent: 0, freePercent: 100, freeSlots: 0 })
        }

        // ESCUCHA DE ACTUALIZACIÓN DEL CALENDARIO 
        const handleCalendarUpdate = () => {
            if (userId) {
                calculateStats()
                // Limpiamos los datos de distribución para que se recalculen la próxima vez que se abra el modal
                setDistributionData([])

                requestCount.current += 1
                // Refrescamos recomendación cada 5 cambios para ahorrar peticiones
                if (requestCount.current % 5 === 0) {
                    fetchRecommendation()
                }
            }
        }

        window.addEventListener('calendarUpdated', handleCalendarUpdate)

        return () => {
            window.removeEventListener('calendarUpdated', handleCalendarUpdate)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [userId])

    const radius = 40
    const circumference = 2 * Math.PI * radius
    const occupiedDash = (stats.occupiedPercent / 100) * circumference

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '12px', position: 'relative' }}>

            {showModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
                    backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 9999,
                    display: 'flex', justifyContent: 'center', alignItems: 'center'
                }}>
                    <div className="card" style={{
                        width: '500px', maxWidth: '90%', padding: '25px',
                        backgroundColor: 'white', borderRadius: '12px',
                        display: 'flex', flexDirection: 'column', gap: '20px',
                        boxShadow: '0 10px 25px rgba(0,0,0,0.2)'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <h3 style={{ margin: 0 }}>Desglose de Tiempo Ocupado</h3>
                            <button onClick={() => setShowModal(false)} style={{ background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer' }}>✕</button>
                        </div>

                        <div style={{ height: '300px', width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                            {isLoadingDist ? (
                                <span style={{ color: '#666' }}>Analizando eventos...</span>
                            ) : distributionData.length === 0 ? (
                                <span style={{ color: '#666' }}>No hay suficientes datos.</span>
                            ) : (
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={distributionData}
                                            innerRadius={60}
                                            outerRadius={100}
                                            paddingAngle={2}
                                            dataKey="value"
                                        >
                                            {distributionData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            formatter={(value: number, name: string, props: any) => [`${value}%`, `${props.payload.name} (${props.payload.minutes} min)`]}
                                            contentStyle={{ borderRadius: '8px' }}
                                        />
                                        <Legend layout="vertical" verticalAlign="middle" align="right" />
                                    </PieChart>
                                </ResponsiveContainer>
                            )}
                        </div>
                    </div>
                </div>
            )}

            <style>
                {`
                    @keyframes rotate {
                        from { transform: rotate(-90deg); }
                        to { transform: rotate(270deg); }
                    }
                    @keyframes pulse {
                        0% { opacity: 1; }
                        50% { opacity: 0.6; }
                        100% { opacity: 1; }
                    }
                    .loader-svg {
                        animation: rotate 2s linear infinite, pulse 1.5s ease-in-out infinite;
                    }
                `}
            </style>

            <button
                onClick={handleOpenModal}
                title="Ver desglose detallado"
                style={{
                    position: 'absolute', top: '0', right: '0',
                    width: '24px', height: '24px', borderRadius: '50%',
                    border: 'none', background: '#EFF6FF', color: '#2563EB',
                    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 'bold', fontSize: '1rem', boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}
            >
                +
            </button>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px', marginTop: '10px' }}>
                <svg
                    width="100"
                    height="100"
                    viewBox="0 0 100 100"
                    className={isLoading ? 'loader-svg' : ''}
                >
                    <circle cx="50" cy="50" r={radius} fill="none" stroke="#60A5FA" strokeWidth="12" />
                    <circle
                        cx="50" cy="50" r={radius}
                        fill="none" stroke="#EF4444" strokeWidth="12"
                        strokeDasharray={`${occupiedDash} ${circumference}`}
                        strokeLinecap="round"
                        transform={isLoading ? "" : "rotate(-90 50 50)"}
                        style={{ transition: 'stroke-dasharray 1s ease' }}
                    />
                </svg>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#EF4444' }}></div>
                        <span style={{ fontSize: '0.9rem', color: '#374151', fontWeight: 500 }}>Ocupado {stats.occupiedPercent}%</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#60A5FA' }}></div>
                        <span style={{ fontSize: '0.9rem', color: '#374151', fontWeight: 500 }}>Libre {stats.freePercent}%</span>
                    </div>
                </div>
            </div>

            <div style={{
                fontSize: '0.95rem', color: '#374151', lineHeight: '1.6',
                padding: '16px', backgroundColor: '#F9FAFB',
                borderRadius: '10px', overflow: 'auto', maxHeight: '140px',
                fontWeight: 450, marginBottom: '10px'
            }}>
                {isLoading ? (
                    <span style={{ color: '#9CA3AF' }}>Analizando tu agenda...</span>
                ) : (
                    <span dangerouslySetInnerHTML={{ __html: formatMarkdown(recommendation) }} />
                )}
            </div>
        </div>
    )
}

export default StatsInterface;
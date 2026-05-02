import { useState, useEffect } from 'react'
import { listarSolicitudes } from '../servicios/api'

function formatearFecha(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('es-ES', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
    timeZone: 'Europe/Madrid'
  })
}

const FILTROS = [
  { clave: 'todos',      etiqueta: 'Todos' },
  { clave: 'completada', etiqueta: 'Completadas' },
  { clave: 'en-proceso', etiqueta: 'En proceso' },
  { clave: 'error',      etiqueta: 'Error' },
]

export default function ListaSolicitudes({ onSeleccionar }) {
  const [solicitudes, setSolicitudes] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)
  const [filtro, setFiltro] = useState('todos')

  const cargar = async () => {
    setCargando(true)
    setError(null)
    try {
      const datos = await listarSolicitudes()
      setSolicitudes(datos.solicitudes)
    } catch {
      setError('No se pudo conectar con el servidor')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => { cargar() }, [])

  const solicitudesFiltradas = filtro === 'todos' ? solicitudes :
    filtro === 'en-proceso'
      ? solicitudes.filter(s => {
          const e = s.estado?.toLowerCase()
          return e !== 'completada' && e !== 'error'
        })
      : solicitudes.filter(s => s.estado?.toLowerCase() === filtro)

  const conteo = {
    todos:      solicitudes.length,
    completada: solicitudes.filter(s => s.estado?.toLowerCase() === 'completada').length,
    error:      solicitudes.filter(s => s.estado?.toLowerCase() === 'error').length,
    'en-proceso': solicitudes.filter(s => {
      const e = s.estado?.toLowerCase()
      return e !== 'completada' && e !== 'error'
    }).length,
  }

  if (cargando) {
    return <p className="lista-cargando">Cargando solicitudes...</p>
  }

  if (error) {
    return (
      <div className="lista-error">
        {error}
        <button className="boton-reintentar" onClick={cargar}>Reintentar</button>
      </div>
    )
  }

  if (solicitudes.length === 0) {
    return <p className="lista-vacia">No hay solicitudes registradas todavía.</p>
  }

  return (
    <div className="lista-solicitudes">
      <div className="lista-cabecera">
        <span className="lista-total">{solicitudes.length} solicitud{solicitudes.length !== 1 ? 'es' : ''}</span>
        <button className="boton-refrescar" onClick={cargar} title="Actualizar">↻</button>
      </div>

      <div className="filtros-historial">
        {FILTROS.map(f => (
          <button
            key={f.clave}
            className={`filtro-btn ${filtro === f.clave ? 'activo' : ''}`}
            onClick={() => setFiltro(f.clave)}
          >
            {f.etiqueta}
            {conteo[f.clave] > 0 && (
              <span className="filtro-count">{conteo[f.clave]}</span>
            )}
          </button>
        ))}
      </div>

      {solicitudesFiltradas.length === 0 ? (
        <p className="lista-vacia">Sin resultados para este filtro.</p>
      ) : (
        <div className="galeria-solicitudes">
          {solicitudesFiltradas.map(s => (
            <button
              key={s.guid}
              className="tarjeta-solicitud"
              onClick={() => onSeleccionar(s.guid)}
              title={`${s.guid}\n${formatearFecha(s.inicio)}`}
            >
              <div className="tarjeta-imagen">
                {s.url_thumbnail
                  ? <img src={s.url_thumbnail} alt="Solicitud" className="thumbnail-solicitud" />
                  : <div className="thumbnail-placeholder">Sin imagen</div>
                }
                <span className={`tarjeta-estado-badge estado-${s.estado?.toLowerCase()}`}>
                  {s.estado ?? '—'}
                </span>
              </div>
              <div className="tarjeta-info">
                <span className="tarjeta-fecha">{formatearFecha(s.inicio)}</span>
                <div className="tarjeta-caras">
                  {s.total_caras > 0
                    ? <>
                        <span className="tarjeta-badge-caras">{s.total_caras} 👤</span>
                        {s.total_menores > 0 &&
                          <span className="tarjeta-badge-menores">{s.total_menores} ⚠</span>
                        }
                      </>
                    : <span className="tarjeta-sin-caras">—</span>
                  }
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

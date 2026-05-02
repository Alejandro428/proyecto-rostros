import { useState, useRef, useEffect } from 'react'
import { subirImagen, listarSolicitudes } from '../servicios/api'
import ListaSolicitudes from './ListaSolicitudes'

const TAMANO_MAXIMO_MB = 10
const TAMANO_MAXIMO_BYTES = TAMANO_MAXIMO_MB * 1024 * 1024

const MAGIC = [
  { bytes: [0xFF, 0xD8, 0xFF],       tipo: 'JPEG' },
  { bytes: [0x89, 0x50, 0x4E, 0x47], tipo: 'PNG'  },
  { bytes: [0x42, 0x4D],             tipo: 'BMP'  },
  { bytes: [0x47, 0x49, 0x46, 0x38], tipo: 'GIF'  },
]

function detectarTipoReal(archivo) {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const b = new Uint8Array(e.target.result)
      const encontrado = MAGIC.find(({ bytes }) => bytes.every((v, i) => b[i] === v))
      resolve(encontrado ? encontrado.tipo : null)
    }
    reader.readAsArrayBuffer(archivo.slice(0, 8))
  })
}

function formatearFecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-ES', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
    timeZone: 'Europe/Madrid'
  })
}

export default function ZonaSubida({ onSubir, onBuscar }) {
  const [archivoSeleccionado, setArchivoSeleccionado] = useState(null)
  const [arrastrando, setArrastrando] = useState(false)
  const [subiendo, setSubiendo] = useState(false)
  const [error, setError] = useState(null)
  const [mostrarLista, setMostrarLista] = useState(false)
  const [cerrandoLista, setCerrandoLista] = useState(false)

  const [recientes, setRecientes] = useState([])
  const [solicitudes, setSolicitudes] = useState([])
  const [cargandoSolicitudes, setCargandoSolicitudes] = useState(false)
  const [busqueda, setBusqueda] = useState('')
  const [mostrarSugerencias, setMostrarSugerencias] = useState(false)

  const inputRef = useRef(null)
  const blurTimeoutRef = useRef(null)
  const yaCargoRef = useRef(false)

  useEffect(() => {
    listarSolicitudes(5)
      .then(d => setRecientes(d.solicitudes))
      .catch(() => {})
    return () => clearTimeout(blurTimeoutRef.current)
  }, [])

  const cargarTodasSolicitudes = async () => {
    if (yaCargoRef.current) return
    yaCargoRef.current = true
    setCargandoSolicitudes(true)
    try {
      const datos = await listarSolicitudes()
      setSolicitudes(datos.solicitudes)
    } catch { yaCargoRef.current = false }
    finally { setCargandoSolicitudes(false) }
  }

  const sugerencias = busqueda.length >= 1
    ? solicitudes.filter(s => s.guid.toLowerCase().includes(busqueda.toLowerCase())).slice(0, 6)
    : []

  const alSeleccionarSugerencia = (guid) => {
    setBusqueda('')
    setMostrarSugerencias(false)
    onBuscar(guid)
  }

  const seleccionarArchivo = async (archivo) => {
    if (archivo.size > TAMANO_MAXIMO_BYTES) {
      setError(`El archivo supera el límite de ${TAMANO_MAXIMO_MB} MB`)
      setArchivoSeleccionado(null)
      return
    }
    const tipo = await detectarTipoReal(archivo)
    if (!tipo) {
      setError('El archivo no es una imagen válida (JPEG, PNG, BMP o GIF)')
      setArchivoSeleccionado(null)
      return
    }
    setError(null)
    setArchivoSeleccionado(archivo)
  }

  const alSoltarArchivo = async (e) => {
    e.preventDefault()
    setArrastrando(false)
    const archivo = e.dataTransfer.files[0]
    if (archivo) await seleccionarArchivo(archivo)
  }

  const alCambiarInput = async (e) => {
    const archivo = e.target.files[0]
    if (archivo) await seleccionarArchivo(archivo)
  }

  const alEnviar = async () => {
    if (!archivoSeleccionado) return
    setSubiendo(true)
    setError(null)
    try {
      const respuesta = await subirImagen(archivoSeleccionado)
      onSubir(respuesta.GUID_Solicitud)
    } catch (e) {
      setError(e.message)
      setSubiendo(false)
    }
  }

  const tamanoLegible = (bytes) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="zona-subida">
      <div
        className={`zona-drop ${arrastrando ? 'arrastrando' : ''} ${archivoSeleccionado ? 'con-archivo' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setArrastrando(true) }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={alSoltarArchivo}
        onClick={() => inputRef.current.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          onChange={alCambiarInput}
          style={{ display: 'none' }}
        />
        {archivoSeleccionado ? (
          <div className="archivo-info">
            <span className="icono-archivo">🖼️</span>
            <p className="nombre-archivo">{archivoSeleccionado.name}</p>
            <p className="tamano-archivo">{tamanoLegible(archivoSeleccionado.size)}</p>
            <p className="cambiar-archivo">Haz clic para cambiar</p>
          </div>
        ) : (
          <div className="instrucciones-drop">
            <span className="icono-subida">📁</span>
            <p className="texto-principal">Arrastra una imagen aquí</p>
            <p className="texto-secundario">o haz clic para seleccionar</p>
          </div>
        )}
      </div>

      <div className="info-formatos">
        <span className="etiqueta-formatos">Formatos aceptados:</span>
        {['JPEG', 'PNG', 'BMP', 'GIF'].map(f => (
          <span key={f} className="badge-formato">{f}</span>
        ))}
        <span className="separador">·</span>
        <span className="limite-tamano">Máximo {TAMANO_MAXIMO_MB} MB</span>
      </div>

      {error && <div className="mensaje-error">{error}</div>}

      <button
        className="boton-subir"
        onClick={alEnviar}
        disabled={!archivoSeleccionado || subiendo}
      >
        {subiendo ? 'Subiendo...' : 'Analizar imagen'}
      </button>

      {recientes.length > 0 && (
        <>
          <div className="separador-busqueda"><span>análisis recientes</span></div>
          <div className="historial-imagenes">
            {recientes.map(s => (
              <button
                key={s.guid}
                className="item-historial"
                onClick={() => onBuscar(s.guid)}
                title={formatearFecha(s.inicio)}
              >
                {s.url_thumbnail
                  ? <img src={s.url_thumbnail} alt="análisis reciente" />
                  : <div className="item-historial-vacio" />
                }
              </button>
            ))}
          </div>
        </>
      )}

      <div className="separador-busqueda"><span>buscar solicitud</span></div>

      <div className="autocomplete-wrapper">
        <input
          type="text"
          className="input-guid"
          placeholder="Escribe parte del ID para buscar..."
          value={busqueda}
          onChange={e => setBusqueda(e.target.value)}
          onFocus={() => {
            cargarTodasSolicitudes()
            setMostrarSugerencias(true)
          }}
          onBlur={() => {
            blurTimeoutRef.current = setTimeout(() => setMostrarSugerencias(false), 150)
          }}
        />

        {mostrarSugerencias && busqueda.length >= 1 && (
          <div className="sugerencias-dropdown">
            {cargandoSolicitudes && (
              <div className="sugerencia-cargando">Cargando...</div>
            )}
            {!cargandoSolicitudes && sugerencias.length === 0 && (
              <div className="sugerencia-vacia">Sin resultados para "{busqueda}"</div>
            )}
            {sugerencias.map(s => (
              <button
                key={s.guid}
                className="sugerencia-item"
                onMouseDown={() => {
                  clearTimeout(blurTimeoutRef.current)
                  alSeleccionarSugerencia(s.guid)
                }}
              >
                <div className="sugerencia-thumb">
                  {s.url_thumbnail
                    ? <img src={s.url_thumbnail} alt="" />
                    : <div className="sugerencia-thumb-vacio" />
                  }
                </div>
                <div className="sugerencia-info">
                  <span className="sugerencia-guid">{s.guid}</span>
                  <span className="sugerencia-fecha">{formatearFecha(s.inicio)}</span>
                </div>
                <span className={`sugerencia-estado estado-${s.estado?.toLowerCase()}`}>
                  {s.estado ?? '—'}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="separador-busqueda"><span>todas las solicitudes</span></div>

      <button
        className="boton-toggle-lista"
        onClick={() => {
          if (mostrarLista) {
            setCerrandoLista(true)
            setTimeout(() => { setMostrarLista(false); setCerrandoLista(false) }, 220)
          } else {
            setMostrarLista(true)
          }
        }}
      >
        {mostrarLista ? 'Ocultar' : 'Ver historial completo'}
      </button>

      {mostrarLista && (
        <div className={`lista-wrapper${cerrandoLista ? ' lista-cerrando' : ''}`}>
          <ListaSolicitudes onSeleccionar={(guid) => { setMostrarLista(false); onBuscar(guid) }} />
        </div>
      )}
    </div>
  )
}

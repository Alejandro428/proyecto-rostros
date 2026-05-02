import { useState, useEffect } from 'react'
import ZonaSubida from './componentes/ZonaSubida'
import Procesando from './componentes/Procesando'
import Resultado from './componentes/Resultado'
import Toast from './componentes/Toast'
import { consultarResultado, listarSolicitudes } from './servicios/api'

export default function App() {
  const [pantalla, setPantalla] = useState('subida')
  const [guid, setGuid] = useState(null)
  const [resultado, setResultado] = useState(null)
  const [toast, setToast] = useState(null)
  const [stats, setStats] = useState(null)
  const [modoOscuro, setModoOscuro] = useState(() => localStorage.getItem('modoOscuro') === 'true')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', modoOscuro)
    localStorage.setItem('modoOscuro', modoOscuro)
  }, [modoOscuro])

  const cargarStats = () => {
    listarSolicitudes().then(d => {
      setStats({
        total:   d.solicitudes.length,
        caras:   d.solicitudes.reduce((s, x) => s + (x.total_caras   || 0), 0),
        menores: d.solicitudes.reduce((s, x) => s + (x.total_menores || 0), 0),
      })
    }).catch(() => {})
  }

  useEffect(() => { cargarStats() }, [])

  const alSubirImagen = (guidRecibido) => {
    setGuid(guidRecibido)
    setPantalla('procesando')
  }

  const alBuscarSolicitud = async (guidBuscado) => {
    try {
      const datos = await consultarResultado(guidBuscado)
      setGuid(guidBuscado)
      if (datos.estado === 'COMPLETADA') {
        setResultado(datos)
        setPantalla('resultado')
      } else {
        setPantalla('procesando')
      }
    } catch (e) {
      if (e?.status !== 404) {
        setGuid(guidBuscado)
        setPantalla('procesando')
      }
    }
  }

  const alCompletar = (datos) => {
    setResultado(datos)
    setPantalla('resultado')
    setToast('Análisis completado')
    cargarStats()
  }

  const reiniciar = () => {
    setGuid(null)
    setResultado(null)
    setPantalla('subida')
  }

  return (
    <div className="contenedor-app">
      <header className="cabecera">
        <div className="cabecera-contenido">
          <div>
            <h1>Detección de Menores en Imágenes</h1>
            <p>Sistema automático de detección y pixelado de rostros de menores</p>
          </div>
          <button
            className="boton-modo-oscuro"
            onClick={() => setModoOscuro(m => !m)}
            title={modoOscuro ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
          >
            {modoOscuro ? '☀️' : '🌙'}
          </button>
        </div>
        {stats && (
          <div className="stats-cabecera">
            <div className="stat-item">
              <span className="stat-numero">{stats.total}</span>
              <span className="stat-etiqueta">{stats.total === 1 ? 'imagen' : 'imágenes'}</span>
            </div>
            <div className="stat-separador" />
            <div className="stat-item">
              <span className="stat-numero">{stats.caras}</span>
              <span className="stat-etiqueta">{stats.caras === 1 ? 'cara' : 'caras'}</span>
            </div>
            <div className="stat-separador" />
            <div className="stat-item">
              <span className={`stat-numero ${stats.menores > 0 ? 'stat-rojo' : ''}`}>{stats.menores}</span>
              <span className="stat-etiqueta">{stats.menores === 1 ? 'menor' : 'menores'}</span>
            </div>
          </div>
        )}
      </header>

      <main className="contenido-principal" key={pantalla}>
        {pantalla === 'subida'     && <ZonaSubida onSubir={alSubirImagen} onBuscar={alBuscarSolicitud} />}
        {pantalla === 'procesando' && <Procesando guid={guid} onCompletar={alCompletar} onError={reiniciar} />}
        {pantalla === 'resultado'  && <Resultado datos={resultado} guid={guid} onReiniciar={reiniciar} />}
      </main>

      {toast && <Toast mensaje={toast} onCerrar={() => setToast(null)} />}
    </div>
  )
}

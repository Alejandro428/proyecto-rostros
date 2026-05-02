import { useState } from 'react'
import ZonaSubida from './componentes/ZonaSubida'
import Procesando from './componentes/Procesando'
import Resultado from './componentes/Resultado'
import { consultarResultado } from './servicios/api'

export default function App() {
  const [pantalla, setPantalla] = useState('subida')
  const [guid, setGuid] = useState(null)
  const [resultado, setResultado] = useState(null)

  const alSubirImagen = (guidRecibido) => {
    setGuid(guidRecibido)
    setPantalla('procesando')
  }

  const alBuscarSolicitud = async (guidBuscado) => {
    try {
      const datos = await consultarResultado(guidBuscado)
      setGuid(guidBuscado)
      if (datos.estado === 'COMPLETADO') {
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
  }

  const reiniciar = () => {
    setGuid(null)
    setResultado(null)
    setPantalla('subida')
  }

  return (
    <div className="contenedor-app">
      <header className="cabecera">
        <h1>Detección de Menores en Imágenes</h1>
        <p>Sistema automático de detección y pixelado de rostros de menores</p>
      </header>

      <main className="contenido-principal">
        {pantalla === 'subida' && (
          <ZonaSubida
            onSubir={alSubirImagen}
            onBuscar={alBuscarSolicitud}
          />
        )}
        {pantalla === 'procesando' && (
          <Procesando guid={guid} onCompletar={alCompletar} onError={reiniciar} />
        )}
        {pantalla === 'resultado' && (
          <Resultado datos={resultado} guid={guid} onReiniciar={reiniciar} />
        )}
      </main>
    </div>
  )
}

import { useEffect, useRef } from 'react'
import { consultarResultado } from '../servicios/api'

const INTERVALO_MS = 2000
const TIMEOUT_MS = 120000

export default function Procesando({ guid, onCompletar, onError }) {
  const tiempoInicio = useRef(Date.now())

  useEffect(() => {
    const intervalo = setInterval(async () => {
      if (Date.now() - tiempoInicio.current > TIMEOUT_MS) {
        clearInterval(intervalo)
        onError()
        return
      }

      try {
        const datos = await consultarResultado(guid)
        if (datos.estado === 'COMPLETADA') {
          clearInterval(intervalo)
          onCompletar(datos)
        } else if (datos.estado === 'ERROR') {
          clearInterval(intervalo)
          onError()
        }
      } catch (e) {
        if (e.status === 404) {
          clearInterval(intervalo)
          onError()
        }
        // Para otros errores (red caída, etc.) seguir reintentando
      }
    }, INTERVALO_MS)

    return () => clearInterval(intervalo)
  }, [guid, onCompletar, onError])

  return (
    <div className="pantalla-procesando">
      <div className="spinner"></div>
      <h2>Analizando imagen...</h2>
      <p>Detectando rostros y clasificando edades</p>
      <div className="pasos">
        <div className="paso">Detección de rostros</div>
        <div className="paso">Clasificación de edad</div>
        <div className="paso">Generación de resultado</div>
      </div>
    </div>
  )
}

import { useState } from 'react'
import TarjetaCara from './TarjetaCara'

function fmt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-ES', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    timeZone: 'Europe/Madrid'
  })
}

function duracion(inicio, fin) {
  if (!inicio || !fin) return null
  const ms = new Date(fin) - new Date(inicio)
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(1)} s`
}

export default function Resultado({ datos, guid, onReiniciar }) {
  const imagenesDisponibles = [
    datos.imagenes.terminada && { clave: 'terminada', etiqueta: 'Pixelada',    url: datos.imagenes.terminada },
    datos.imagenes.marcos    && { clave: 'marcos',    etiqueta: 'Con marcos',  url: datos.imagenes.marcos    },
    datos.imagenes.original  && { clave: 'original',  etiqueta: 'Original',   url: datos.imagenes.original  },
  ].filter(Boolean)

  const [imagenActiva, setImagenActiva] = useState(
    imagenesDisponibles[0]?.clave ?? 'original'
  )

  const totalCaras = datos.caras_detectadas
  const totalMenores = datos.caras.filter(c => c.es_menor).length
  const hayMenores = totalMenores > 0
  const hayCaras = totalCaras > 0

  return (
    <div className="pantalla-resultado">
      <div className="resumen">
        <div className="resumen-titulo">
          <h2>Análisis completado</h2>
        </div>
        <div className="resumen-estadisticas">
          <div className="estadistica">
            <span className="estadistica-numero">{totalCaras}</span>
            <span className="estadistica-etiqueta">
              {totalCaras === 1 ? 'cara detectada' : 'caras detectadas'}
            </span>
          </div>
          {hayCaras && (
            <>
              <div className="estadistica">
                <span className={`estadistica-numero ${hayMenores ? 'rojo' : ''}`}>{totalMenores}</span>
                <span className="estadistica-etiqueta">
                  {totalMenores === 1 ? 'menor' : 'menores'}
                </span>
              </div>
              <div className="estadistica">
                <span className="estadistica-numero verde">{totalCaras - totalMenores}</span>
                <span className="estadistica-etiqueta">
                  {totalCaras - totalMenores === 1 ? 'adulto' : 'adultos'}
                </span>
              </div>
            </>
          )}
        </div>

        {!hayCaras && (
          <p className="aviso-sin-caras">No se detectaron rostros en la imagen.</p>
        )}
        {hayCaras && !hayMenores && (
          <p className="aviso-sin-menores">No se detectaron menores. No se ha generado imagen pixelada.</p>
        )}
      </div>

      {imagenesDisponibles.length > 0 && (
        <div className="seccion-imagenes">
          <div className="pestanas">
            {imagenesDisponibles.map(({ clave, etiqueta }) => (
              <button
                key={clave}
                className={`pestana ${imagenActiva === clave ? 'activa' : ''}`}
                onClick={() => setImagenActiva(clave)}
              >
                {etiqueta}
              </button>
            ))}
          </div>
          <div className="contenedor-imagen">
            {imagenesDisponibles.map(({ clave, url }) => (
              <img
                key={clave}
                src={url}
                alt={clave}
                className={`imagen-resultado ${imagenActiva === clave ? 'imagen-activa' : 'imagen-inactiva'}`}
              />
            ))}
          </div>
        </div>
      )}

      {hayCaras && (
        <div className="seccion-caras">
          <h3>Caras detectadas ({totalCaras})</h3>
          <div className="lista-caras">
            {datos.caras.map(cara => (
              <TarjetaCara key={cara.id_imagen} cara={cara} guid={guid} />
            ))}
          </div>
        </div>
      )}

      {datos.tiempos && (
        <div className="seccion-tiempos">
          <h3>Tiempos de procesamiento</h3>
          <div className="tabla-tiempos">
            <div className="tiempo-fila">
              <span className="tiempo-etiqueta">Inicio solicitud</span>
              <span className="tiempo-valor">{fmt(datos.tiempos.inicio_solicitud)}</span>
            </div>
            <div className="tiempo-fila">
              <span className="tiempo-etiqueta">Fin solicitud</span>
              <span className="tiempo-valor">{fmt(datos.tiempos.fin_solicitud)}</span>
            </div>
            {datos.tiempos.inicio_deteccion_caras && (
              <>
                <div className="tiempo-fila">
                  <span className="tiempo-etiqueta">Inicio detección caras</span>
                  <span className="tiempo-valor">{fmt(datos.tiempos.inicio_deteccion_caras)}</span>
                </div>
                <div className="tiempo-fila">
                  <span className="tiempo-etiqueta">Fin detección caras</span>
                  <span className="tiempo-valor">{fmt(datos.tiempos.fin_deteccion_caras)}</span>
                </div>
                <div className="tiempo-fila tiempo-duracion-fila">
                  <span className="tiempo-etiqueta">Detección de caras</span>
                  <span className="tiempo-valor tiempo-duracion">
                    {duracion(datos.tiempos.inicio_deteccion_caras, datos.tiempos.fin_deteccion_caras)}
                  </span>
                </div>
              </>
            )}
            {datos.tiempos.inicio_edad && (
              <>
                <div className="tiempo-fila">
                  <span className="tiempo-etiqueta">Inicio análisis edad</span>
                  <span className="tiempo-valor">{fmt(datos.tiempos.inicio_edad)}</span>
                </div>
                <div className="tiempo-fila">
                  <span className="tiempo-etiqueta">Fin análisis edad</span>
                  <span className="tiempo-valor">{fmt(datos.tiempos.fin_edad)}</span>
                </div>
                <div className="tiempo-fila tiempo-duracion-fila">
                  <span className="tiempo-etiqueta">Análisis de edad</span>
                  <span className="tiempo-valor tiempo-duracion">
                    {duracion(datos.tiempos.inicio_edad, datos.tiempos.fin_edad)}
                  </span>
                </div>
              </>
            )}
            {datos.tiempos.inicio_pixelado && (
              <>
                <div className="tiempo-fila">
                  <span className="tiempo-etiqueta">Inicio pixelado</span>
                  <span className="tiempo-valor">{fmt(datos.tiempos.inicio_pixelado)}</span>
                </div>
                <div className="tiempo-fila">
                  <span className="tiempo-etiqueta">Fin pixelado</span>
                  <span className="tiempo-valor">{fmt(datos.tiempos.fin_pixelado)}</span>
                </div>
                <div className="tiempo-fila tiempo-duracion-fila">
                  <span className="tiempo-etiqueta">Pixelado</span>
                  <span className="tiempo-valor tiempo-duracion">
                    {duracion(datos.tiempos.inicio_pixelado, datos.tiempos.fin_pixelado)}
                  </span>
                </div>
              </>
            )}
            {datos.tiempos.inicio_solicitud && datos.tiempos.fin_solicitud && (
              <div className="tiempo-fila tiempo-total">
                <span className="tiempo-etiqueta">Total</span>
                <span className="tiempo-valor tiempo-duracion">
                  {duracion(datos.tiempos.inicio_solicitud, datos.tiempos.fin_solicitud)}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      <button className="boton-reiniciar" onClick={onReiniciar}>
        Analizar otra imagen
      </button>
    </div>
  )
}

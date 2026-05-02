import { useState, useEffect } from 'react'
import { consultarCara } from '../servicios/api'

export default function TarjetaCara({ cara, guid }) {
  const [urlCrop, setUrlCrop] = useState(null)

  useEffect(() => {
    let activo = true
    consultarCara(guid, cara.id_imagen)
      .then(datos => { if (activo) setUrlCrop(datos.imagen) })
      .catch(() => {})
    return () => { activo = false }
  }, [guid, cara.id_imagen])

  const esMenor = cara.es_menor
  const score = cara.score !== null ? (cara.score * 100).toFixed(1) : null

  return (
    <div className={`tarjeta-cara ${esMenor ? 'menor' : 'adulto'}`}>
      <div className="crop-imagen">
        {urlCrop
          ? <img src={urlCrop} alt={`Cara ${cara.id_imagen}`} />
          : <div className="crop-cargando">⏳</div>
        }
      </div>
      <div className="cara-info">
        <span className={`badge-clasificacion ${esMenor ? 'badge-menor' : 'badge-adulto'}`}>
          {esMenor ? 'Menor' : 'Adulto'}
        </span>
        {score !== null && (
          <span className="cara-score">Score: {score}%</span>
        )}
        <span className="cara-id">Cara #{cara.id_imagen}</span>
      </div>
    </div>
  )
}

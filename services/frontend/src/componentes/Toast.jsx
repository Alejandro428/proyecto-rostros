import { useEffect } from 'react'

export default function Toast({ mensaje, onCerrar }) {
  useEffect(() => {
    const t = setTimeout(onCerrar, 4000)
    return () => clearTimeout(t)
  }, [onCerrar])

  return (
    <div className="toast" onClick={onCerrar}>
      <span className="toast-icono">✓</span>
      <span>{mensaje}</span>
    </div>
  )
}

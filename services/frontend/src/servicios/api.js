const URL_API_1 = '/api/v1'
const URL_API_2 = '/api/v2'

export async function subirImagen(archivo) {
  const formulario = new FormData()
  formulario.append('file', archivo)

  const respuesta = await fetch(`${URL_API_1}/upload`, {
    method: 'POST',
    body: formulario,
  })

  if (!respuesta.ok) {
    const error = await respuesta.json()
    throw new Error(error.detail || 'Error al subir la imagen')
  }

  return respuesta.json()
}

export async function consultarResultado(guid) {
  const respuesta = await fetch(`${URL_API_2}/resultado/${guid}`)

  if (!respuesta.ok) {
    const err = new Error('Error al consultar el resultado')
    err.status = respuesta.status
    throw err
  }

  return respuesta.json()
}

export async function listarSolicitudes(limite = 100) {
  const respuesta = await fetch(`${URL_API_2}/solicitudes?limite=${limite}`)
  if (!respuesta.ok) {
    throw new Error('Error al obtener la lista de solicitudes')
  }
  return respuesta.json()
}

export async function obtenerThumbnail(guid) {
  const respuesta = await fetch(`${URL_API_2}/resultado/${guid}/thumbnail`)
  if (!respuesta.ok) {
    const err = new Error('No encontrado')
    err.status = respuesta.status
    throw err
  }
  return respuesta.json()
}

export async function consultarCara(guid, idCara) {
  const respuesta = await fetch(`${URL_API_2}/resultado/${guid}/cara/${idCara}`)

  if (!respuesta.ok) {
    throw new Error('Error al obtener la cara')
  }

  return respuesta.json()
}

// Cliente API centralizado para los 6 microservicios.
// Cuando Cristian termine el API Gateway en Laravel, basta definir VITE_GATEWAY_URL
// para enrutar todas las peticiones a través del Gateway sin tocar los componentes.

const GW = import.meta.env.VITE_GATEWAY_URL || ''

export const SERVICES = {
  usuarios: GW ? `${GW}/api/usuarios` : (import.meta.env.VITE_USUARIOS_URL || 'http://localhost:5001'),
  catalogo: GW ? `${GW}/api/catalogo` : (import.meta.env.VITE_CATALOGO_URL || 'http://localhost:5002'),
  inventario: GW ? `${GW}/api/inventario` : (import.meta.env.VITE_INVENTARIO_URL || 'http://localhost:5003'),
  abastecimiento: GW ? `${GW}/api/abastecimiento` : (import.meta.env.VITE_ABASTECIMIENTO_URL || 'http://localhost:5004'),
  ventas: GW ? `${GW}/api/ventas` : (import.meta.env.VITE_VENTAS_URL || 'http://localhost:5005'),
  reportes: GW ? `${GW}/api/reportes` : (import.meta.env.VITE_REPORTES_URL || 'http://localhost:5006'),
}

let traceListener = null
export function setTraceListener(fn) {
  traceListener = fn
}

let unauthorizedListener = null
export function setUnauthorizedListener(fn) {
  unauthorizedListener = fn
}

export async function apiFetch(serviceKey, path, options = {}) {
  const base = SERVICES[serviceKey]
  const url = `${base}${path}`
  const token = localStorage.getItem('andina_token')
  const headers = { ...(options.headers || {}) }

  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const start = performance.now()
  try {
    const res = await fetch(url, { ...options, headers })
    const ms = Math.round(performance.now() - start)
    const isJson = (res.headers.get('content-type') || '').includes('application/json')
    const data = isJson ? await res.json() : await res.text()

    if (traceListener) {
      traceListener({
        id: `${Date.now()}-${Math.random()}`,
        service: serviceKey,
        method: options.method || 'GET',
        path,
        status: res.status,
        ms,
        ok: res.ok,
        time: new Date().toLocaleTimeString(),
      })
    }

    if (!res.ok) {
      if (
        res.status === 401 &&
        unauthorizedListener &&
        !path.startsWith('/auth/login') &&
        !path.startsWith('/auth/change-password')
      ) {
        unauthorizedListener()
      }
      const msg =
        (data && data.detail && (typeof data.detail === 'string' ? data.detail : data.detail.reason || data.detail.message)) ||
        (data && data.error) ||
        `Error HTTP ${res.status}`
      throw new Error(msg)
    }
    return data
  } catch (err) {
    if (traceListener && !err.message.startsWith('Error HTTP')) {
      traceListener({
        id: `${Date.now()}-${Math.random()}`,
        service: serviceKey,
        method: options.method || 'GET',
        path,
        status: 0,
        ms: Math.round(performance.now() - start),
        ok: false,
        time: new Date().toLocaleTimeString(),
      })
    }
    throw err
  }
}

export async function checkAllHealth() {
  const entries = await Promise.all(
    Object.keys(SERVICES).map(async (key) => {
      try {
        const res = await fetch(`${SERVICES[key]}/health`)
        return [key, res.ok]
      } catch {
        return [key, false]
      }
    })
  )
  return Object.fromEntries(entries)
}

import React, { useEffect, useState } from 'react'
import {
  Activity,
  BarChart3,
  Boxes,
  CheckCircle2,
  LayoutDashboard,
  LogOut,
  Package,
  RefreshCw,
  ShoppingCart,
  Truck,
  Users,
  AlertCircle,
} from 'lucide-react'
import { apiFetch, checkAllHealth, setTraceListener } from './api'
import DashboardView from './components/DashboardView'
import DailySalesView from './components/DailySalesView'
import PosView from './components/PosView'
import InventoryView from './components/InventoryView'
import CatalogView from './components/CatalogView'
import ProcurementView from './components/ProcurementView'
import ReportsView from './components/ReportsView'
import UsersView from './components/UsersView'
import Modal from './components/Modal'

export default function App() {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('andina_user')
    return raw ? JSON.parse(raw) : null
  })
  const [tab, setTab] = useState('dashboard')
  const [health, setHealth] = useState({})
  const [traces, setTraces] = useState([])
  const [statusModalOpen, setStatusModalOpen] = useState(false)
  const [toast, setToast] = useState(null)
  const [syncing, setSyncing] = useState(false)

  // Datos de negocio
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [warehouses, setWarehouses] = useState([])
  const [stocks, setStocks] = useState([])
  const [movements, setMovements] = useState([])
  const [returnsList, setReturnsList] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [orders, setOrders] = useState([])
  const [sales, setSales] = useState([])
  const [dashboard, setDashboard] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [thresholds, setThresholds] = useState([])
  const [usersList, setUsersList] = useState([])
  const [roles, setRoles] = useState([])

  // Login
  const [correo, setCorreo] = useState('admin@andina.com')
  const [contrasena, setContrasena] = useState('Admin123*')
  const [loggingIn, setLoggingIn] = useState(false)

  const notify = (msg, isError = false) => {
    setToast({ msg, isError, id: Date.now() })
    setTimeout(() => setToast(null), 4000)
  }

  useEffect(() => {
    setTraceListener((entry) => {
      setTraces((prev) => [entry, ...prev].slice(0, 20))
    })
  }, [])

  const refreshAll = async () => {
    const h = await checkAllHealth()
    setHealth(h)
    try {
      const [prods, cats, whs, st, movs, rets, sups, ocs, sls, dash, alts, ths, usrs, rls] = await Promise.all([
        apiFetch('catalogo', '/products').catch(() => []),
        apiFetch('catalogo', '/categories').catch(() => []),
        apiFetch('inventario', '/warehouses').catch(() => []),
        apiFetch('inventario', '/inventory/stock').catch(() => []),
        apiFetch('inventario', '/inventory/movements?limit=100').catch(() => []),
        apiFetch('inventario', '/inventory/returns').catch(() => []),
        apiFetch('abastecimiento', '/suppliers').catch(() => []),
        apiFetch('abastecimiento', '/purchase-orders').catch(() => []),
        apiFetch('ventas', '/sales').catch(() => []),
        apiFetch('reportes', '/reports/dashboard').catch(() => null),
        apiFetch('reportes', '/alerts').catch(() => []),
        apiFetch('reportes', '/thresholds').catch(() => []),
        apiFetch('usuarios', '/users').catch(() => []),
        apiFetch('usuarios', '/roles').catch(() => []),
      ])
      setProducts(prods)
      setCategories(cats)
      setWarehouses(whs)
      setStocks(st)
      setMovements(movs)
      setReturnsList(rets)
      setSuppliers(sups)
      setOrders(ocs)
      setSales(sls)
      setDashboard(dash)
      setAlerts(alts)
      setThresholds(ths)
      setUsersList(usrs)
      setRoles(rls)
    } catch (e) {
      notify(e.message, true)
    }
  }

  useEffect(() => {
    if (user) {
      refreshAll()
    }
  }, [user])

  const handleSyncAndRefresh = async () => {
    setSyncing(true)
    try {
      await apiFetch('reportes', '/reports/sync', { method: 'POST' }).catch(() => {})
      await refreshAll()
      notify('Datos actualizados')
    } finally {
      setSyncing(false)
    }
  }

  const handleAfterMutation = async () => {
    await apiFetch('reportes', '/reports/sync', { method: 'POST' }).catch(() => {})
    await refreshAll()
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoggingIn(true)
    try {
      const data = await apiFetch('usuarios', '/auth/login', {
        method: 'POST',
        body: JSON.stringify({ correo, contrasena }),
      })
      localStorage.setItem('andina_token', data.access_token)
      localStorage.setItem('andina_user', JSON.stringify(data.usuario))
      setUser(data.usuario)
      notify(`Bienvenido, ${data.usuario.nombre}`)
    } catch (err) {
      notify(err.message, true)
    } finally {
      setLoggingIn(false)
    }
  }

  const handleLogout = async () => {
    try {
      await apiFetch('usuarios', '/auth/logout', { method: 'POST' })
    } catch {
      /* noop */
    }
    localStorage.removeItem('andina_token')
    localStorage.removeItem('andina_user')
    setUser(null)
  }

  // ==================== LOGIN EDITORIAL ====================
  if (!user) {
    return (
      <div className="login-page">
        <aside className="login-brand-pane">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2.5rem' }}>
              <div className="brand-mark" style={{ background: '#FFFFFF', color: '#1E3A5F' }}>DA</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1rem' }}>Distribuidora Andina S.A.S.</div>
                <div style={{ fontSize: '0.8rem', opacity: 0.78 }}>Ferretería Industrial y Comercial</div>
              </div>
            </div>
            <h1>Control operativo de inventario y ventas en tiempo real.</h1>
            <div className="login-feature-list">
              <span>• Ventas con descuento automático de existencias por bodega</span>
              <span>• Trazabilidad completa (Kardex), traslados y devoluciones</span>
              <span>• Órdenes de compra, importación masiva y alertas tempranas</span>
            </div>
          </div>
          <div style={{ fontSize: '0.78rem', opacity: 0.72 }}>
            Arquitectura de Microservicios · Ingeniería de Software II
          </div>
        </aside>

        <main className="login-form-pane">
          <form className="login-card" onSubmit={handleLogin}>
            <div>
              <h2 style={{ fontSize: '1.35rem' }}>Iniciar Sesión</h2>
              <p style={{ fontSize: '0.85rem', color: 'var(--ink-muted)', marginTop: '0.25rem' }}>
                Ingresa tus credenciales para acceder a la plataforma operativa.
              </p>
            </div>

            <div className="field">
              <label htmlFor="login-email">Correo electrónico</label>
              <input
                id="login-email"
                type="email"
                value={correo}
                onChange={(e) => setCorreo(e.target.value)}
                autoComplete="email"
                required
              />
            </div>

            <div className="field">
              <label htmlFor="login-pass">Contraseña</label>
              <input
                id="login-pass"
                type="password"
                value={contrasena}
                onChange={(e) => setContrasena(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>

            <button className="btn" type="submit" disabled={loggingIn} style={{ width: '100%' }}>
              {loggingIn ? 'Verificando...' : 'Ingresar al Sistema'}
            </button>

            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '0.9rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', marginBottom: '0.5rem' }}>
                Accesos rápidos de demostración:
              </div>
              <div className="chip-row">
                <button type="button" className="filter-chip" onClick={() => { setCorreo('admin@andina.com'); setContrasena('Admin123*') }}>
                  Administrador
                </button>
                <button type="button" className="filter-chip" onClick={() => { setCorreo('bodega@andina.com'); setContrasena('Bodega123*') }}>
                  Operador Bodega
                </button>
                <button type="button" className="filter-chip" onClick={() => { setCorreo('ventas@andina.com'); setContrasena('Ventas123*') }}>
                  Vendedor
                </button>
              </div>
            </div>
          </form>
        </main>

        {toast && (
          <div className={`toast ${toast.isError ? 'error' : ''}`} role="status">
            {toast.isError ? <AlertCircle size={16} color="var(--crimson)" /> : <CheckCircle2 size={16} color="var(--sage)" />}
            <span>{toast.msg}</span>
          </div>
        )}
      </div>
    )
  }

  const activeAlertsCount = alerts.filter((a) => a.estado === 'ACTIVA').length
  const onlineServices = Object.values(health).filter(Boolean).length
  const totalServices = 6

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', subtitle: 'Resumen general de ventas e inventario', icon: LayoutDashboard },
    { id: 'pos', label: 'Cobrar Venta', subtitle: 'Punto de venta con cálculo de devuelta y descuento de stock', icon: ShoppingCart },
    { id: 'inventario', label: 'Inventario y Kardex', subtitle: 'Existencias por bodega, movimientos, traslados y devoluciones', icon: Boxes },
    { id: 'catalogo', label: 'Catálogo', subtitle: 'Productos, categorías e importación Excel / CSV', icon: Package },
    { id: 'abastecimiento', label: 'Abastecimiento', subtitle: 'Proveedores, órdenes de compra y recepción de mercancía', icon: Truck },
    { id: 'reportes', label: 'Reportes y Alertas', subtitle: 'Valorización, rotación y umbrales mínimos de stock', icon: BarChart3, badge: activeAlertsCount },
    { id: 'usuarios', label: 'Usuarios y Roles', subtitle: 'Control de cuentas y permisos de acceso', icon: Users },
  ]

  const currentNav =
    tab === 'ventas-hoy'
      ? { label: 'Ventas del Día', subtitle: 'Detalle de productos vendidos, valor y hora exacta realizada' }
      : navItems.find((n) => n.id === tab) || navItems[0]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">DA</div>
          <div>
            <div className="brand-title">Distribuidora Andina</div>
            <div className="brand-sub">Gestión de Inventarios</div>
          </div>
        </div>

        <div>
          <div className="nav-section-label">Operación</div>
          <nav className="nav-list" aria-label="Navegación principal">
            {navItems.map(({ id, label, icon: Icon, badge }) => (
              <button
                key={id}
                type="button"
                className={`nav-item ${tab === id ? 'active' : ''}`}
                onClick={() => setTab(id)}
              >
                <Icon size={17} />
                <span>{label}</span>
                {badge > 0 && <span className="nav-badge">{badge}</span>}
              </button>
            ))}
          </nav>
        </div>

        <div className="sidebar-footer">
          <button
            type="button"
            className="status-pill-btn"
            onClick={() => setStatusModalOpen(true)}
            title="Ver estado de microservicios y latencias"
          >
            <span className="status-indicator">
              <span className={`status-dot ${onlineServices === totalServices ? 'ok' : onlineServices > 0 ? 'warn' : 'err'}`} />
              <span>Servicios ({onlineServices}/{totalServices})</span>
            </span>
            <Activity size={14} />
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <h1 className="topbar-title">{currentNav.label}</h1>
            <p className="topbar-subtitle">{currentNav.subtitle}</p>
          </div>

          <div className="topbar-actions">
            <button type="button" className="btn btn-secondary btn-sm" onClick={handleSyncAndRefresh} disabled={syncing}>
              <RefreshCw size={14} />
              {syncing ? 'Actualizando...' : 'Actualizar'}
            </button>

            <div className="user-chip">
              <span>{user.nombre}</span>
              <span className="user-role-tag">{user.rol}</span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ padding: '0.2rem 0.45rem', minBlockSize: '1.65rem' }}
                onClick={handleLogout}
                title="Cerrar sesión"
                aria-label="Cerrar sesión"
              >
                <LogOut size={13} />
              </button>
            </div>
          </div>
        </header>

        {tab === 'dashboard' && (
          <DashboardView
            dashboard={dashboard}
            products={products}
            stocks={stocks}
            sales={sales}
            alerts={alerts}
            warehouses={warehouses}
            onNavigate={setTab}
          />
        )}

        {tab === 'ventas-hoy' && (
          <DailySalesView
            sales={sales}
            products={products}
            warehouses={warehouses}
            onBack={() => setTab('dashboard')}
            onGoPos={() => setTab('pos')}
          />
        )}

        {tab === 'pos' && (
          <PosView
            user={user}
            products={products}
            categories={categories}
            warehouses={warehouses}
            stocks={stocks}
            sales={sales}
            onSaleCompleted={handleAfterMutation}
            notify={notify}
          />
        )}

        {tab === 'inventario' && (
          <InventoryView
            user={user}
            products={products}
            warehouses={warehouses}
            stocks={stocks}
            movements={movements}
            returnsList={returnsList}
            onUpdated={handleAfterMutation}
            notify={notify}
          />
        )}

        {tab === 'catalogo' && (
          <CatalogView
            user={user}
            products={products}
            categories={categories}
            stocks={stocks}
            onUpdated={handleAfterMutation}
            notify={notify}
          />
        )}

        {tab === 'abastecimiento' && (
          <ProcurementView
            user={user}
            suppliers={suppliers}
            orders={orders}
            products={products}
            warehouses={warehouses}
            onUpdated={handleAfterMutation}
            notify={notify}
          />
        )}

        {tab === 'reportes' && (
          <ReportsView
            products={products}
            stocks={stocks}
            movements={movements}
            alerts={alerts}
            thresholds={thresholds}
            warehouses={warehouses}
            onUpdated={handleAfterMutation}
            notify={notify}
          />
        )}

        {tab === 'usuarios' && (
          <UsersView
            usersList={usersList}
            roles={roles}
            onUpdated={refreshAll}
            notify={notify}
          />
        )}
      </main>

      {/* Modal discreto bajo demanda para monitoreo de los 6 microservicios */}
      <Modal
        open={statusModalOpen}
        onClose={() => setStatusModalOpen(false)}
        title="Estado de la Arquitectura de Microservicios"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            {[
              { key: 'usuarios', label: 'Usuarios y Seguridad', tech: 'Flask :5001' },
              { key: 'catalogo', label: 'Catálogo', tech: 'Flask :5002' },
              { key: 'inventario', label: 'Inventario y Almacenes', tech: 'FastAPI :5003' },
              { key: 'abastecimiento', label: 'Abastecimiento', tech: 'Flask :5004' },
              { key: 'ventas', label: 'Ventas', tech: 'FastAPI :5005' },
              { key: 'reportes', label: 'Reportes y Alertas', tech: 'FastAPI :5006' },
            ].map((svc) => (
              <div
                key={svc.key}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.6rem 0.75rem',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.84rem' }}>{svc.label}</div>
                  <div className="mono" style={{ fontSize: '0.73rem', color: 'var(--ink-muted)' }}>{svc.tech}</div>
                </div>
                <span className={`badge ${health[svc.key] ? 'badge-sage' : 'badge-crimson'}`}>
                  {health[svc.key] ? 'En línea' : 'Sin conexión'}
                </span>
              </div>
            ))}
          </div>

          <div>
            <div style={{ fontWeight: 600, fontSize: '0.84rem', marginBottom: '0.4rem' }}>Últimas peticiones HTTP</div>
            <div className="table-wrapper" style={{ maxBlockSize: '210px' }}>
              <table>
                <thead><tr><th>Servicio</th><th>Endpoint</th><th>Estado</th><th>Latencia</th></tr></thead>
                <tbody>
                  {traces.slice(0, 10).map((t) => (
                    <tr key={t.id}>
                      <td className="mono">{t.service}</td>
                      <td className="mono" style={{ fontSize: '0.75rem' }}>{t.method} {t.path}</td>
                      <td>
                        <span className={`badge ${t.ok ? 'badge-sage' : 'badge-crimson'}`}>{t.status || 'ERR'}</span>
                      </td>
                      <td className="mono">{t.ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </Modal>

      {toast && (
        <div className={`toast ${toast.isError ? 'error' : ''}`} role="status">
          {toast.isError ? <AlertCircle size={17} color="var(--crimson)" /> : <CheckCircle2 size={17} color="var(--sage)" />}
          <span>{toast.msg}</span>
        </div>
      )}
    </div>
  )
}

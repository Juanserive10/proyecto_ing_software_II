import React, { useMemo, useState } from 'react'
import {
  ArrowRightLeft,
  Plus,
  RotateCcw,
  Search,
  Warehouse,
} from 'lucide-react'
import { apiFetch } from '../api'
import { formatDate } from '../utils/format'
import Modal from './Modal'

export default function InventoryView({
  user,
  products,
  warehouses,
  stocks,
  movements,
  returnsList,
  usersList = [],
  onUpdated,
  notify,
}) {
  const canOperate = user?.rol === 'ADMINISTRADOR' || user?.rol === 'OPERADOR_BODEGA'
  const [subTab, setSubTab] = useState('stock') // 'stock' | 'kardex' | 'devoluciones' | 'bodegas'
  const [filterBodega, setFilterBodega] = useState('ALL')
  const [searchQ, setSearchQ] = useState('')
  const [filterTipo, setFilterTipo] = useState('ALL')

  // Modales
  const [activeModal, setActiveModal] = useState(null) // 'movimiento' | 'traslado' | 'devolucion' | 'bodega'

  // Formularios
  const [movForm, setMovForm] = useState({ tipo: 'ENTRADA', id_producto: 1, cantidad: 5, id_bodega: 1 })
  const [trForm, setTrForm] = useState({ id_bodega_origen: 1, id_bodega_destino: 2, id_producto: 1, cantidad: 2 })
  const [retForm, setRetForm] = useState({
    origen: 'CLIENTE',
    id_bodega: 1,
    id_producto: 1,
    cantidad: 1,
    condicion: 'BUENO',
    motivo: 'Cambio de referencia',
  })
  const [bodForm, setBodForm] = useState({ codigo: '', nombre: '', ubicacion: '' })

  const productMap = useMemo(() => {
    const m = {}
    products.forEach((p) => { m[p.id_producto] = p })
    return m
  }, [products])

  const warehouseMap = useMemo(() => {
    const m = {}
    warehouses.forEach((w) => { m[w.id_bodega] = w })
    return m
  }, [warehouses])

  const userMap = useMemo(() => {
    const m = {}
    usersList.forEach((u) => { m[u.id_usuario] = u })
    return m
  }, [usersList])

  const filteredStock = useMemo(() => {
    const q = searchQ.trim().toLowerCase()
    return stocks.filter((s) => {
      if (filterBodega !== 'ALL' && Number(s.id_bodega) !== Number(filterBodega)) return false
      if (!q) return true
      const p = productMap[s.id_producto]
      return (
        (p?.nombre || '').toLowerCase().includes(q) ||
        (p?.codigo || '').toLowerCase().includes(q) ||
        (s.bodega_nombre || '').toLowerCase().includes(q)
      )
    })
  }, [stocks, filterBodega, searchQ, productMap])

  const filteredMovements = useMemo(() => {
    const q = searchQ.trim().toLowerCase()
    return movements.filter((m) => {
      if (filterTipo !== 'ALL' && m.tipo !== filterTipo) return false
      if (!q) return true
      const p = productMap[m.id_producto]
      return (
        (p?.nombre || '').toLowerCase().includes(q) ||
        (p?.codigo || '').toLowerCase().includes(q) ||
        (m.tipo_referencia || '').toLowerCase().includes(q)
      )
    })
  }, [movements, filterTipo, searchQ, productMap])

  const handleMovement = async (e) => {
    e.preventDefault()
    const isIn = movForm.tipo === 'ENTRADA' || movForm.tipo === 'AJUSTE_POSITIVO'
    try {
      await apiFetch('inventario', '/inventory/movements', {
        method: 'POST',
        body: JSON.stringify({
          tipo: movForm.tipo,
          id_producto: Number(movForm.id_producto),
          cantidad: Number(movForm.cantidad),
          id_bodega_destino: isIn ? Number(movForm.id_bodega) : null,
          id_bodega_origen: !isIn ? Number(movForm.id_bodega) : null,
          id_usuario: user?.id_usuario || 1,
          tipo_referencia: 'OPERACION_WEB',
        }),
      })
      setActiveModal(null)
      await onUpdated()
      notify(`Movimiento ${movForm.tipo} registrado en el Kardex`)
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleTransfer = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('inventario', '/inventory/transfers', {
        method: 'POST',
        body: JSON.stringify({
          id_bodega_origen: Number(trForm.id_bodega_origen),
          id_bodega_destino: Number(trForm.id_bodega_destino),
          id_producto: Number(trForm.id_producto),
          cantidad: Number(trForm.cantidad),
          id_usuario: user?.id_usuario || 1,
        }),
      })
      setActiveModal(null)
      await onUpdated()
      notify('Traslado atómico completado entre bodegas')
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleReturn = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('inventario', '/inventory/returns', {
        method: 'POST',
        body: JSON.stringify({
          ...retForm,
          id_bodega: Number(retForm.id_bodega),
          id_producto: Number(retForm.id_producto),
          cantidad: Number(retForm.cantidad),
          id_usuario: user?.id_usuario || 1,
        }),
      })
      setActiveModal(null)
      await onUpdated()
      notify('Devolución registrada y reflejada en el inventario')
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleCreateWarehouse = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('inventario', '/warehouses', {
        method: 'POST',
        body: JSON.stringify({ ...bodForm, activo: true }),
      })
      setBodForm({ codigo: '', nombre: '', ubicacion: '' })
      setActiveModal(null)
      await onUpdated()
      notify('Bodega creada correctamente')
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleToggleWarehouse = async (w) => {
    try {
      await apiFetch('inventario', `/warehouses/${w.id_bodega}`, {
        method: 'PATCH',
        body: JSON.stringify({ activo: !w.activo }),
      })
      await onUpdated()
      notify(w.activo ? `Bodega ${w.codigo} desactivada` : `Bodega ${w.codigo} activada`)
    } catch (err) {
      notify(err.message, true)
    }
  }

  return (
    <div className="view-enter">
      {/* Barra superior de sub-vistas y botones de acción */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div className="seg-tabs" role="tablist">
          <button type="button" className={`seg-tab ${subTab === 'stock' ? 'active' : ''}`} onClick={() => setSubTab('stock')}>
            Existencias ({stocks.length})
          </button>
          <button type="button" className={`seg-tab ${subTab === 'kardex' ? 'active' : ''}`} onClick={() => setSubTab('kardex')}>
            Kardex ({movements.length})
          </button>
          <button type="button" className={`seg-tab ${subTab === 'devoluciones' ? 'active' : ''}`} onClick={() => setSubTab('devoluciones')}>
            Devoluciones ({returnsList.length})
          </button>
          <button type="button" className={`seg-tab ${subTab === 'bodegas' ? 'active' : ''}`} onClick={() => setSubTab('bodegas')}>
            Bodegas ({warehouses.length})
          </button>
        </div>

        {canOperate && (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-sm" onClick={() => setActiveModal('movimiento')}>
              <Plus size={14} /> Movimiento
            </button>
            <button type="button" className="btn btn-ochre btn-sm" onClick={() => setActiveModal('traslado')}>
              <ArrowRightLeft size={14} /> Trasladar
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setActiveModal('devolucion')}>
              <RotateCcw size={14} /> Devolución
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setActiveModal('bodega')}>
              <Warehouse size={14} /> Nueva Bodega
            </button>
          </div>
        )}
      </div>

      {/* EXISTENCIAS POR BODEGA */}
      {subTab === 'stock' && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Existencias por Bodega</h3>
              <p className="panel-desc">Saldo disponible, unidades no vendibles y control de versión optimista</p>
            </div>
            <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
              <div className="search-bar" style={{ minWidth: '220px' }}>
                <Search size={15} />
                <input
                  value={searchQ}
                  onChange={(e) => setSearchQ(e.target.value)}
                  placeholder="Filtrar por producto o código..."
                />
              </div>
              <select style={{ width: 'auto' }} value={filterBodega} onChange={(e) => setFilterBodega(e.target.value)}>
                <option value="ALL">Todas las bodegas</option>
                {warehouses.map((w) => (
                  <option key={w.id_bodega} value={w.id_bodega}>{w.codigo} — {w.nombre}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="table-wrapper" role="region" aria-label="Existencias por bodega" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Bodega</th>
                  <th>Código</th>
                  <th>Producto</th>
                  <th>Disponible</th>
                  <th>No Vendible</th>
                  <th>Nivel Visual</th>
                  <th>Versión</th>
                </tr>
              </thead>
              <tbody>
                {filteredStock.map((s) => {
                  const p = productMap[s.id_producto]
                  const qty = Number(s.cantidad_disponible || 0)
                  const pct = Math.min(100, Math.round((qty / 60) * 100))
                  const color = qty <= 5 ? 'var(--crimson)' : qty <= 15 ? 'var(--ochre)' : 'var(--sage)'
                  return (
                    <tr key={s.id_stock}>
                      <td><span className="badge badge-slate">{s.bodega_codigo}</span></td>
                      <td className="mono">{p?.codigo || `#${s.id_producto}`}</td>
                      <td style={{ fontWeight: 500 }}>{p?.nombre || `Producto #${s.id_producto}`}</td>
                      <td className="mono" style={{ fontWeight: 700, color }}>{qty}</td>
                      <td className="mono" style={{ color: 'var(--ink-muted)' }}>{s.cantidad_no_vendible}</td>
                      <td style={{ minWidth: '120px' }}>
                        <div className="meter-track">
                          <div className="meter-fill" style={{ width: `${Math.max(4, pct)}%`, background: color }} />
                        </div>
                      </td>
                      <td className="mono" style={{ fontSize: '0.78rem', color: 'var(--ink-muted)' }}>v{s.version}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* KARDEX / HISTÓRICO DE MOVIMIENTOS */}
      {subTab === 'kardex' && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Kardex — Trazabilidad y Auditoría (RF10)</h3>
              <p className="panel-desc">Registro inmutable de entradas, salidas, ajustes, traslados y devoluciones</p>
            </div>
            <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
              <div className="search-bar" style={{ minWidth: '200px' }}>
                <Search size={15} />
                <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} placeholder="Buscar producto o ref..." />
              </div>
              <select style={{ width: 'auto' }} value={filterTipo} onChange={(e) => setFilterTipo(e.target.value)}>
                <option value="ALL">Todos los tipos</option>
                <option value="ENTRADA">ENTRADA</option>
                <option value="SALIDA">SALIDA</option>
                <option value="TRASLADO">TRASLADO</option>
                <option value="AJUSTE_POSITIVO">AJUSTE_POSITIVO</option>
                <option value="AJUSTE_NEGATIVO">AJUSTE_NEGATIVO</option>
                <option value="DEVOLUCION_CLIENTE">DEVOLUCION_CLIENTE</option>
                <option value="DEVOLUCION_PROVEEDOR">DEVOLUCION_PROVEEDOR</option>
              </select>
            </div>
          </div>

          <div className="table-wrapper" role="region" aria-label="Kardex de movimientos" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Fecha</th>
                  <th>Tipo</th>
                  <th>Producto</th>
                  <th>Origen → Destino</th>
                  <th>Cantidad</th>
                  <th>Usuario</th>
                  <th>Referencia</th>
                </tr>
              </thead>
              <tbody>
                {filteredMovements.map((m) => {
                  const p = productMap[m.id_producto]
                  const orig = m.id_bodega_origen ? warehouseMap[m.id_bodega_origen]?.codigo || `BOD-0${m.id_bodega_origen}` : '—'
                  const dest = m.id_bodega_destino ? warehouseMap[m.id_bodega_destino]?.codigo || `BOD-0${m.id_bodega_destino}` : '—'
                  const uName = userMap[m.id_usuario]?.nombre || `Usuario #${m.id_usuario}`
                  const badgeCls =
                    m.tipo.includes('ENTRADA') || m.tipo.includes('POSITIVO') || m.tipo === 'DEVOLUCION_CLIENTE'
                      ? 'badge-sage'
                      : m.tipo === 'TRASLADO'
                      ? 'badge-ochre'
                      : 'badge-crimson'
                  return (
                    <tr key={m.id_movimiento}>
                      <td className="mono">#{m.id_movimiento}</td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--ink-muted)' }}>{formatDate(m.ocurrido_en)}</td>
                      <td><span className={`badge ${badgeCls}`}>{m.tipo}</span></td>
                      <td>
                        <span className="mono" style={{ marginRight: '0.4rem', color: 'var(--ink-muted)' }}>{p?.codigo}</span>
                        {p?.nombre || `#${m.id_producto}`}
                      </td>
                      <td className="mono" style={{ fontSize: '0.8rem' }}>{orig} → {dest}</td>
                      <td className="mono" style={{ fontWeight: 700 }}>{m.cantidad}</td>
                      <td style={{ fontSize: '0.78rem' }}>{uName}</td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--ink-secondary)' }}>
                        {m.tipo_referencia}{m.id_referencia ? ` #${m.id_referencia}` : ''}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* DEVOLUCIONES (RF13) */}
      {subTab === 'devoluciones' && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Historial de Devoluciones (RF13)</h3>
              <p className="panel-desc">Devoluciones de clientes o hacia proveedores vinculadas al Kardex</p>
            </div>
          </div>
          <div className="table-wrapper" role="region" aria-label="Devoluciones" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Fecha</th>
                  <th>Origen</th>
                  <th>Bodega</th>
                  <th>Producto</th>
                  <th>Cantidad</th>
                  <th>Condición</th>
                  <th>Motivo</th>
                </tr>
              </thead>
              <tbody>
                {returnsList.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', color: 'var(--ink-muted)' }}>
                      No hay devoluciones registradas.
                    </td>
                  </tr>
                ) : (
                  returnsList.map((d) => (
                    <tr key={d.id_devolucion}>
                      <td className="mono">#{d.id_devolucion}</td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--ink-muted)' }}>{formatDate(d.registrado_en)}</td>
                      <td><span className="badge badge-slate">{d.origen}</span></td>
                      <td className="mono">{warehouseMap[d.id_bodega]?.codigo || `BOD-0${d.id_bodega}`}</td>
                      <td>{productMap[d.id_producto]?.nombre || `#${d.id_producto}`}</td>
                      <td className="mono" style={{ fontWeight: 700 }}>{d.cantidad}</td>
                      <td>
                        <span className={`badge ${d.condicion === 'BUENO' ? 'badge-sage' : 'badge-ochre'}`}>
                          {d.condicion}
                        </span>
                      </td>
                      <td>{d.motivo || '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* BODEGAS (RF05) */}
      {subTab === 'bodegas' && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Almacenes y Bodegas (RF05)</h3>
              <p className="panel-desc">Ubicaciones físicas habilitadas para almacenar y despachar inventario</p>
            </div>
          </div>
          <div className="table-wrapper" role="region" aria-label="Bodegas" tabIndex={0}>
            <table>
              <thead>
                <tr><th>ID</th><th>Código</th><th>Nombre</th><th>Ubicación</th><th>Estado</th>{canOperate && <th>Acción</th>}</tr>
              </thead>
              <tbody>
                {warehouses.map((w) => (
                  <tr key={w.id_bodega}>
                    <td className="mono">#{w.id_bodega}</td>
                    <td><span className="badge badge-slate">{w.codigo}</span></td>
                    <td style={{ fontWeight: 600 }}>{w.nombre}</td>
                    <td>{w.ubicacion || '—'}</td>
                    <td><span className={`badge ${w.activo ? 'badge-sage' : 'badge-neutral'}`}>{w.activo ? 'Activa' : 'Inactiva'}</span></td>
                    {canOperate && (
                      <td>
                        <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleToggleWarehouse(w)}>
                          {w.activo ? 'Desactivar' : 'Activar'}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* MODALES NATIVOS */}
      <Modal open={activeModal === 'movimiento'} onClose={() => setActiveModal(null)} title="Registrar Movimiento de Inventario">
        <form onSubmit={handleMovement} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <div className="field">
            <label>Tipo de Movimiento</label>
            <select value={movForm.tipo} onChange={(e) => setMovForm({ ...movForm, tipo: e.target.value })}>
              <option value="ENTRADA">ENTRADA (Suma existencias)</option>
              <option value="SALIDA">SALIDA (Descuenta existencias)</option>
              <option value="AJUSTE_POSITIVO">AJUSTE_POSITIVO (Suma por conteo)</option>
              <option value="AJUSTE_NEGATIVO">AJUSTE_NEGATIVO (Descuenta por conteo)</option>
            </select>
          </div>
          <div className="field">
            <label>Bodega</label>
            <select value={movForm.id_bodega} onChange={(e) => setMovForm({ ...movForm, id_bodega: e.target.value })}>
              {warehouses.map((w) => <option key={w.id_bodega} value={w.id_bodega}>{w.codigo} — {w.nombre}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Producto</label>
            <select value={movForm.id_producto} onChange={(e) => setMovForm({ ...movForm, id_producto: e.target.value })}>
              {products.map((p) => <option key={p.id_producto} value={p.id_producto}>{p.codigo} — {p.nombre}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Cantidad</label>
            <input type="number" min="1" step="1" value={movForm.cantidad} onChange={(e) => setMovForm({ ...movForm, cantidad: e.target.value })} required />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setActiveModal(null)}>Cancelar</button>
            <button type="submit" className="btn">Guardar en Kardex</button>
          </div>
        </form>
      </Modal>

      <Modal open={activeModal === 'traslado'} onClose={() => setActiveModal(null)} title="Traslado entre Bodegas">
        <form onSubmit={handleTransfer} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <div className="form-grid">
            <div className="field">
              <label>Bodega Origen</label>
              <select value={trForm.id_bodega_origen} onChange={(e) => setTrForm({ ...trForm, id_bodega_origen: e.target.value })}>
                {warehouses.map((w) => <option key={w.id_bodega} value={w.id_bodega}>{w.codigo} — {w.nombre}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Bodega Destino</label>
              <select value={trForm.id_bodega_destino} onChange={(e) => setTrForm({ ...trForm, id_bodega_destino: e.target.value })}>
                {warehouses.map((w) => <option key={w.id_bodega} value={w.id_bodega}>{w.codigo} — {w.nombre}</option>)}
              </select>
            </div>
          </div>
          <div className="field">
            <label>Producto</label>
            <select value={trForm.id_producto} onChange={(e) => setTrForm({ ...trForm, id_producto: e.target.value })}>
              {products.map((p) => <option key={p.id_producto} value={p.id_producto}>{p.codigo} — {p.nombre}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Cantidad a trasladar</label>
            <input type="number" min="1" value={trForm.cantidad} onChange={(e) => setTrForm({ ...trForm, cantidad: e.target.value })} required />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setActiveModal(null)}>Cancelar</button>
            <button type="submit" className="btn btn-ochre">Ejecutar Traslado</button>
          </div>
        </form>
      </Modal>

      <Modal open={activeModal === 'devolucion'} onClose={() => setActiveModal(null)} title="Registrar Devolución (RF13)">
        <form onSubmit={handleReturn} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <div className="form-grid">
            <div className="field">
              <label>Origen</label>
              <select value={retForm.origen} onChange={(e) => setRetForm({ ...retForm, origen: e.target.value })}>
                <option value="CLIENTE">Devolución de CLIENTE</option>
                <option value="PROVEEDOR">Devolución a PROVEEDOR</option>
              </select>
            </div>
            <div className="field">
              <label>Condición</label>
              <select value={retForm.condicion} onChange={(e) => setRetForm({ ...retForm, condicion: e.target.value })}>
                <option value="BUENO">BUENO (Reingresa vendible)</option>
                <option value="DANADO">DAÑADO (Stock no vendible)</option>
              </select>
            </div>
          </div>
          <div className="form-grid">
            <div className="field">
              <label>Bodega</label>
              <select value={retForm.id_bodega} onChange={(e) => setRetForm({ ...retForm, id_bodega: e.target.value })}>
                {warehouses.map((w) => <option key={w.id_bodega} value={w.id_bodega}>{w.codigo}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Cantidad</label>
              <input type="number" min="1" value={retForm.cantidad} onChange={(e) => setRetForm({ ...retForm, cantidad: e.target.value })} required />
            </div>
          </div>
          <div className="field">
            <label>Producto</label>
            <select value={retForm.id_producto} onChange={(e) => setRetForm({ ...retForm, id_producto: e.target.value })}>
              {products.map((p) => <option key={p.id_producto} value={p.id_producto}>{p.codigo} — {p.nombre}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Motivo</label>
            <input value={retForm.motivo} onChange={(e) => setRetForm({ ...retForm, motivo: e.target.value })} placeholder="Motivo de la devolución" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setActiveModal(null)}>Cancelar</button>
            <button type="submit" className="btn btn-crimson">Confirmar Devolución</button>
          </div>
        </form>
      </Modal>

      <Modal open={activeModal === 'bodega'} onClose={() => setActiveModal(null)} title="Nueva Bodega / Almacén">
        <form onSubmit={handleCreateWarehouse} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <div className="form-grid">
            <div className="field">
              <label>Código</label>
              <input value={bodForm.codigo} onChange={(e) => setBodForm({ ...bodForm, codigo: e.target.value })} placeholder="Ej. BOD-03" required />
            </div>
            <div className="field">
              <label>Nombre</label>
              <input value={bodForm.nombre} onChange={(e) => setBodForm({ ...bodForm, nombre: e.target.value })} placeholder="Ej. Bodega Sur" required />
            </div>
          </div>
          <div className="field">
            <label>Ubicación</label>
            <input value={bodForm.ubicacion} onChange={(e) => setBodForm({ ...bodForm, ubicacion: e.target.value })} placeholder="Dirección o zona" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setActiveModal(null)}>Cancelar</button>
            <button type="submit" className="btn">Crear Bodega</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

import React, { useMemo, useState } from 'react'
import { CheckCircle2, PackageCheck, Plus, Trash2 } from 'lucide-react'
import { apiFetch } from '../api'
import { formatDate, formatMoney } from '../utils/format'
import Modal from './Modal'

export default function ProcurementView({ user, suppliers, orders, products, warehouses, onUpdated, notify }) {
  const [subTab, setSubTab] = useState('ordenes') // 'ordenes' | 'proveedores'
  const [ocModal, setOcModal] = useState(false)
  const [supModal, setSupModal] = useState(false)
  const [receiveTarget, setReceiveTarget] = useState(null)

  const [ocProveedor, setOcProveedor] = useState(suppliers[0]?.id_proveedor || 1)
  const [ocItems, setOcItems] = useState([{ id_producto: 1, cantidad_pedida: 10, costo_unitario: 150000 }])
  const [supForm, setSupForm] = useState({ identificacion: '', razon_social: '', contacto: '', correo: '', telefono: '' })

  const [recBodega, setRecBodega] = useState(1)
  const [recQtys, setRecQtys] = useState({})

  const productMap = useMemo(() => {
    const m = {}
    products.forEach((p) => { m[p.id_producto] = p })
    return m
  }, [products])

  const openReceiveModal = (oc) => {
    const init = {}
    oc.detalles.forEach((d) => {
      init[d.id_detalle_orden] = d.cantidad_pedida
    })
    setRecQtys(init)
    setRecBodega(warehouses[0]?.id_bodega || 1)
    setReceiveTarget(oc)
  }

  const handleCreateOC = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('abastecimiento', '/purchase-orders', {
        method: 'POST',
        body: JSON.stringify({
          id_proveedor: Number(ocProveedor),
          id_usuario: user?.id_usuario || 1,
          items: ocItems.map((it) => ({
            id_producto: Number(it.id_producto),
            cantidad_pedida: Number(it.cantidad_pedida),
            costo_unitario: Number(it.costo_unitario),
          })),
        }),
      })
      setOcModal(false)
      setOcItems([{ id_producto: 1, cantidad_pedida: 10, costo_unitario: 150000 }])
      await onUpdated()
      notify('Orden de compra emitida correctamente')
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleConfirmReceive = async (e) => {
    e.preventDefault()
    if (!receiveTarget) return
    const itemsPayload = receiveTarget.detalles
      .map((d) => ({
        id_detalle_orden: d.id_detalle_orden,
        cantidad_recibida: Number(recQtys[d.id_detalle_orden] || 0),
        condicion: 'BUENO',
      }))
      .filter((it) => it.cantidad_recibida > 0)

    if (itemsPayload.length === 0) {
      return notify('Ingresa al menos una cantidad mayor a 0 para recibir', true)
    }

    try {
      const res = await apiFetch('abastecimiento', `/purchase-orders/${receiveTarget.id_orden}/receipts`, {
        method: 'POST',
        body: JSON.stringify({
          id_bodega: Number(recBodega),
          id_usuario: user?.id_usuario || 1,
          items: itemsPayload,
        }),
      })
      setReceiveTarget(null)
      await onUpdated()
      notify(`OC ${receiveTarget.numero} recibida (${res.orden_estado}) · Inventario actualizado`)
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleCreateSupplier = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('abastecimiento', '/suppliers', {
        method: 'POST',
        body: JSON.stringify(supForm),
      })
      setSupForm({ identificacion: '', razon_social: '', contacto: '', correo: '', telefono: '' })
      setSupModal(false)
      await onUpdated()
      notify('Proveedor registrado correctamente')
    } catch (err) {
      notify(err.message, true)
    }
  }

  const ocTotalPreview = ocItems.reduce(
    (acc, it) => acc + Number(it.cantidad_pedida || 0) * Number(it.costo_unitario || 0),
    0
  )

  return (
    <div className="view-enter">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div className="seg-tabs" role="tablist">
          <button type="button" className={`seg-tab ${subTab === 'ordenes' ? 'active' : ''}`} onClick={() => setSubTab('ordenes')}>
            Órdenes de Compra ({orders.length})
          </button>
          <button type="button" className={`seg-tab ${subTab === 'proveedores' ? 'active' : ''}`} onClick={() => setSubTab('proveedores')}>
            Proveedores ({suppliers.length})
          </button>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setSupModal(true)}>
            <Plus size={14} /> Proveedor
          </button>
          <button type="button" className="btn btn-sm" onClick={() => setOcModal(true)}>
            <Plus size={14} /> Nueva Orden de Compra
          </button>
        </div>
      </div>

      {subTab === 'ordenes' ? (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Órdenes de Compra y Recepción de Mercancía (RF06)</h3>
              <p className="panel-desc">Al confirmar una recepción, Abastecimiento solicita la entrada automática en Inventario</p>
            </div>
          </div>

          <div className="table-wrapper" role="region" aria-label="Órdenes de compra" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Número</th>
                  <th>Fecha Emisión</th>
                  <th>Proveedor</th>
                  <th>Ítems</th>
                  <th>Total Estimado</th>
                  <th>Estado</th>
                  <th>Acción</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((oc) => {
                  const badgeCls =
                    oc.estado === 'RECIBIDA' ? 'badge-sage' : oc.estado === 'PARCIAL' ? 'badge-ochre' : 'badge-slate'
                  return (
                    <tr key={oc.id_orden}>
                      <td className="mono" style={{ fontWeight: 600 }}>{oc.numero}</td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--ink-muted)' }}>{formatDate(oc.fecha_emision)}</td>
                      <td style={{ fontWeight: 500 }}>{oc.proveedor_nombre}</td>
                      <td style={{ fontSize: '0.8rem' }}>
                        {oc.detalles.map((d) => `${productMap[d.id_producto]?.codigo || `#${d.id_producto}`} (×${d.cantidad_pedida})`).join(', ')}
                      </td>
                      <td className="mono" style={{ fontWeight: 700 }}>{formatMoney(oc.total_estimado)}</td>
                      <td><span className={`badge ${badgeCls}`}>{oc.estado}</span></td>
                      <td>
                        {oc.estado !== 'RECIBIDA' ? (
                          <button type="button" className="btn btn-sage btn-sm" onClick={() => openReceiveModal(oc)}>
                            <PackageCheck size={14} /> Recibir
                          </button>
                        ) : (
                          <span style={{ fontSize: '0.78rem', color: 'var(--sage)', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                            <CheckCircle2 size={14} /> Completada
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Directorio de Proveedores (RF03)</h3>
              <p className="panel-desc">Proveedores autorizados para abastecimiento de Distribuidora Andina</p>
            </div>
          </div>

          <div className="table-wrapper" role="region" aria-label="Proveedores" tabIndex={0}>
            <table>
              <thead>
                <tr><th>Identificación</th><th>Razón Social</th><th>Contacto</th><th>Correo</th><th>Teléfono</th><th>Estado</th></tr>
              </thead>
              <tbody>
                {suppliers.map((s) => (
                  <tr key={s.id_proveedor}>
                    <td className="mono">{s.identificacion}</td>
                    <td style={{ fontWeight: 600 }}>{s.razon_social}</td>
                    <td>{s.contacto || '—'}</td>
                    <td>{s.correo || '—'}</td>
                    <td className="mono">{s.telefono || '—'}</td>
                    <td><span className={`badge ${s.activo ? 'badge-sage' : 'badge-neutral'}`}>{s.activo ? 'Activo' : 'Inactivo'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Modal Nueva Orden de Compra */}
      <Modal open={ocModal} onClose={() => setOcModal(false)} title="Emitir Orden de Compra">
        <form onSubmit={handleCreateOC} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <div className="field">
            <label>Proveedor</label>
            <select value={ocProveedor} onChange={(e) => setOcProveedor(e.target.value)}>
              {suppliers.map((s) => <option key={s.id_proveedor} value={s.id_proveedor}>{s.razon_social}</option>)}
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--ink-secondary)' }}>Productos solicitados</label>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setOcItems([...ocItems, { id_producto: products[0]?.id_producto || 1, cantidad_pedida: 5, costo_unitario: 25000 }])}
              >
                <Plus size={13} /> Línea
              </button>
            </div>
            {ocItems.map((it, idx) => (
              <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1.6fr 0.7fr 1fr auto', gap: '0.45rem', alignItems: 'center' }}>
                <select
                  value={it.id_producto}
                  onChange={(e) => setOcItems(ocItems.map((x, i) => (i === idx ? { ...x, id_producto: e.target.value } : x)))}
                >
                  {products.map((p) => <option key={p.id_producto} value={p.id_producto}>{p.codigo} — {p.nombre}</option>)}
                </select>
                <input
                  type="number"
                  min="1"
                  value={it.cantidad_pedida}
                  onChange={(e) => setOcItems(ocItems.map((x, i) => (i === idx ? { ...x, cantidad_pedida: e.target.value } : x)))}
                  placeholder="Cant."
                />
                <input
                  type="number"
                  min="1"
                  value={it.costo_unitario}
                  onChange={(e) => setOcItems(ocItems.map((x, i) => (i === idx ? { ...x, costo_unitario: e.target.value } : x)))}
                  placeholder="Costo"
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={ocItems.length === 1}
                  onClick={() => setOcItems(ocItems.filter((_, i) => i !== idx))}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.5rem', borderTop: '1px solid var(--border)' }}>
            <span>Total estimado: <strong className="mono">{formatMoney(ocTotalPreview)}</strong></span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setOcModal(false)}>Cancelar</button>
              <button type="submit" className="btn">Emitir Orden</button>
            </div>
          </div>
        </form>
      </Modal>

      {/* Modal Recepción de Mercancía (elige bodega y cantidades) */}
      <Modal
        open={Boolean(receiveTarget)}
        onClose={() => setReceiveTarget(null)}
        title={`Recibir Mercancía — ${receiveTarget?.numero || ''}`}
      >
        {receiveTarget && (
          <form onSubmit={handleConfirmReceive} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
            <div className="field">
              <label>Bodega de Ingreso</label>
              <select value={recBodega} onChange={(e) => setRecBodega(e.target.value)}>
                {warehouses.map((w) => <option key={w.id_bodega} value={w.id_bodega}>{w.codigo} — {w.nombre}</option>)}
              </select>
            </div>

            <div className="table-wrapper">
              <table>
                <thead><tr><th>Producto</th><th>Pedido</th><th>A Recibir</th></tr></thead>
                <tbody>
                  {receiveTarget.detalles.map((d) => (
                    <tr key={d.id_detalle_orden}>
                      <td>{productMap[d.id_producto]?.nombre || `Producto #${d.id_producto}`}</td>
                      <td className="mono">{d.cantidad_pedida}</td>
                      <td>
                        <input
                          type="number"
                          min="0"
                          max={d.cantidad_pedida}
                          style={{ width: '90px' }}
                          value={recQtys[d.id_detalle_orden] ?? 0}
                          onChange={(e) => setRecQtys({ ...recQtys, [d.id_detalle_orden]: e.target.value })}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setReceiveTarget(null)}>Cancelar</button>
              <button type="submit" className="btn btn-sage">Confirmar Entrada en Inventario</button>
            </div>
          </form>
        )}
      </Modal>

      {/* Modal Nuevo Proveedor */}
      <Modal open={supModal} onClose={() => setSupModal(false)} title="Registrar Proveedor (RF03)">
        <form onSubmit={handleCreateSupplier} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <div className="form-grid">
            <div className="field">
              <label>NIT / Identificación</label>
              <input value={supForm.identificacion} onChange={(e) => setSupForm({ ...supForm, identificacion: e.target.value })} placeholder="NIT-900..." required />
            </div>
            <div className="field">
              <label>Teléfono</label>
              <input value={supForm.telefono} onChange={(e) => setSupForm({ ...supForm, telefono: e.target.value })} />
            </div>
          </div>
          <div className="field">
            <label>Razón Social</label>
            <input value={supForm.razon_social} onChange={(e) => setSupForm({ ...supForm, razon_social: e.target.value })} required />
          </div>
          <div className="form-grid">
            <div className="field">
              <label>Persona de Contacto</label>
              <input value={supForm.contacto} onChange={(e) => setSupForm({ ...supForm, contacto: e.target.value })} />
            </div>
            <div className="field">
              <label>Correo</label>
              <input type="email" value={supForm.correo} onChange={(e) => setSupForm({ ...supForm, correo: e.target.value })} />
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setSupModal(false)}>Cancelar</button>
            <button type="submit" className="btn">Guardar Proveedor</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

import React, { useMemo, useState } from 'react'
import {
  Search,
  Plus,
  Minus,
  Trash2,
  Banknote,
  ArrowLeftRight,
  CreditCard,
  CheckCircle2,
  Printer,
  ShoppingBag,
} from 'lucide-react'
import { apiFetch } from '../api'
import { formatMoney, formatDate, toLocalDateKey } from '../utils/format'
import Modal from './Modal'

export default function PosView({
  user,
  products,
  categories,
  warehouses,
  stocks,
  sales,
  usersList = [],
  onSaleCompleted,
  notify,
}) {
  const [subTab, setSubTab] = useState('pos') // 'pos' | 'historial'
  const [search, setSearch] = useState('')
  const [selectedCat, setSelectedCat] = useState('ALL')
  const [bodegaId, setBodegaId] = useState(1)
  const [metodoPago, setMetodoPago] = useState('EFECTIVO')
  const [efectivoRecibido, setEfectivoRecibido] = useState('')
  const [cart, setCart] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [receipt, setReceipt] = useState(null)

  // Filtros historial
  const [histMetodo, setHistMetodo] = useState('ALL')
  const [histQuery, setHistQuery] = useState('')
  const [histFecha, setHistFecha] = useState('')
  const [histUsuario, setHistUsuario] = useState('ALL')

  // Mapa rápido de stock disponible en la bodega seleccionada
  const stockByProduct = useMemo(() => {
    const m = {}
    stocks.forEach((s) => {
      if (Number(s.id_bodega) === Number(bodegaId)) {
        m[s.id_producto] = Number(s.cantidad_disponible || 0)
      }
    })
    return m
  }, [stocks, bodegaId])

  const cartQtyMap = useMemo(() => {
    const m = {}
    cart.forEach((c) => { m[c.id_producto] = c.cantidad })
    return m
  }, [cart])

  const filteredProducts = useMemo(() => {
    const q = search.trim().toLowerCase()
    return products.filter((p) => {
      if (!p.activo) return false
      if (selectedCat !== 'ALL' && Number(p.id_categoria) !== Number(selectedCat)) return false
      if (!q) return true
      return (
        p.nombre.toLowerCase().includes(q) ||
        p.codigo.toLowerCase().includes(q) ||
        (p.categoria_nombre || '').toLowerCase().includes(q)
      )
    })
  }, [products, search, selectedCat])

  const cartTotal = useMemo(
    () => cart.reduce((acc, item) => acc + item.cantidad * item.precio_unitario, 0),
    [cart]
  )

  const receivedNum = Number(efectivoRecibido || 0)
  const changeAmount = receivedNum - cartTotal
  const canConfirmCash = metodoPago !== 'EFECTIVO' || (receivedNum >= cartTotal && cartTotal > 0)

  const addToCart = (prod) => {
    const avail = stockByProduct[prod.id_producto] ?? 0
    const inCart = cartQtyMap[prod.id_producto] ?? 0
    if (avail <= 0) {
      return notify(`Sin existencias de ${prod.nombre} en esta bodega`, true)
    }
    if (inCart + 1 > avail) {
      return notify(`Solo hay ${avail} unidades disponibles en esta bodega`, true)
    }
    setCart((prev) => {
      const idx = prev.findIndex((i) => i.id_producto === prod.id_producto)
      if (idx >= 0) {
        const copy = [...prev]
        copy[idx] = { ...copy[idx], cantidad: copy[idx].cantidad + 1 }
        return copy
      }
      return [
        ...prev,
        {
          id_producto: prod.id_producto,
          codigo: prod.codigo,
          nombre: prod.nombre,
          unidad_medida: prod.unidad_medida,
          precio_unitario: Number(prod.precio_venta),
          cantidad: 1,
        },
      ]
    })
  }

  const updateCartQty = (idProducto, nextQty) => {
    const qty = Math.max(0, Number(nextQty || 0))
    if (qty === 0) {
      setCart((prev) => prev.filter((c) => c.id_producto !== idProducto))
      return
    }
    const avail = stockByProduct[idProducto] ?? 0
    if (qty > avail) {
      notify(`Stock máximo disponible en bodega: ${avail} uds`, true)
      return
    }
    setCart((prev) => prev.map((c) => (c.id_producto === idProducto ? { ...c, cantidad: qty } : c)))
  }

  const handleCheckout = async () => {
    if (cart.length === 0) return
    if (metodoPago === 'EFECTIVO' && receivedNum < cartTotal) {
      return notify('El monto recibido en efectivo es menor al total a cobrar', true)
    }

    setSubmitting(true)
    try {
      const res = await apiFetch('ventas', '/sales', {
        method: 'POST',
        body: JSON.stringify({
          id_bodega: Number(bodegaId),
          id_usuario: user?.id_usuario || 1,
          metodo_pago: metodoPago,
          items: cart.map((c) => ({
            id_producto: c.id_producto,
            cantidad: Number(c.cantidad),
            precio_unitario: Number(c.precio_unitario),
          })),
        }),
      })

      const bodName = warehouses.find((w) => Number(w.id_bodega) === Number(bodegaId))?.nombre || `BOD-0${bodegaId}`
      setReceipt({
        venta: res.venta,
        bodegaNombre: bodName,
        items: cart,
        recibido: metodoPago === 'EFECTIVO' ? receivedNum : cartTotal,
        devuelta: metodoPago === 'EFECTIVO' ? Math.max(0, changeAmount) : 0,
      })

      setCart([])
      setEfectivoRecibido('')
      await onSaleCompleted()
      notify(`Venta ${res.venta.numero} cobrada · Inventario descontado`)
    } catch (err) {
      notify(`No se pudo procesar la venta: ${err.message}`, true)
    } finally {
      setSubmitting(false)
    }
  }

  // Sugerencias rápidas de billetes para pago en efectivo
  const quickCashOptions = useMemo(() => {
    if (cartTotal <= 0) return []
    const roundUp = (step) => Math.ceil(cartTotal / step) * step
    const candidates = [cartTotal, roundUp(5000), roundUp(10000), roundUp(20000), roundUp(50000), 100000]
    return [...new Set(candidates.filter((v) => v >= cartTotal))].slice(0, 4)
  }, [cartTotal])

  const userMap = useMemo(() => {
    const m = {}
    usersList.forEach((u) => { m[u.id_usuario] = u })
    return m
  }, [usersList])

  const filteredHistory = useMemo(() => {
    const q = histQuery.trim().toLowerCase()
    return sales.filter((s) => {
      if (histMetodo !== 'ALL' && s.metodo_pago !== histMetodo) return false
      if (histUsuario !== 'ALL' && Number(s.id_usuario) !== Number(histUsuario)) return false
      if (histFecha && toLocalDateKey(s.fecha) !== histFecha) return false
      if (!q) return true
      return s.numero.toLowerCase().includes(q)
    })
  }, [sales, histMetodo, histUsuario, histFecha, histQuery])

  return (
    <div className="view-enter">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div className="seg-tabs" role="tablist">
          <button
            type="button"
            className={`seg-tab ${subTab === 'pos' ? 'active' : ''}`}
            onClick={() => setSubTab('pos')}
          >
            Caja / Cobrar Venta
          </button>
          <button
            type="button"
            className={`seg-tab ${subTab === 'historial' ? 'active' : ''}`}
            onClick={() => setSubTab('historial')}
          >
            Historial de Ventas ({sales.length})
          </button>
        </div>
      </div>

      {subTab === 'pos' ? (
        <div className="pos-grid">
          {/* IZQUIERDA: Buscador + Lista de productos con stock */}
          <section className="panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">Productos en Catálogo</h3>
                <p className="panel-desc">Busca por nombre o código y agrégalos al cobro</p>
              </div>
              <div style={{ minWidth: '210px' }}>
                <select
                  aria-label="Bodega de despacho"
                  value={bodegaId}
                  onChange={(e) => {
                    setBodegaId(Number(e.target.value))
                    setCart([])
                  }}
                >
                  {warehouses.map((w) => (
                    <option key={w.id_bodega} value={w.id_bodega}>
                      Despacho: {w.codigo} — {w.nombre}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="search-bar">
              <Search size={16} />
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar producto por nombre, SKU (ej. FER-001) o categoría..."
              />
            </div>

            <div className="chip-row">
              <button
                type="button"
                className={`filter-chip ${selectedCat === 'ALL' ? 'active' : ''}`}
                onClick={() => setSelectedCat('ALL')}
              >
                Todas ({products.filter((p) => p.activo).length})
              </button>
              {categories.filter((c) => c.activo && !c.id_categoria_padre).map((c) => (
                <button
                  key={c.id_categoria}
                  type="button"
                  className={`filter-chip ${Number(selectedCat) === Number(c.id_categoria) ? 'active' : ''}`}
                  onClick={() => setSelectedCat(c.id_categoria)}
                >
                  {c.nombre}
                </button>
              ))}
            </div>

            <div className="pos-product-list">
              {filteredProducts.length === 0 ? (
                <p style={{ color: 'var(--ink-muted)', padding: '1.5rem 0', textAlign: 'center' }}>
                  No se encontraron productos con ese criterio.
                </p>
              ) : (
                filteredProducts.map((p) => {
                  const stock = stockByProduct[p.id_producto] ?? 0
                  const inCart = cartQtyMap[p.id_producto] ?? 0
                  const remaining = stock - inCart
                  const isOut = stock <= 0

                  return (
                    <div key={p.id_producto} className={`pos-product-row ${isOut ? 'out' : ''}`}>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
                          <code style={{ fontSize: '0.75rem', color: 'var(--ink-muted)', background: 'var(--surface-muted)', padding: '0.1rem 0.4rem', borderRadius: '4px' }}>
                            {p.codigo}
                          </code>
                          <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{p.nombre}</span>
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--ink-muted)', marginTop: '0.15rem' }}>
                          {p.categoria_nombre} · {p.unidad_medida}
                        </div>
                      </div>

                      <div>
                        <span className={`badge ${remaining <= 0 ? 'badge-crimson' : remaining <= 5 ? 'badge-ochre' : 'badge-sage'}`}>
                          {remaining} disp.
                        </span>
                      </div>

                      <div className="mono" style={{ fontWeight: 700, fontSize: '0.92rem' }}>
                        {formatMoney(p.precio_venta)}
                      </div>

                      <button
                        type="button"
                        className="btn btn-sm"
                        disabled={remaining <= 0}
                        onClick={() => addToCart(p)}
                      >
                        <Plus size={14} /> Agregar
                      </button>
                    </div>
                  )
                })
              )}
            </div>
          </section>

          {/* DERECHA: Ticket de Cobro + Método de Pago + Cálculo de Devuelta */}
          <aside className="panel pos-checkout-panel">
            <div className="panel-header">
              <div>
                <h3 className="panel-title">
                  <ShoppingBag size={17} /> Ticket de Cobro
                </h3>
                <p className="panel-desc">
                  Bodega {warehouses.find((w) => Number(w.id_bodega) === Number(bodegaId))?.codigo || `BOD-0${bodegaId}`}
                </p>
              </div>
              {cart.length > 0 && (
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setCart([])}>
                  Vaciar
                </button>
              )}
            </div>

            {cart.length === 0 ? (
              <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--ink-muted)', border: '1px dashed var(--border-strong)', borderRadius: 'var(--radius-sm)' }}>
                Agrega productos desde la lista para iniciar el cobro.
              </div>
            ) : (
              <div className="cart-list">
                {cart.map((item) => (
                  <div key={item.id_producto} className="cart-item">
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.84rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.nombre}
                      </div>
                      <div className="mono" style={{ fontSize: '0.75rem', color: 'var(--ink-muted)' }}>
                        {formatMoney(item.precio_unitario)} c/u
                      </div>
                    </div>

                    <div className="qty-stepper">
                      <button type="button" aria-label="Disminuir cantidad" onClick={() => updateCartQty(item.id_producto, item.cantidad - 1)}>
                        <Minus size={13} />
                      </button>
                      <input
                        type="number"
                        min="1"
                        value={item.cantidad}
                        onChange={(e) => updateCartQty(item.id_producto, e.target.value)}
                      />
                      <button type="button" aria-label="Aumentar cantidad" onClick={() => updateCartQty(item.id_producto, item.cantidad + 1)}>
                        <Plus size={13} />
                      </button>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                      <span className="mono" style={{ fontWeight: 700, fontSize: '0.85rem' }}>
                        {formatMoney(item.cantidad * item.precio_unitario)}
                      </span>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '0.25rem 0.4rem' }}
                        onClick={() => updateCartQty(item.id_producto, 0)}
                        aria-label={`Quitar ${item.nombre}`}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Total */}
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: 'var(--ink-muted)' }}>
                <span>Ítems ({cart.reduce((a, b) => a + b.cantidad, 0)} unidades)</span>
                <span className="mono">{formatMoney(cartTotal)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontWeight: 700, fontSize: '1rem' }}>Total a Cobrar</span>
                <span className="mono" style={{ fontWeight: 700, fontSize: '1.5rem', color: 'var(--accent)' }}>
                  {formatMoney(cartTotal)}
                </span>
              </div>
            </div>

            {/* Método de pago */}
            <div className="field">
              <label>Método de Pago</label>
              <div className="payment-methods">
                {[
                  { id: 'EFECTIVO', label: 'Efectivo', icon: Banknote },
                  { id: 'TRANSFERENCIA', label: 'Transferencia', icon: ArrowLeftRight },
                  { id: 'TARJETA', label: 'Tarjeta', icon: CreditCard },
                ].map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    type="button"
                    className={`payment-btn ${metodoPago === id ? 'active' : ''}`}
                    onClick={() => setMetodoPago(id)}
                  >
                    <Icon size={17} />
                    <span>{label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Cálculo automático de devuelta si es Efectivo */}
            {metodoPago === 'EFECTIVO' && (
              <div className="change-box">
                <div className="field">
                  <label htmlFor="cash-received">Efectivo Recibido (COP)</label>
                  <input
                    id="cash-received"
                    type="number"
                    min="0"
                    step="500"
                    className="mono"
                    value={efectivoRecibido}
                    onChange={(e) => setEfectivoRecibido(e.target.value)}
                    placeholder="Ej. 100000"
                  />
                </div>

                {quickCashOptions.length > 0 && (
                  <div className="chip-row">
                    {quickCashOptions.map((val) => (
                      <button
                        key={val}
                        type="button"
                        className={`filter-chip mono ${Number(efectivoRecibido) === val ? 'active' : ''}`}
                        onClick={() => setEfectivoRecibido(String(val))}
                      >
                        {val === cartTotal ? 'Exacto' : formatMoney(val)}
                      </button>
                    ))}
                  </div>
                )}

                {cartTotal > 0 && (
                  <div className={`change-result ${changeAmount >= 0 ? 'ok' : 'missing'}`}>
                    <span>{changeAmount >= 0 ? 'Devuelta al cliente' : 'Saldo faltante'}</span>
                    <span className="mono" style={{ fontSize: '1.05rem' }}>
                      {formatMoney(Math.abs(changeAmount))}
                    </span>
                  </div>
                )}
              </div>
            )}

            <button
              type="button"
              className="btn btn-sage"
              style={{ width: '100%', minBlockSize: '2.75rem', fontSize: '0.9375rem' }}
              disabled={submitting || cart.length === 0 || !canConfirmCash}
              onClick={handleCheckout}
            >
              <CheckCircle2 size={17} />
              {submitting ? 'Procesando y descontando...' : 'Confirmar Cobro y Descontar Inventario'}
            </button>
          </aside>
        </div>
      ) : (
        /* HISTORIAL DE VENTAS (RF16) */
        <section className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Historial de Ventas (RF16)</h3>
              <p className="panel-desc">Consulta ventas confirmadas o rechazadas con filtros por método de pago</p>
            </div>
            <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
              <div className="search-bar" style={{ minWidth: '180px' }}>
                <Search size={15} />
                <input
                  value={histQuery}
                  onChange={(e) => setHistQuery(e.target.value)}
                  placeholder="Buscar por # venta..."
                />
              </div>
              <input
                type="date"
                aria-label="Filtrar por fecha"
                style={{ width: 'auto' }}
                value={histFecha}
                onChange={(e) => setHistFecha(e.target.value)}
              />
              <select style={{ width: 'auto' }} value={histUsuario} onChange={(e) => setHistUsuario(e.target.value)}>
                <option value="ALL">Todos los vendedores</option>
                {usersList.map((u) => (
                  <option key={u.id_usuario} value={u.id_usuario}>{u.nombre}</option>
                ))}
              </select>
              <select style={{ width: 'auto' }} value={histMetodo} onChange={(e) => setHistMetodo(e.target.value)}>
                <option value="ALL">Todos los métodos</option>
                <option value="EFECTIVO">Efectivo</option>
                <option value="TRANSFERENCIA">Transferencia</option>
                <option value="TARJETA">Tarjeta</option>
              </select>
            </div>
          </div>

          <div className="table-wrapper" role="region" aria-label="Historial de ventas" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Comprobante</th>
                  <th>Fecha</th>
                  <th>Vendedor</th>
                  <th>Bodega</th>
                  <th>Método de Pago</th>
                  <th>Ítems</th>
                  <th>Total</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {filteredHistory.map((s) => (
                  <tr key={s.id_venta}>
                    <td className="mono" style={{ fontWeight: 600 }}>{s.numero}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--ink-muted)' }}>{formatDate(s.fecha)}</td>
                    <td style={{ fontSize: '0.8rem' }}>{userMap[s.id_usuario]?.nombre || `Usuario #${s.id_usuario}`}</td>
                    <td className="mono">BOD-0{s.id_bodega}</td>
                    <td>{s.metodo_pago}</td>
                    <td className="mono">{(s.detalles || []).length} ref.</td>
                    <td className="mono" style={{ fontWeight: 700 }}>{formatMoney(s.total)}</td>
                    <td>
                      <span className={`badge ${s.estado === 'CONFIRMADA' ? 'badge-sage' : 'badge-crimson'}`}>
                        {s.estado}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Modal Comprobante de Venta Confirmada */}
      <Modal
        open={Boolean(receipt)}
        onClose={() => setReceipt(null)}
        title="Comprobante de Venta Confirmada"
      >
        {receipt && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: 'var(--sage-soft)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--sage-border)' }}>
              <span style={{ color: 'var(--sage)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <CheckCircle2 size={17} /> Stock descontado correctamente
              </span>
              <span className="mono" style={{ fontWeight: 700 }}>{receipt.venta.numero}</span>
            </div>

            <div style={{ fontSize: '0.84rem', color: 'var(--ink-secondary)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
              <span><b>Bodega:</b> {receipt.bodegaNombre}</span>
              <span><b>Método:</b> {receipt.venta.metodo_pago}</span>
              <span><b>Fecha:</b> {formatDate(receipt.venta.fecha)}</span>
              <span><b>Estado:</b> {receipt.venta.estado}</span>
            </div>

            <div className="table-wrapper">
              <table>
                <thead>
                  <tr><th>Producto</th><th>Cant.</th><th>Subtotal</th></tr>
                </thead>
                <tbody>
                  {receipt.items.map((it) => (
                    <tr key={it.id_producto}>
                      <td>{it.nombre}</td>
                      <td className="mono">{it.cantidad}</td>
                      <td className="mono">{formatMoney(it.cantidad * it.precio_unitario)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ background: 'var(--surface-muted)', padding: '0.85rem', borderRadius: 'var(--radius-sm)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Total venta</span>
                <strong className="mono">{formatMoney(receipt.venta.total)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                <span>Recibido</span>
                <span className="mono">{formatMoney(receipt.recibido)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.95rem', color: 'var(--sage)', fontWeight: 700 }}>
                <span>Devuelta</span>
                <span className="mono">{formatMoney(receipt.devuelta)}</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.6rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => window.print()}>
                <Printer size={15} /> Imprimir
              </button>
              <button type="button" className="btn" onClick={() => setReceipt(null)}>
                Nueva Venta
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

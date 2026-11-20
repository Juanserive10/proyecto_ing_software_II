import React, { useMemo, useState } from 'react'
import {
  ArrowLeft,
  Calendar,
  Clock,
  Download,
  PackageCheck,
  Receipt,
  Search,
  ShoppingCart,
  TrendingUp,
} from 'lucide-react'
import { downloadCsv, formatMoney, formatTime, toLocalDateKey } from '../utils/format'

export default function DailySalesView({
  sales,
  products,
  warehouses,
  onBack,
  onGoPos,
}) {
  const [selectedDate, setSelectedDate] = useState(() => toLocalDateKey(new Date()))
  const [viewMode, setViewMode] = useState('productos') // 'productos' | 'comprobantes'
  const [searchQ, setSearchQ] = useState('')
  const [metodoFilter, setMetodoFilter] = useState('ALL')

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

  const todayKey = toLocalDateKey(new Date())

  // Ventas del día seleccionado
  const daySales = useMemo(() => {
    return sales.filter((s) => {
      if (toLocalDateKey(s.fecha) !== selectedDate) return false
      if (metodoFilter !== 'ALL' && s.metodo_pago !== metodoFilter) return false
      return true
    })
  }, [sales, selectedDate, metodoFilter])

  const confirmedDaySales = useMemo(
    () => daySales.filter((s) => s.estado === 'CONFIRMADA'),
    [daySales]
  )

  // Filas planas por producto vendido en el día (hora, producto, cantidad, valor)
  const productLines = useMemo(() => {
    const q = searchQ.trim().toLowerCase()
    const rows = []
    daySales.forEach((sale) => {
      ;(sale.detalles || []).forEach((det) => {
        const prod = productMap[det.id_producto]
        const codigo = prod?.codigo || `ID-${det.id_producto}`
        const nombre = prod?.nombre || `Producto #${det.id_producto}`
        if (
          q &&
          !nombre.toLowerCase().includes(q) &&
          !codigo.toLowerCase().includes(q) &&
          !sale.numero.toLowerCase().includes(q)
        ) {
          return
        }
        rows.push({
          key: `${sale.id_venta}-${det.id_detalle_venta}`,
          id_venta: sale.id_venta,
          numero: sale.numero,
          fecha: sale.fecha,
          hora: formatTime(sale.fecha),
          codigo,
          nombre,
          categoria: prod?.categoria_nombre || '',
          cantidad: Number(det.cantidad || 0),
          precio_unitario: Number(det.precio_unitario || 0),
          valor: Number(det.subtotal || 0),
          bodega: warehouseMap[sale.id_bodega]?.codigo || `BOD-0${sale.id_bodega}`,
          metodo_pago: sale.metodo_pago,
          estado: sale.estado,
        })
      })
    })
    return rows
  }, [daySales, productMap, warehouseMap, searchQ])

  const totalVendido = confirmedDaySales.reduce((acc, s) => acc + Number(s.total || 0), 0)
  const unidadesVendidas = confirmedDaySales.reduce(
    (acc, s) => acc + (s.detalles || []).reduce((dAcc, d) => dAcc + Number(d.cantidad || 0), 0),
    0
  )
  const ticketPromedio = confirmedDaySales.length > 0 ? totalVendido / confirmedDaySales.length : 0

  const handleExportDay = () => {
    downloadCsv(
      `ventas_detalle_${selectedDate}.csv`,
      ['Hora', 'Comprobante', 'Codigo', 'Producto', 'Cantidad', 'Valor Unitario', 'Valor Total', 'Bodega', 'Metodo Pago', 'Estado'],
      productLines.map((r) => [
        r.hora,
        r.numero,
        r.codigo,
        r.nombre,
        r.cantidad,
        r.precio_unitario,
        r.valor,
        r.bodega,
        r.metodo_pago,
        r.estado,
      ])
    )
  }

  return (
    <div className="view-enter">
      {/* Barra superior de navegación de regreso y filtro de día */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onBack}>
            <ArrowLeft size={14} /> Volver al Dashboard
          </button>

          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', background: 'var(--surface)', border: '1px solid var(--border)', padding: '0.25rem 0.6rem', borderRadius: 'var(--radius-sm)' }}>
            <Calendar size={14} color="var(--ink-muted)" />
            <input
              type="date"
              aria-label="Seleccionar fecha"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              style={{ border: 'none', padding: '0.2rem', width: 'auto', boxShadow: 'none' }}
            />
            {selectedDate !== todayKey && (
              <button type="button" className="filter-chip" onClick={() => setSelectedDate(todayKey)}>
                Ir a Hoy
              </button>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleExportDay} disabled={productLines.length === 0}>
            <Download size={14} /> Exportar CSV
          </button>
          <button type="button" className="btn btn-sage btn-sm" onClick={onGoPos}>
            <ShoppingCart size={14} /> Nueva Venta
          </button>
        </div>
      </div>

      {/* 4 KPIs del día */}
      <section className="kpi-grid">
        <article className="kpi-card">
          <div className="kpi-header">
            <span>Total Vendido {selectedDate === todayKey ? 'Hoy' : selectedDate}</span>
            <span className="kpi-icon-box sage"><TrendingUp size={16} /></span>
          </div>
          <div className="kpi-value">{formatMoney(totalVendido)}</div>
          <div className="kpi-meta">{confirmedDaySales.length} ventas confirmadas</div>
        </article>

        <article className="kpi-card">
          <div className="kpi-header">
            <span>Unidades Despachadas</span>
            <span className="kpi-icon-box teal"><PackageCheck size={16} /></span>
          </div>
          <div className="kpi-value">{unidadesVendidas}</div>
          <div className="kpi-meta">{productLines.filter((r) => r.estado === 'CONFIRMADA').length} líneas de producto</div>
        </article>

        <article className="kpi-card">
          <div className="kpi-header">
            <span>Ticket Promedio</span>
            <span className="kpi-icon-box"><Receipt size={16} /></span>
          </div>
          <div className="kpi-value">{formatMoney(ticketPromedio)}</div>
          <div className="kpi-meta">Por comprobante confirmado</div>
        </article>

        <article className="kpi-card">
          <div className="kpi-header">
            <span>Última Operación</span>
            <span className="kpi-icon-box ochre"><Clock size={16} /></span>
          </div>
          <div className="kpi-value" style={{ fontSize: '1.25rem' }}>
            {daySales[0] ? formatTime(daySales[0].fecha) : '—'}
          </div>
          <div className="kpi-meta">{daySales[0] ? daySales[0].numero : 'Sin ventas en esta fecha'}</div>
        </article>
      </section>

      {/* Panel principal con desglose por producto y hora */}
      <section className="panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-title">
              Detalle de Ventas {selectedDate === todayKey ? 'de Hoy' : `del ${selectedDate}`}
            </h3>
            <p className="panel-desc">Producto vendido, cantidad, valor y hora exacta de realización</p>
          </div>

          <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <div className="seg-tabs">
              <button
                type="button"
                className={`seg-tab ${viewMode === 'productos' ? 'active' : ''}`}
                onClick={() => setViewMode('productos')}
              >
                Por Producto ({productLines.length})
              </button>
              <button
                type="button"
                className={`seg-tab ${viewMode === 'comprobantes' ? 'active' : ''}`}
                onClick={() => setViewMode('comprobantes')}
              >
                Por Comprobante ({daySales.length})
              </button>
            </div>

            <div className="search-bar" style={{ minWidth: '210px' }}>
              <Search size={15} />
              <input
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="Buscar producto o # venta..."
              />
            </div>

            <select style={{ width: 'auto' }} value={metodoFilter} onChange={(e) => setMetodoFilter(e.target.value)}>
              <option value="ALL">Todos los métodos</option>
              <option value="EFECTIVO">Efectivo</option>
              <option value="TRANSFERENCIA">Transferencia</option>
              <option value="TARJETA">Tarjeta</option>
            </select>
          </div>
        </div>

        {viewMode === 'productos' ? (
          <div className="table-wrapper" role="region" aria-label="Detalle por producto vendido hoy" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Hora</th>
                  <th>Comprobante</th>
                  <th>Producto Vendido</th>
                  <th>Cantidad</th>
                  <th>Precio Unit.</th>
                  <th>Valor Total</th>
                  <th>Bodega</th>
                  <th>Método</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {productLines.length === 0 ? (
                  <tr>
                    <td colSpan={9} style={{ textAlign: 'center', color: 'var(--ink-muted)', padding: '2rem' }}>
                      No hay ventas registradas para esta fecha con los filtros seleccionados.
                    </td>
                  </tr>
                ) : (
                  productLines.map((row) => (
                    <tr key={row.key}>
                      <td className="mono" style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{row.hora}</td>
                      <td className="mono" style={{ color: 'var(--ink-secondary)' }}>{row.numero}</td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{row.nombre}</div>
                        <div className="mono" style={{ fontSize: '0.73rem', color: 'var(--ink-muted)' }}>
                          {row.codigo}{row.categoria ? ` · ${row.categoria}` : ''}
                        </div>
                      </td>
                      <td className="mono" style={{ fontWeight: 600 }}>{row.cantidad}</td>
                      <td className="mono" style={{ color: 'var(--ink-secondary)' }}>{formatMoney(row.precio_unitario)}</td>
                      <td className="mono" style={{ fontWeight: 700, color: 'var(--accent)' }}>{formatMoney(row.valor)}</td>
                      <td className="mono">{row.bodega}</td>
                      <td>{row.metodo_pago}</td>
                      <td>
                        <span className={`badge ${row.estado === 'CONFIRMADA' ? 'badge-sage' : 'badge-crimson'}`}>
                          {row.estado}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="table-wrapper" role="region" aria-label="Comprobantes de venta del día" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Hora</th>
                  <th>Comprobante</th>
                  <th>Productos Incluidos</th>
                  <th>Bodega</th>
                  <th>Método de Pago</th>
                  <th>Total Venta</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {daySales.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: 'center', color: 'var(--ink-muted)', padding: '2rem' }}>
                      No hay comprobantes para esta fecha.
                    </td>
                  </tr>
                ) : (
                  daySales.map((s) => (
                    <tr key={s.id_venta}>
                      <td className="mono" style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{formatTime(s.fecha)}</td>
                      <td className="mono" style={{ fontWeight: 600 }}>{s.numero}</td>
                      <td style={{ fontSize: '0.82rem' }}>
                        {(s.detalles || []).map((d) => {
                          const p = productMap[d.id_producto]
                          return `${p?.nombre || `#${d.id_producto}`} (×${d.cantidad})`
                        }).join(', ')}
                      </td>
                      <td className="mono">{warehouseMap[s.id_bodega]?.codigo || `BOD-0${s.id_bodega}`}</td>
                      <td>{s.metodo_pago}</td>
                      <td className="mono" style={{ fontWeight: 700 }}>{formatMoney(s.total)}</td>
                      <td>
                        <span className={`badge ${s.estado === 'CONFIRMADA' ? 'badge-sage' : 'badge-crimson'}`}>
                          {s.estado}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

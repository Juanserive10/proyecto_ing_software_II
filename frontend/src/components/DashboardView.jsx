import React, { useMemo } from 'react'
import {
  Wallet,
  Boxes,
  TrendingUp,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react'
import { formatMoney, formatDate, toLocalDateKey } from '../utils/format'
import {
  StockWarehouseChart,
  HorizontalBarChart,
  DonutBreakdownChart,
  SalesTrendAreaChart,
} from './Charts'

export default function DashboardView({
  dashboard,
  products,
  stocks,
  sales,
  alerts,
  warehouses,
  onNavigate,
}) {
  const productMap = useMemo(() => {
    const m = {}
    products.forEach((p) => { m[p.id_producto] = p })
    return m
  }, [products])

  // Agrupar stock por producto entre BOD-01 y BOD-02 para el gráfico comparativo
  const stockChartData = useMemo(() => {
    const byProd = {}
    stocks.forEach((s) => {
      if (!byProd[s.id_producto]) {
        const p = productMap[s.id_producto]
        byProd[s.id_producto] = {
          id_producto: s.id_producto,
          codigo: p?.codigo || `P-${s.id_producto}`,
          nombre: p?.nombre || `Producto #${s.id_producto}`,
          b1: 0,
          b2: 0,
        }
      }
      if (s.id_bodega === 1) byProd[s.id_producto].b1 += Number(s.cantidad_disponible || 0)
      else byProd[s.id_producto].b2 += Number(s.cantidad_disponible || 0)
    })
    return Object.values(byProd)
      .sort((a, b) => (b.b1 + b.b2) - (a.b1 + a.b2))
      .slice(0, 8)
  }, [stocks, productMap])

  // Valor total del inventario calculado directamente si dashboard aún no ha sincronizado
  const inventoryStats = useMemo(() => {
    let totalUnits = 0
    let totalValue = 0
    let b1Units = 0
    let b2Units = 0
    stocks.forEach((s) => {
      const qty = Number(s.cantidad_disponible || 0)
      const price = Number(productMap[s.id_producto]?.precio_venta || 0)
      totalUnits += qty
      totalValue += qty * price
      if (s.id_bodega === 1) b1Units += qty
      if (s.id_bodega === 2) b2Units += qty
    })
    return {
      totalUnits,
      totalValue: dashboard?.valor_total_inventario || totalValue,
      b1Units,
      b2Units,
    }
  }, [stocks, productMap, dashboard])

  const confirmedSales = useMemo(
    () => sales.filter((s) => s.estado === 'CONFIRMADA'),
    [sales]
  )

  const todayKey = toLocalDateKey(new Date())
  const todayConfirmed = useMemo(
    () => confirmedSales.filter((s) => toLocalDateKey(s.fecha) === todayKey),
    [confirmedSales, todayKey]
  )
  const todayRevenue = useMemo(
    () => todayConfirmed.reduce((acc, s) => acc + Number(s.total || 0), 0),
    [todayConfirmed]
  )

  const totalRevenue = useMemo(
    () => confirmedSales.reduce((acc, s) => acc + Number(s.total || 0), 0),
    [confirmedSales]
  )

  // Top productos vendidos a partir de ventas confirmadas
  const topProductsData = useMemo(() => {
    const agg = {}
    confirmedSales.forEach((s) => {
      ;(s.detalles || []).forEach((d) => {
        if (!agg[d.id_producto]) {
          agg[d.id_producto] = { units: 0, revenue: 0 }
        }
        agg[d.id_producto].units += Number(d.cantidad || 0)
        agg[d.id_producto].revenue += Number(d.subtotal || 0)
      })
    })
    return Object.entries(agg)
      .map(([id, vals]) => ({
        label: productMap[id]?.nombre || `Producto #${id}`,
        value: vals.revenue,
        sub: `${vals.units} uds`,
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 5)
  }, [confirmedSales, productMap])

  // Ventas por método de pago
  const paymentBreakdown = useMemo(() => {
    const sums = { EFECTIVO: 0, TRANSFERENCIA: 0, TARJETA: 0 }
    confirmedSales.forEach((s) => {
      const m = s.metodo_pago || 'EFECTIVO'
      sums[m] = (sums[m] || 0) + Number(s.total || 0)
    })
    return [
      { label: 'Efectivo', value: sums.EFECTIVO, color: '#1E3A5F' },
      { label: 'Transferencia', value: sums.TRANSFERENCIA, color: '#2B6C6D' },
      { label: 'Tarjeta', value: sums.TARJETA, color: '#B87A2A' },
    ].filter((s) => s.value > 0)
  }, [confirmedSales])

  const activeAlerts = useMemo(() => alerts.filter((a) => a.estado === 'ACTIVA'), [alerts])

  return (
    <div className="view-enter">
      {/* 4 KPIs esenciales */}
      <section className="kpi-grid" aria-label="Indicadores principales">
        <article className="kpi-card">
          <div className="kpi-header">
            <span>Valor del Inventario</span>
            <span className="kpi-icon-box"><Boxes size={16} /></span>
          </div>
          <div className="kpi-value">{formatMoney(inventoryStats.totalValue)}</div>
          <div className="kpi-meta">
            <span className="mono">{inventoryStats.totalUnits}</span> unidades en {warehouses.length || 2} bodegas
          </div>
        </article>

        <article className="kpi-card">
          <div className="kpi-header">
            <span>Ingresos por Ventas</span>
            <span className="kpi-icon-box sage"><TrendingUp size={16} /></span>
          </div>
          <div className="kpi-value">{formatMoney(totalRevenue)}</div>
          <div className="kpi-meta" style={{ justifyContent: 'space-between', width: '100%' }}>
            <span>Hoy: <strong className="mono">{formatMoney(todayRevenue)}</strong> ({todayConfirmed.length})</span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ minBlockSize: '1.6rem', padding: '0.15rem 0.5rem', fontSize: '0.73rem' }}
              onClick={() => onNavigate('ventas-hoy')}
            >
              Ver hoy <ArrowRight size={12} />
            </button>
          </div>
        </article>

        <article className="kpi-card">
          <div className="kpi-header">
            <span>Distribución por Bodega</span>
            <span className="kpi-icon-box teal"><Wallet size={16} /></span>
          </div>
          <div className="kpi-value">
            {inventoryStats.b1Units} <span style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--ink-muted)' }}>/ {inventoryStats.b2Units}</span>
          </div>
          <div className="kpi-meta">Principal (BOD-01) / Norte (BOD-02)</div>
        </article>

        <article className="kpi-card">
          <div className="kpi-header">
            <span>Alertas de Stock</span>
            <span className={`kpi-icon-box ${activeAlerts.length > 0 ? 'crimson' : 'sage'}`}>
              {activeAlerts.length > 0 ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
            </span>
          </div>
          <div className="kpi-value" style={{ color: activeAlerts.length > 0 ? 'var(--crimson)' : 'var(--sage)' }}>
            {activeAlerts.length}
          </div>
          <div className="kpi-meta">
            {activeAlerts.length > 0 ? 'Productos bajo umbral mínimo' : 'Todos los niveles saludables'}
          </div>
        </article>
      </section>

      {/* Fila principal de gráficos: Stock por bodega + Evolución de ventas */}
      <section className="grid-asymmetric">
        <article className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Existencias por Bodega (Top 8 productos)</h3>
              <p className="panel-desc">Comparativa en vivo entre Bodega Principal y Punto Norte</p>
            </div>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onNavigate('inventario')}>
              Ver inventario <ArrowRight size={13} />
            </button>
          </div>
          <StockWarehouseChart items={stockChartData} />
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Ventas por Método de Pago</h3>
              <p className="panel-desc">Distribución de ingresos confirmados</p>
            </div>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onNavigate('pos')}>
              Ir a cobrar <ArrowRight size={13} />
            </button>
          </div>
          <DonutBreakdownChart
            segments={paymentBreakdown}
            centerLabel="Ingresos"
            centerValue={formatMoney(totalRevenue)}
          />
        </article>
      </section>

      {/* Segunda fila de gráficos: Tendencia de ventas + Top vendidos */}
      <section className="grid-2">
        <article className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Comportamiento de Ventas Recientes</h3>
              <p className="panel-desc">Valor por transacción confirmada (últimas 10 ventas)</p>
            </div>
          </div>
          <SalesTrendAreaChart sales={sales} />
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Productos con Mayor Facturación</h3>
              <p className="panel-desc">Participación en ventas confirmadas</p>
            </div>
          </div>
          <HorizontalBarChart items={topProductsData} />
        </article>
      </section>

      {/* Tablas de resumen: Últimas ventas y Alertas activas */}
      <section className="grid-2">
        <article className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Últimas Ventas</h3>
              <p className="panel-desc">Operaciones recientes registradas en POS</p>
            </div>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onNavigate('ventas-hoy')}>
              Detalle ventas de hoy <ArrowRight size={13} />
            </button>
          </div>
          <div className="table-wrapper" role="region" aria-label="Últimas ventas" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Comprobante</th>
                  <th>Fecha</th>
                  <th>Método</th>
                  <th>Total</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {sales.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', color: 'var(--ink-muted)' }}>
                      No hay ventas registradas todavía.
                    </td>
                  </tr>
                ) : (
                  sales.slice(0, 6).map((s) => (
                    <tr key={s.id_venta}>
                      <td className="mono" style={{ fontWeight: 600 }}>{s.numero}</td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--ink-muted)' }}>{formatDate(s.fecha)}</td>
                      <td>{s.metodo_pago}</td>
                      <td className="mono" style={{ fontWeight: 600 }}>{formatMoney(s.total)}</td>
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
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Alertas de Stock Mínimo</h3>
              <p className="panel-desc">Productos que requieren reposición</p>
            </div>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => onNavigate('reportes')}>
              Gestionar <ArrowRight size={13} />
            </button>
          </div>
          <div className="table-wrapper" role="region" aria-label="Alertas activas" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Bodega</th>
                  <th>Saldo</th>
                  <th>Mínimo</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {activeAlerts.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', color: 'var(--ink-muted)' }}>
                      No hay alertas pendientes.
                    </td>
                  </tr>
                ) : (
                  activeAlerts.slice(0, 6).map((a) => (
                    <tr key={a.id_alerta}>
                      <td style={{ fontWeight: 500 }}>
                        {productMap[a.id_producto]?.nombre || `Producto #${a.id_producto}`}
                      </td>
                      <td className="mono">BOD-0{a.id_bodega}</td>
                      <td className="mono" style={{ color: 'var(--crimson)', fontWeight: 700 }}>{a.saldo_observado}</td>
                      <td className="mono">{a.cantidad_minima}</td>
                      <td>
                        <span className="badge badge-crimson">
                          <AlertTriangle size={11} /> Activa
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </div>
  )
}

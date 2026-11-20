import React, { useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, Download, Plus } from 'lucide-react'
import { apiFetch } from '../api'
import { downloadCsv, formatDate, formatMoney } from '../utils/format'
import { DonutBreakdownChart, HorizontalBarChart } from './Charts'
import Modal from './Modal'

export default function ReportsView({
  products,
  stocks,
  movements,
  alerts,
  thresholds,
  warehouses,
  onUpdated,
  notify,
}) {
  const [umbModal, setUmbModal] = useState(false)
  const [umbForm, setUmbForm] = useState({ id_producto: 1, id_bodega: 1, cantidad_minima: 15 })

  const productMap = useMemo(() => {
    const m = {}
    products.forEach((p) => { m[p.id_producto] = p })
    return m
  }, [products])

  // Valorización del inventario por bodega
  const valuationByWarehouse = useMemo(() => {
    const sums = {}
    stocks.forEach((s) => {
      const price = Number(productMap[s.id_producto]?.precio_venta || 0)
      const val = Number(s.cantidad_disponible || 0) * price
      sums[s.id_bodega] = (sums[s.id_bodega] || 0) + val
    })
    const colors = ['#1E3A5F', '#2B6C6D', '#B87A2A']
    return warehouses.map((w, idx) => ({
      label: w.nombre,
      value: sums[w.id_bodega] || 0,
      color: colors[idx % colors.length],
    })).filter((x) => x.value > 0)
  }, [stocks, warehouses, productMap])

  const totalValuation = valuationByWarehouse.reduce((a, b) => a + b.value, 0)

  // Rotación: top productos con más movimientos registrados en Kardex
  const topMovementProducts = useMemo(() => {
    const counts = {}
    movements.forEach((m) => {
      counts[m.id_producto] = (counts[m.id_producto] || 0) + Number(m.cantidad || 0)
    })
    return Object.entries(counts)
      .map(([id, total]) => ({
        label: productMap[id]?.nombre || `Producto #${id}`,
        value: total,
        sub: 'movs',
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6)
  }, [movements, productMap])

  const handleSaveThreshold = async (e) => {
    e.preventDefault()
    try {
      await apiFetch('reportes', '/thresholds', {
        method: 'POST',
        body: JSON.stringify({
          id_producto: Number(umbForm.id_producto),
          id_bodega: Number(umbForm.id_bodega),
          cantidad_minima: Number(umbForm.cantidad_minima),
          activo: true,
        }),
      })
      setUmbModal(false)
      await onUpdated()
      notify('Umbral guardado y alertas evaluadas')
    } catch (err) {
      notify(err.message, true)
    }
  }

  const handleAckAlert = async (idAlerta) => {
    try {
      await apiFetch('reportes', `/alerts/${idAlerta}/ack`, { method: 'POST' })
      await onUpdated()
      notify('Alerta marcada como atendida')
    } catch (err) {
      notify(err.message, true)
    }
  }

  const exportInventoryReport = () => {
    downloadCsv(
      'reporte_valorizacion_inventario.csv',
      ['Bodega', 'Codigo', 'Producto', 'Disponible', 'Precio Unitario', 'Valor Total'],
      stocks.map((s) => {
        const p = productMap[s.id_producto]
        const price = Number(p?.precio_venta || 0)
        return [
          s.bodega_codigo,
          p?.codigo || s.id_producto,
          p?.nombre || '',
          s.cantidad_disponible,
          price,
          Number(s.cantidad_disponible) * price,
        ]
      })
    )
  }

  return (
    <div className="view-enter">
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', flexWrap: 'wrap' }}>
        <button type="button" className="btn btn-secondary btn-sm" onClick={exportInventoryReport}>
          <Download size={14} /> Exportar Valorización CSV
        </button>
        <button type="button" className="btn btn-sm" onClick={() => setUmbModal(true)}>
          <Plus size={14} /> Configurar Umbral Mínimo
        </button>
      </div>

      {/* Gráficos de reportes (RF11) */}
      <section className="grid-2">
        <article className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Valorización del Inventario por Bodega</h3>
              <p className="panel-desc">Capital almacenado a precio de venta actual</p>
            </div>
          </div>
          <DonutBreakdownChart
            segments={valuationByWarehouse}
            centerLabel="Valor Total"
            centerValue={formatMoney(totalValuation)}
          />
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Productos con Mayor Rotación (Unidades Movidas)</h3>
              <p className="panel-desc">Suma de entradas, salidas y traslados en Kardex</p>
            </div>
          </div>
          <HorizontalBarChart
            items={topMovementProducts}
            valueFormatter={(v) => `${v} uds`}
            color="#2B6C6D"
          />
        </article>
      </section>

      {/* Alertas + Umbrales */}
      <section className="grid-2">
        <article className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Alertas de Stock Mínimo (RF09)</h3>
              <p className="panel-desc">Generadas automáticamente por eventos RabbitMQ</p>
            </div>
          </div>
          <div className="table-wrapper" role="region" aria-label="Alertas" tabIndex={0}>
            <table>
              <thead>
                <tr><th>Producto</th><th>Bodega</th><th>Saldo / Mín</th><th>Generada</th><th>Estado</th><th></th></tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.id_alerta}>
                    <td style={{ fontWeight: 500 }}>{productMap[a.id_producto]?.nombre || `#${a.id_producto}`}</td>
                    <td className="mono">BOD-0{a.id_bodega}</td>
                    <td className="mono">
                      <strong style={{ color: a.estado === 'ACTIVA' ? 'var(--crimson)' : 'var(--ink)' }}>{a.saldo_observado}</strong> / {a.cantidad_minima}
                    </td>
                    <td style={{ fontSize: '0.76rem', color: 'var(--ink-muted)' }}>{formatDate(a.generada_en)}</td>
                    <td>
                      <span className={`badge ${a.estado === 'ACTIVA' ? 'badge-crimson' : 'badge-sage'}`}>
                        {a.estado === 'ACTIVA' ? <AlertTriangle size={11} /> : <CheckCircle2 size={11} />}
                        {a.estado}
                      </span>
                    </td>
                    <td>
                      {a.estado === 'ACTIVA' && (
                        <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleAckAlert(a.id_alerta)}>
                          Atender
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h3 className="panel-title">Umbrales Configurados ({thresholds.length})</h3>
              <p className="panel-desc">Nivel mínimo permitido por producto y bodega</p>
            </div>
          </div>
          <div className="table-wrapper" role="region" aria-label="Umbrales" tabIndex={0}>
            <table>
              <thead>
                <tr><th>Código</th><th>Producto</th><th>Bodega</th><th>Cantidad Mínima</th></tr>
              </thead>
              <tbody>
                {thresholds.map((u) => (
                  <tr key={u.id_umbral}>
                    <td className="mono">{productMap[u.id_producto]?.codigo || `#${u.id_producto}`}</td>
                    <td>{productMap[u.id_producto]?.nombre || `Producto #${u.id_producto}`}</td>
                    <td className="mono">BOD-0{u.id_bodega}</td>
                    <td className="mono" style={{ fontWeight: 700 }}>{u.cantidad_minima} uds</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <Modal open={umbModal} onClose={() => setUmbModal(false)} title="Configurar Umbral Mínimo de Stock">
        <form onSubmit={handleSaveThreshold} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          <div className="field">
            <label>Producto</label>
            <select value={umbForm.id_producto} onChange={(e) => setUmbForm({ ...umbForm, id_producto: e.target.value })}>
              {products.map((p) => <option key={p.id_producto} value={p.id_producto}>{p.codigo} — {p.nombre}</option>)}
            </select>
          </div>
          <div className="form-grid">
            <div className="field">
              <label>Bodega</label>
              <select value={umbForm.id_bodega} onChange={(e) => setUmbForm({ ...umbForm, id_bodega: e.target.value })}>
                {warehouses.map((w) => <option key={w.id_bodega} value={w.id_bodega}>{w.codigo} — {w.nombre}</option>)}
              </select>
            </div>
            <div className="field">
              <label>Cantidad Mínima</label>
              <input type="number" min="0" value={umbForm.cantidad_minima} onChange={(e) => setUmbForm({ ...umbForm, cantidad_minima: e.target.value })} required />
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setUmbModal(false)}>Cancelar</button>
            <button type="submit" className="btn">Guardar Umbral</button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

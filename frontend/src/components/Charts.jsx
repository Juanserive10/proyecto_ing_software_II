import React, { useState } from 'react'
import { formatMoney, formatShortMoney } from '../utils/format'

const PALETTE = {
  slate: '#1E3A5F',
  teal: '#2B6C6D',
  sage: '#2E7D5B',
  ochre: '#B87A2A',
  stone: '#7C8594',
}

/**
 * Gráfico de barras verticales agrupadas (animado) para Stock por Bodega (BOD-01 vs BOD-02)
 */
export function StockWarehouseChart({ items = [] }) {
  const [tip, setTip] = useState(null)

  if (items.length === 0) {
    return <p style={{ color: 'var(--ink-muted)', fontSize: '0.85rem' }}>Sin existencias registradas para graficar.</p>
  }

  const maxVal = Math.max(10, ...items.flatMap((i) => [i.b1, i.b2]))
  const chartW = 580
  const chartH = 220
  const padL = 36
  const padB = 42
  const padT = 14
  const plotH = chartH - padB - padT
  const groupW = (chartW - padL - 16) / items.length

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((p) => Math.round(maxVal * p))

  return (
    <div className="chart-container" onMouseLeave={() => setTip(null)}>
      <svg viewBox={`0 0 ${chartW} ${chartH}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
        {ticks.map((tk, idx) => {
          const y = padT + plotH - (tk / maxVal) * plotH
          return (
            <g key={idx}>
              <line x1={padL} x2={chartW - 10} y1={y} y2={y} stroke="#EAEBE6" strokeWidth="1" />
              <text x={padL - 6} y={y + 4} textAnchor="end" fontSize="10" fill="#666D7A" fontFamily="JetBrains Mono, monospace">
                {tk}
              </text>
            </g>
          )
        })}

        {items.map((item, idx) => {
          const gx = padL + idx * groupW + groupW * 0.18
          const barW = Math.min(18, groupW * 0.28)
          const h1 = (item.b1 / maxVal) * plotH
          const h2 = (item.b2 / maxVal) * plotH
          const y1 = padT + plotH - h1
          const y2 = padT + plotH - h2

          return (
            <g key={item.codigo}>
              <rect
                className="chart-bar-anim"
                style={{ animationDelay: `${idx * 40}ms` }}
                x={gx}
                y={y1}
                width={barW}
                height={Math.max(2, h1)}
                rx="4"
                fill={PALETTE.slate}
                onMouseEnter={(e) =>
                  setTip({
                    x: ((gx + barW / 2) / chartW) * 100,
                    y: (y1 / chartH) * 100,
                    label: `${item.nombre} · BOD-01: ${item.b1} uds`,
                  })
                }
              />
              <rect
                className="chart-bar-anim"
                style={{ animationDelay: `${idx * 40 + 60}ms` }}
                x={gx + barW + 4}
                y={y2}
                width={barW}
                height={Math.max(2, h2)}
                rx="4"
                fill={PALETTE.teal}
                onMouseEnter={() =>
                  setTip({
                    x: ((gx + barW * 1.5 + 4) / chartW) * 100,
                    y: (y2 / chartH) * 100,
                    label: `${item.nombre} · BOD-02: ${item.b2} uds`,
                  })
                }
              />
              <text
                x={gx + barW + 2}
                y={chartH - 18}
                textAnchor="middle"
                fontSize="10"
                fill="#4A505C"
                fontFamily="JetBrains Mono, monospace"
              >
                {item.codigo}
              </text>
            </g>
          )
        })}
      </svg>

      {tip && (
        <div className="chart-tooltip" style={{ left: `${tip.x}%`, top: `${tip.y}%` }}>
          {tip.label}
        </div>
      )}

      <div className="chart-legend" style={{ marginTop: '0.5rem' }}>
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: PALETTE.slate }} />
          BOD-01 Principal
        </span>
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: PALETTE.teal }} />
          BOD-02 Punto Norte
        </span>
      </div>
    </div>
  )
}

/**
 * Gráfico de barras horizontales animadas para ingresos / top productos vendidos
 */
export function HorizontalBarChart({ items = [], valueFormatter = formatMoney, color = PALETTE.sage }) {
  if (items.length === 0) {
    return <p style={{ color: 'var(--ink-muted)', fontSize: '0.85rem' }}>Aún no hay datos suficientes para este gráfico.</p>
  }

  const max = Math.max(1, ...items.map((i) => i.value))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {items.map((item, idx) => {
        const pct = Math.max(4, Math.round((item.value / max) * 100))
        return (
          <div key={item.label + idx} style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', gap: '0.5rem' }}>
              <span style={{ fontWeight: 500, color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {item.label}
              </span>
              <span className="mono" style={{ fontWeight: 600, color: 'var(--ink-secondary)', flexShrink: 0 }}>
                {valueFormatter(item.value)}
                {item.sub ? ` (${item.sub})` : ''}
              </span>
            </div>
            <div className="meter-track" style={{ height: '9px' }}>
              <div
                className="meter-fill chart-hbar-anim"
                style={{
                  width: `${pct}%`,
                  background: color,
                  animationDelay: `${idx * 70}ms`,
                }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

/**
 * Gráfico Donut SVG elegante para Métodos de Pago o Distribución por Categoría
 */
export function DonutBreakdownChart({ segments = [], centerLabel = 'Total', centerValue = '0' }) {
  const [hoverIdx, setHoverIdx] = useState(null)
  const total = segments.reduce((acc, s) => acc + Number(s.value || 0), 0)

  if (total <= 0) {
    return <p style={{ color: 'var(--ink-muted)', fontSize: '0.85rem' }}>Sin ventas confirmadas para desglosar.</p>
  }

  const radius = 56
  const stroke = 18
  const circ = 2 * Math.PI * radius
  let cumulative = 0

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
      <div style={{ position: 'relative', width: '150px', height: '150px', flexShrink: 0 }}>
        <svg viewBox="0 0 150 150" style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
          <circle cx="75" cy="75" r={radius} fill="none" stroke="#EEEEEA" strokeWidth={stroke} />
          {segments.map((seg, idx) => {
            const frac = seg.value / total
            const dash = frac * circ
            const offset = -cumulative * circ
            cumulative += frac
            const active = hoverIdx === idx
            return (
              <circle
                key={seg.label}
                cx="75"
                cy="75"
                r={radius}
                fill="none"
                stroke={seg.color}
                strokeWidth={active ? stroke + 3 : stroke}
                strokeDasharray={`${dash} ${circ - dash}`}
                strokeDashoffset={offset}
                style={{ transition: 'stroke-width 150ms ease, opacity 150ms ease', opacity: hoverIdx !== null && !active ? 0.55 : 1, cursor: 'pointer' }}
                onMouseEnter={() => setHoverIdx(idx)}
                onMouseLeave={() => setHoverIdx(null)}
              />
            )
          })}
        </svg>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            pointerEvents: 'none',
          }}
        >
          <span style={{ fontSize: '0.68rem', color: 'var(--ink-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
            {hoverIdx !== null ? segments[hoverIdx].label : centerLabel}
          </span>
          <span className="mono" style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--ink)' }}>
            {hoverIdx !== null ? formatShortMoney(segments[hoverIdx].value) : centerValue}
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', flex: 1, minWidth: '160px' }}>
        {segments.map((seg, idx) => {
          const pct = Math.round((seg.value / total) * 100)
          return (
            <div
              key={seg.label}
              onMouseEnter={() => setHoverIdx(idx)}
              onMouseLeave={() => setHoverIdx(null)}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.35rem 0.5rem',
                borderRadius: '6px',
                background: hoverIdx === idx ? 'var(--surface-muted)' : 'transparent',
                fontSize: '0.82rem',
                cursor: 'default',
              }}
            >
              <span className="legend-item">
                <span className="legend-swatch" style={{ background: seg.color }} />
                {seg.label}
              </span>
              <span className="mono" style={{ fontWeight: 600 }}>
                {pct}% · {formatShortMoney(seg.value)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/**
 * Gráfico simple de línea/área de ventas recientes por fecha/número
 */
export function SalesTrendAreaChart({ sales = [] }) {
  const [hoverIdx, setHoverIdx] = useState(null)
  const confirmed = [...sales].filter((s) => s.estado === 'CONFIRMADA').reverse().slice(-10)

  if (confirmed.length === 0) {
    return <p style={{ color: 'var(--ink-muted)', fontSize: '0.85rem' }}>Registra tu primera venta para ver la tendencia.</p>
  }

  const maxVal = Math.max(10000, ...confirmed.map((s) => Number(s.total || 0)))
  const w = 520
  const h = 190
  const padL = 48
  const padR = 16
  const padT = 16
  const padB = 34
  const plotW = w - padL - padR
  const plotH = h - padT - padB

  const pts = confirmed.map((s, idx) => {
    const x = confirmed.length === 1 ? padL + plotW / 2 : padL + (idx / (confirmed.length - 1)) * plotW
    const y = padT + plotH - (Number(s.total) / maxVal) * plotH
    return { x, y, sale: s }
  })

  const polyline = pts.map((p) => `${p.x},${p.y}`).join(' ')
  const area = `${pts[0].x},${padT + plotH} ${polyline} ${pts[pts.length - 1].x},${padT + plotH}`

  return (
    <div className="chart-container" onMouseLeave={() => setHoverIdx(null)}>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
        <defs>
          <linearGradient id="salesAreaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1E3A5F" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#1E3A5F" stopOpacity="0.01" />
          </linearGradient>
        </defs>

        {[0, 0.5, 1].map((p, i) => {
          const val = maxVal * p
          const y = padT + plotH - p * plotH
          return (
            <g key={i}>
              <line x1={padL} x2={w - padR} y1={y} y2={y} stroke="#EAEBE6" strokeWidth="1" />
              <text x={padL - 6} y={y + 4} textAnchor="end" fontSize="10" fill="#666D7A" fontFamily="JetBrains Mono, monospace">
                {formatShortMoney(val)}
              </text>
            </g>
          )
        })}

        {pts.length > 1 && <polygon points={area} fill="url(#salesAreaGrad)" />}
        {pts.length > 1 && (
          <polyline fill="none" stroke={PALETTE.slate} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" points={polyline} />
        )}

        {pts.map((p, idx) => (
          <g key={p.sale.id_venta}>
            <circle
              cx={p.x}
              cy={p.y}
              r={hoverIdx === idx ? 6 : 4.2}
              fill="#FFFFFF"
              stroke={PALETTE.slate}
              strokeWidth="2.5"
              style={{ cursor: 'pointer', transition: 'r 120ms ease' }}
              onMouseEnter={() => setHoverIdx(idx)}
            />
            <text x={p.x} y={h - 10} textAnchor="middle" fontSize="9.5" fill="#666D7A" fontFamily="JetBrains Mono, monospace">
              {p.sale.numero.slice(-5)}
            </text>
          </g>
        ))}
      </svg>

      {hoverIdx !== null && pts[hoverIdx] && (
        <div
          className="chart-tooltip"
          style={{ left: `${(pts[hoverIdx].x / w) * 100}%`, top: `${(pts[hoverIdx].y / h) * 100}%` }}
        >
          {pts[hoverIdx].sale.numero} · {formatMoney(pts[hoverIdx].sale.total)} ({pts[hoverIdx].sale.metodo_pago})
        </div>
      )}
    </div>
  )
}

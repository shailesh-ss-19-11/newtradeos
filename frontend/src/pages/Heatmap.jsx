import { useEffect, useState } from 'react'
import axios from 'axios'

const api = (path) => axios.get(`/api${path}`)

function HeatCell({ cell }) {
  const { displaySymbol, pnl, trades, winRate } = cell

  const intensity = Math.min(Math.abs(pnl) / 5000, 1)   // cap at 5000 for color scale
  let bg, border, textColor

  if (trades === 0) {
    bg = 'rgba(255,255,255,0.03)'; border = 'var(--border)'; textColor = 'var(--text-3)'
  } else if (pnl > 0) {
    bg      = `rgba(0,255,136,${0.08 + intensity * 0.25})`
    border  = `rgba(0,255,136,${0.2 + intensity * 0.4})`
    textColor = '#00FF88'
  } else if (pnl < 0) {
    bg      = `rgba(255,59,107,${0.08 + intensity * 0.25})`
    border  = `rgba(255,59,107,${0.2 + intensity * 0.4})`
    textColor = '#FF3B6B'
  } else {
    bg = 'var(--surface-hi)'; border = 'var(--border)'; textColor = 'var(--text-2)'
  }

  return (
    <div style={{
      background: bg, border: `1px solid ${border}`, borderRadius: 8,
      padding: '12px 10px', textAlign: 'center', cursor: 'default',
      transition: 'all 0.15s ease', minHeight: 80,
      display: 'flex', flexDirection: 'column', justifyContent: 'center',
    }}
      title={`${displaySymbol}: ₹${pnl.toLocaleString('en-IN', { minimumFractionDigits: 2 })} | ${trades} trades | ${winRate}% win rate`}
    >
      <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>{displaySymbol}</p>
      <p style={{ fontSize: 12, fontWeight: 700, color: textColor, fontFamily: 'var(--font-mono)', marginBottom: 2 }}>
        {pnl >= 0 ? '+' : ''}{pnl.toLocaleString('en-IN', { minimumFractionDigits: 0 })}
      </p>
      {trades > 0 && (
        <p style={{ fontSize: 10, color: 'var(--text-3)' }}>{trades}T · {winRate}%</p>
      )}
    </div>
  )
}

export default function Heatmap() {
  const [cells,   setCells]   = useState([])
  const [loading, setLoading] = useState(true)
  const [days,    setDays]    = useState(30)
  const [stats,   setStats]   = useState({ totalPnl: 0, bestSym: null, worstSym: null })

  const load = (d) => {
    setLoading(true)
    api(`/heatmap?days=${d}`).then(r => {
      const data = r.data.cells || []
      setCells(data)
      const withTrades = data.filter(c => c.trades > 0)
      setStats({
        totalPnl: data.reduce((s, c) => s + c.pnl, 0),
        bestSym:  withTrades[0]?.displaySymbol || null,
        worstSym: withTrades[withTrades.length - 1]?.displaySymbol || null,
      })
    }).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load(days) }, [days])

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', margin: 0 }}>Portfolio Heat Map</h1>
          <p style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 4 }}>
            Symbol P&L performance · green = profitable · red = loss
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {[7, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className={days === d ? 'btn-primary' : 'btn-ghost'}
              style={{ padding: '7px 16px', fontSize: 12 }}>
              {d}D
            </button>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        {[
          { label: `Total P&L (${days}D)`, val: `${stats.totalPnl >= 0 ? '+' : ''}₹${stats.totalPnl.toLocaleString('en-IN', { minimumFractionDigits: 0 })}`,
            color: stats.totalPnl >= 0 ? '#00FF88' : '#FF3B6B' },
          { label: 'Best Symbol',  val: stats.bestSym  || '—', color: '#00FF88' },
          { label: 'Worst Symbol', val: stats.worstSym || '—', color: '#FF3B6B' },
          { label: 'Symbols Tracked', val: cells.length, color: 'var(--cyan)' },
        ].map(s => (
          <div key={s.label} style={{ background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '12px 20px', flex: 1 }}>
            <p style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase',
              letterSpacing: '0.08em', marginBottom: 4 }}>{s.label}</p>
            <p style={{ fontSize: 18, fontWeight: 700, color: s.color, fontFamily: 'var(--font-mono)' }}>{s.val}</p>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 16, fontSize: 11, color: 'var(--text-3)' }}>
        <span>Legend:</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: 'rgba(0,255,136,0.3)', border: '1px solid rgba(0,255,136,0.5)' }} />
          <span>Profitable (brighter = larger gain)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: 'rgba(255,59,107,0.3)', border: '1px solid rgba(255,59,107,0.5)' }} />
          <span>Loss (brighter = larger loss)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 12, borderRadius: 3, background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)' }} />
          <span>No trades</span>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
          <div className="spin" style={{ width: 28, height: 28, border: '2px solid var(--border)',
            borderTopColor: 'var(--cyan)', borderRadius: '50%' }} />
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))',
          gap: 8,
        }}>
          {cells.map(cell => <HeatCell key={cell.symbol} cell={cell} />)}
        </div>
      )}
    </div>
  )
}


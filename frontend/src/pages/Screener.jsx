import { useEffect, useState, useCallback } from 'react'
import axios from 'axios'

const api = (path) => axios.get(`/api${path}`)

function SignalBadge({ type }) {
  if (!type) return <span style={{ color: 'var(--text-3)', fontSize: 11 }}>—</span>
  const color = type === 'BUY' ? '#00FF88' : '#FF3B6B'
  const bg    = type === 'BUY' ? 'rgba(0,255,136,0.12)' : 'rgba(255,59,107,0.12)'
  return (
    <span style={{ fontSize: 11, fontWeight: 700, color, background: bg,
      padding: '2px 8px', borderRadius: 4, border: `1px solid ${color}40` }}>
      {type}
    </span>
  )
}

function PnlCell({ val }) {
  if (val == null) return <span style={{ color: 'var(--text-3)' }}>—</span>
  const color = val >= 0 ? '#00FF88' : '#FF3B6B'
  return <span style={{ color, fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
    {val >= 0 ? '+' : ''}{val.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
  </span>
}

function ChangeCell({ val }) {
  if (!val && val !== 0) return <span style={{ color: 'var(--text-3)' }}>—</span>
  const color = val >= 0 ? '#00FF88' : '#FF3B6B'
  return <span style={{ color, fontFamily: 'var(--font-mono)' }}>{val >= 0 ? '+' : ''}{val.toFixed(2)}%</span>
}

export default function Screener() {
  const [symbols, setSymbols]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [filter, setFilter]     = useState('ALL')   // ALL | ACTIVE | BUY | SELL
  const [search, setSearch]     = useState('')
  const [sortBy, setSortBy]     = useState('changePct')
  const [sortDir, setSortDir]   = useState('desc')
  const [lastUpdated, setLast]  = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    api('/screener').then(r => {
      setSymbols(r.data.symbols || [])
      setLast(new Date())
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    const t = setInterval(load, 30_000)
    return () => clearInterval(t)
  }, [load])

  const filtered = symbols
    .filter(s => {
      if (search && !s.displaySymbol.toLowerCase().includes(search.toLowerCase())) return false
      if (filter === 'ACTIVE') return s.hasActive
      if (filter === 'BUY')    return s.activeType === 'BUY'
      if (filter === 'SELL')   return s.activeType === 'SELL'
      return true
    })
    .sort((a, b) => {
      const av = a[sortBy] ?? (sortDir === 'desc' ? -Infinity : Infinity)
      const bv = b[sortBy] ?? (sortDir === 'desc' ? -Infinity : Infinity)
      return sortDir === 'desc' ? bv - av : av - bv
    })

  const toggleSort = (col) => {
    if (sortBy === col) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortBy(col); setSortDir('desc') }
  }

  const SortTh = ({ col, label }) => (
    <th onClick={() => toggleSort(col)} style={{ cursor: 'pointer', userSelect: 'none' }}>
      {label} {sortBy === col ? (sortDir === 'desc' ? '↓' : '↑') : ''}
    </th>
  )

  const activeCount = symbols.filter(s => s.hasActive).length
  const buyCount    = symbols.filter(s => s.activeType === 'BUY').length
  const sellCount   = symbols.filter(s => s.activeType === 'SELL').length

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', margin: 0 }}>Symbol Screener</h1>
          <p style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 4 }}>
            Live snapshot of all scanned symbols · auto-refreshes every 30s
            {lastUpdated && ` · Updated ${lastUpdated.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })}`}
          </p>
        </div>
        <button onClick={load} className="btn-ghost" style={{ fontSize: 12 }}>↻ Refresh</button>
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'Total Symbols', val: symbols.length, color: 'var(--cyan)' },
          { label: 'Active Signals', val: activeCount, color: '#f59e0b' },
          { label: 'BUY Signals',   val: buyCount,    color: '#00FF88' },
          { label: 'SELL Signals',  val: sellCount,   color: '#FF3B6B' },
        ].map(s => (
          <div key={s.label} style={{ background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '12px 20px', flex: 1 }}>
            <p style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase',
              letterSpacing: '0.08em', marginBottom: 4 }}>{s.label}</p>
            <p style={{ fontSize: 22, fontWeight: 700, color: s.color, fontFamily: 'var(--font-mono)' }}>{s.val}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center' }}>
        <input className="form-input" placeholder="Search symbol…" value={search}
          onChange={e => setSearch(e.target.value)} style={{ width: 200 }} />
        {['ALL', 'ACTIVE', 'BUY', 'SELL'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={filter === f ? 'btn-primary' : 'btn-ghost'}
            style={{ padding: '7px 16px', fontSize: 12 }}>
            {f}
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <SortTh col="ltp"         label="LTP" />
                <SortTh col="changePct"   label="Change %" />
                <SortTh col="volume"      label="Volume" />
                <th>Signal</th>
                <th>Confidence</th>
                <th>Votes</th>
                <th>Entry</th>
                <SortTh col="unrealizedPnl" label="Unrealized P&L" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={9} style={{ textAlign: 'center', padding: 60 }}>
                  <div className="spin" style={{ width: 20, height: 20, border: '2px solid var(--border)',
                    borderTopColor: 'var(--cyan)', borderRadius: '50%', margin: '0 auto' }} />
                </td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={9} style={{ textAlign: 'center', padding: 60, color: 'var(--text-3)' }}>
                  No symbols match your filter
                </td></tr>
              ) : filtered.map(s => (
                <tr key={s.symbol} style={{ background: s.hasActive ? 'rgba(0,212,255,0.03)' : 'transparent' }}>
                  <td>
                    <span style={{ fontWeight: 600, color: 'var(--text-1)' }}>{s.displaySymbol}</span>
                    {s.hasActive && (
                      <span style={{ marginLeft: 6, width: 6, height: 6, borderRadius: '50%',
                        background: 'var(--cyan)', display: 'inline-block',
                        boxShadow: '0 0 6px var(--cyan)' }} />
                    )}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-1)' }}>
                    {s.ltp ? `₹${s.ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '—'}
                  </td>
                  <td><ChangeCell val={s.changePct} /></td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-3)', fontSize: 11 }}>
                    {s.volume ? (s.volume / 1000).toFixed(0) + 'K' : '—'}
                  </td>
                  <td><SignalBadge type={s.activeType} /></td>
                  <td style={{ fontSize: 12, color: s.confidence === 'HIGH' ? '#f59e0b' : s.confidence === 'MEDIUM' ? 'var(--cyan)' : 'var(--text-3)' }}>
                    {s.confidence || '—'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-2)', fontSize: 12 }}>
                    {s.votes || '—'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-2)', fontSize: 12 }}>
                    {s.entryPrice ? `₹${s.entryPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : '—'}
                  </td>
                  <td><PnlCell val={s.unrealizedPnl} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}


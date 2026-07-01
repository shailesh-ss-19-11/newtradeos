import { useState, useEffect } from 'react'
import { getBacktestHistory, getBacktestResults, exportBacktestCsv } from '../api'

const STATUS_COLOR = { completed: 'var(--emerald)', failed: 'var(--rose)', running: 'var(--amber)' }

export default function BacktestHistory() {
  const [history,  setHistory]  = useState([])
  const [loading,  setLoading]  = useState(true)
  const [selected, setSelected] = useState(null)   // { id, results }
  const [loadingResult, setLoadingResult] = useState(false)
  const [compareIds, setCompareIds] = useState([])
  const [compareData, setCompareData] = useState([])
  const [tab, setTab] = useState('history')         // 'history' | 'compare'

  useEffect(() => {
    getBacktestHistory()
      .then(r => setHistory(r.data.history || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const viewResult = async (id) => {
    setLoadingResult(true)
    try {
      const r = await getBacktestResults(id)
      setSelected({ id, ...r.data })
    } catch {}
    setLoadingResult(false)
  }

  const toggleCompare = (id) => {
    setCompareIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 3 ? [...prev, id] : prev
    )
  }

  const runCompare = async () => {
    setTab('compare')
    const results = await Promise.all(compareIds.map(id => getBacktestResults(id).then(r => ({ id, ...r.data }))))
    setCompareData(results.filter(r => r.status === 'completed'))
  }

  const METRICS = [
    { key: 'totalPnL',       label: 'Total P&L (₹)',     fmt: v => `₹${v?.toLocaleString('en-IN') ?? '—'}` },
    { key: 'totalReturn',    label: 'Return (%)',          fmt: v => v != null ? `${v.toFixed(2)}%` : '—' },
    { key: 'winRate',        label: 'Win Rate (%)',        fmt: v => v != null ? `${v.toFixed(1)}%` : '—' },
    { key: 'totalTrades',    label: 'Total Trades',        fmt: v => v ?? '—' },
    { key: 'sharpeRatio',    label: 'Sharpe Ratio',        fmt: v => v?.toFixed(3) ?? '—' },
    { key: 'maxDrawdown',    label: 'Max Drawdown (%)',    fmt: v => v != null ? `${v.toFixed(2)}%` : '—' },
    { key: 'profitFactor',   label: 'Profit Factor',       fmt: v => v?.toFixed(3) ?? '—' },
    { key: 'avgHoldingDays', label: 'Avg Holding Days',   fmt: v => v?.toFixed(1) ?? '—' },
  ]

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>Backtest History</h1>
          <p style={{ fontSize: 13, color: 'var(--text-2)' }}>Review past runs and compare strategies side by side</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setTab('history')} style={{ ...tabBtn, ...(tab === 'history' ? tabActive : {}) }}>History</button>
          <button onClick={() => setTab('compare')} style={{ ...tabBtn, ...(tab === 'compare' ? tabActive : {}) }}>Compare</button>
        </div>
      </div>

      {tab === 'history' && (
        <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 1.4fr' : '1fr', gap: 20 }}>
          {/* History list */}
          <div>
            {compareIds.length > 0 && (
              <div style={{ padding: '10px 14px', background: 'var(--cyan-15)', border: '1px solid var(--cyan-25)', borderRadius: 8, marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13, color: 'var(--cyan)' }}>{compareIds.length} selected for comparison</span>
                <button onClick={runCompare} style={{ padding: '5px 14px', borderRadius: 6, background: 'var(--cyan)', border: 'none', color: '#fff', fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                  Compare →
                </button>
              </div>
            )}

            {loading ? (
              <p style={{ color: 'var(--text-2)', fontSize: 13, padding: 20 }}>Loading...</p>
            ) : history.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-3)', fontSize: 13 }}>No backtest runs yet</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {history.map(h => (
                  <div key={h.id} style={{
                    background: 'var(--surface)', border: `1px solid ${selected?.id === h.id ? 'var(--cyan)' : 'var(--border)'}`,
                    borderRadius: 10, padding: '14px 16px',
                    display: 'flex', alignItems: 'center', gap: 12,
                  }}>
                    <input type="checkbox" checked={compareIds.includes(h.id)}
                      onChange={() => toggleCompare(h.id)}
                      style={{ flexShrink: 0, accentColor: 'var(--cyan)' }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-1)' }}>
                          {h.strategyName || 'Unknown Strategy'}
                        </span>
                        <span style={{ fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 10,
                          background: STATUS_COLOR[h.status] + '20', color: STATUS_COLOR[h.status] }}>
                          {h.status}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-3)' }}>
                        {h.config?.universe} · {h.config?.period} · {new Date(h.createdAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {h.status === 'completed' && (
                        <>
                          <button onClick={() => exportBacktestCsv(h.id)}
                            style={iconBtn} title="Export CSV">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                          </button>
                          <button onClick={() => viewResult(h.id)} style={{ ...iconBtn, color: 'var(--cyan)' }} title="View results">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Result detail panel */}
          {selected && (
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 20, maxHeight: '80vh', overflowY: 'auto' }}>
              {loadingResult ? (
                <p style={{ color: 'var(--text-2)', fontSize: 13 }}>Loading results...</p>
              ) : (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-1)' }}>
                      {selected.strategyName} · Run #{selected.id}
                    </h3>
                    <button onClick={() => setSelected(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)' }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    {METRICS.map(m => {
                      const val = selected.results?.summary?.[m.key]
                      return (
                        <div key={m.key} style={{ background: 'var(--surface-hi)', borderRadius: 8, padding: '10px 12px' }}>
                          <p style={{ fontSize: 10, color: 'var(--text-3)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{m.label}</p>
                          <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-1)' }}>{m.fmt(val)}</p>
                        </div>
                      )
                    })}
                  </div>
                  <button onClick={() => exportBacktestCsv(selected.id)} style={{ marginTop: 16, width: '100%', padding: '9px', borderRadius: 8, background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-2)', fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                    Download Trades CSV
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'compare' && (
        <div>
          {compareData.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 60 }}>
              <p style={{ color: 'var(--text-3)', fontSize: 13 }}>Select 2–3 runs in History and click Compare</p>
              <button onClick={() => setTab('history')} style={{ marginTop: 16, padding: '8px 20px', borderRadius: 8, background: 'var(--cyan)', border: 'none', color: '#fff', fontSize: 13, cursor: 'pointer' }}>← Back to History</button>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--surface)' }}>
                    <th style={{ ...th, textAlign: 'left' }}>Metric</th>
                    {compareData.map(d => (
                      <th key={d.id} style={{ ...th, color: 'var(--cyan)' }}>
                        {d.strategyName}<br/>
                        <span style={{ fontSize: 10, color: 'var(--text-3)', fontWeight: 400 }}>Run #{d.id}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {METRICS.map(m => (
                    <tr key={m.key} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ ...td, color: 'var(--text-2)', fontWeight: 500 }}>{m.label}</td>
                      {compareData.map(d => {
                        const val = d.results?.summary?.[m.key]
                        const vals = compareData.map(x => x.results?.summary?.[m.key]).filter(v => v != null)
                        const isBest = val != null && vals.length > 1 && val === Math.max(...vals)
                        return (
                          <td key={d.id} style={{ ...td, color: isBest ? 'var(--emerald)' : 'var(--text-1)', fontWeight: isBest ? 700 : 400 }}>
                            {m.fmt(val)}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const tabBtn   = { padding: '7px 16px', borderRadius: 8, cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--surface-hi)', color: 'var(--text-2)', fontSize: 13, fontWeight: 500 }
const tabActive= { background: 'var(--cyan-15)', border: '1px solid var(--cyan)', color: 'var(--cyan)', fontWeight: 700 }
const iconBtn  = { background: 'var(--surface-hi)', border: '1px solid var(--border)', borderRadius: 6, padding: '5px 7px', cursor: 'pointer', color: 'var(--text-2)' }
const th = { padding: '10px 14px', borderBottom: '2px solid var(--border)', fontWeight: 700, color: 'var(--text-1)', fontSize: 12 }
const td = { padding: '10px 14px', borderBottom: '1px solid var(--border)' }

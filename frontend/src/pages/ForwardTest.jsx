import { useState, useEffect, useRef } from 'react'
import { getStrategies, runForwardTest, getForwardStatus } from '../api'

const UNIVERSES = [
  { value: 'NIFTY50',   label: 'Nifty 50',   count: 50  },
  { value: 'NIFTY100',  label: 'Nifty 100',  count: 100 },
  { value: 'NIFTY200',  label: 'Nifty 200',  count: 200 },
  { value: 'NIFTY500',  label: 'Nifty 500',  count: 500 },
]

export default function ForwardTest() {
  const [strategies, setStrategies] = useState([])
  const [strategyId, setStrategyId] = useState('')
  const [universe,   setUniverse]   = useState('NIFTY50')
  const [running,    setRunning]    = useState(false)
  const [progress,   setProgress]   = useState(null)   // { scanned, total }
  const [results,    setResults]    = useState(null)   // { signals, scanned }
  const [error,      setError]      = useState('')
  const [filter,     setFilter]     = useState('ALL')  // ALL | BUY | SELL
  const pollRef = useRef(null)

  useEffect(() => {
    getStrategies().then(r => setStrategies(r.data.strategies || [])).catch(() => {})
    return () => clearInterval(pollRef.current)
  }, [])

  const handleRun = async () => {
    setError('')
    if (!strategyId) return setError('Select a strategy first')
    setRunning(true)
    setResults(null)
    setProgress(null)
    const universe_def = UNIVERSES.find(u => u.value === universe)
    setProgress({ scanned: 0, total: universe_def?.count || 50 })
    try {
      const r   = await runForwardTest({ strategyId: Number(strategyId), universe })
      const rid = r.data.runId
      clearInterval(pollRef.current)
      pollRef.current = setInterval(async () => {
        const s = await getForwardStatus(rid)
        if (s.data.status === 'completed') {
          clearInterval(pollRef.current)
          setResults({ signals: s.data.signals || [], scanned: s.data.scanned || 0 })
          setRunning(false)
          setProgress(null)
        } else if (s.data.status === 'failed') {
          clearInterval(pollRef.current)
          setError(s.data.error || 'Forward test failed')
          setRunning(false)
          setProgress(null)
        }
      }, 2000)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to start forward test')
      setRunning(false)
      setProgress(null)
    }
  }

  const signals     = results?.signals || []
  const filtered    = filter === 'ALL' ? signals : signals.filter(s => s.signal === filter)
  const buyCount    = signals.filter(s => s.signal === 'BUY').length
  const sellCount   = signals.filter(s => s.signal === 'SELL').length
  const selectedStrat = strategies.find(s => s.id === Number(strategyId))

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>Forward Test / Shadow Mode</h1>
        <p style={{ fontSize: 13, color: 'var(--text-2)' }}>Scan the market right now — see which stocks your strategy would signal today</p>
      </div>

      {/* Config panel */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 20, marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 14, alignItems: 'flex-end' }}>
          <div>
            <label style={lbl}>Strategy</label>
            <select value={strategyId} onChange={e => setStrategyId(e.target.value)} style={inp}>
              <option value="">Select strategy...</option>
              {strategies.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div>
            <label style={lbl}>Universe</label>
            <div style={{ display: 'flex', gap: 6 }}>
              {UNIVERSES.map(u => (
                <button key={u.value} onClick={() => setUniverse(u.value)} style={{
                  flex: 1, padding: '9px 0', borderRadius: 8, cursor: 'pointer', fontSize: 12,
                  border: universe === u.value ? '1px solid var(--cyan)' : '1px solid var(--border)',
                  background: universe === u.value ? 'var(--cyan-15)' : 'var(--surface-hi)',
                  color: universe === u.value ? 'var(--cyan)' : 'var(--text-2)',
                  fontWeight: universe === u.value ? 700 : 400,
                }}>
                  {u.label}
                </button>
              ))}
            </div>
          </div>
          <button onClick={handleRun} disabled={running} style={{
            padding: '10px 24px', borderRadius: 8, border: 'none', cursor: 'pointer',
            background: running ? 'var(--surface-hi)' : 'var(--cyan)',
            color: running ? 'var(--text-3)' : '#fff', fontSize: 13, fontWeight: 700,
            display: 'flex', alignItems: 'center', gap: 8, minWidth: 140, justifyContent: 'center',
            opacity: running ? 0.9 : 1,
          }}>
            {running ? (
              <>
                <div style={{ width: 12, height: 12, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', animation: 'spin 0.8s linear infinite' }} />
                Scanning...
              </>
            ) : '▶ Run Scan'}
          </button>
        </div>
        {error && <div style={{ marginTop: 12, padding: '8px 12px', background: 'var(--rose-15)', border: '1px solid var(--rose)', borderRadius: 8, color: 'var(--rose)', fontSize: 13 }}>{error}</div>}
      </div>

      {/* Progress */}
      {running && progress && (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 20, marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: 'var(--text-1)', fontWeight: 600 }}>
              Scanning {UNIVERSES.find(u => u.value === universe)?.label} universe…
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-3)' }}>
              {selectedStrat?.name} · {selectedStrat?.strategyType}
            </span>
          </div>
          <div style={{ background: 'var(--surface-hi)', borderRadius: 4, height: 4, overflow: 'hidden' }}>
            <div style={{ height: '100%', background: 'var(--cyan)', borderRadius: 4, animation: 'progress-fill 3s ease-in-out infinite' }} />
          </div>
          <p style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 6 }}>
            This may take 30–120 seconds depending on universe size
          </p>
        </div>
      )}

      {/* Results */}
      {results && (
        <>
          {/* Summary row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
            {[
              { label: 'Stocks Scanned',  value: results.scanned,  color: null },
              { label: 'Total Signals',   value: signals.length,   color: signals.length > 0 ? 'var(--cyan)' : null },
              { label: 'BUY Signals',     value: buyCount,         color: buyCount  > 0 ? 'var(--emerald)' : null },
              { label: 'SELL Signals',    value: sellCount,        color: sellCount > 0 ? 'var(--rose)'    : null },
            ].map(s => (
              <div key={s.label} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 16px' }}>
                <p style={{ fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{s.label}</p>
                <p style={{ fontSize: 22, fontWeight: 700, color: s.color || 'var(--text-1)' }}>{s.value}</p>
              </div>
            ))}
          </div>

          {signals.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 60, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12 }}>
              <p style={{ fontSize: 32, marginBottom: 12 }}>—</p>
              <p style={{ fontSize: 15, color: 'var(--text-2)', marginBottom: 6 }}>No signals found</p>
              <p style={{ fontSize: 13, color: 'var(--text-3)' }}>
                {selectedStrat?.name} found no tradeable setups in {UNIVERSES.find(u => u.value === universe)?.label} today
              </p>
            </div>
          ) : (
            <>
              <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
                {[['ALL', `All (${signals.length})`], ['BUY', `Buy (${buyCount})`], ['SELL', `Sell (${sellCount})`]].map(([v, l]) => (
                  <button key={v} onClick={() => setFilter(v)} style={{
                    padding: '6px 14px', borderRadius: 7, cursor: 'pointer', fontSize: 12,
                    border: filter === v ? '1px solid var(--cyan)' : '1px solid var(--border)',
                    background: filter === v ? 'var(--cyan-15)' : 'var(--surface-hi)',
                    color: filter === v ? 'var(--cyan)' : 'var(--text-2)',
                    fontWeight: filter === v ? 700 : 400,
                  }}>{l}</button>
                ))}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
                {filtered.map((s, i) => (
                  <div key={i} style={{
                    background: 'var(--surface)',
                    border: `1px solid ${s.signal === 'BUY' ? 'var(--emerald)' : 'var(--rose)'}`,
                    borderRadius: 10, padding: '14px 16px',
                    boxShadow: `0 0 12px ${s.signal === 'BUY' ? 'rgba(0,255,136,0.08)' : 'rgba(255,59,107,0.08)'}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)' }}>{s.symbol.split(':').pop()?.replace('-EQ','')}</span>
                      <span style={{
                        fontSize: 11, fontWeight: 700, padding: '3px 9px', borderRadius: 10,
                        background: s.signal === 'BUY' ? 'var(--emerald-15)' : 'var(--rose-15)',
                        color: s.signal === 'BUY' ? 'var(--emerald)' : 'var(--rose)',
                        border: `1px solid ${s.signal === 'BUY' ? 'var(--emerald)' : 'var(--rose)'}`,
                      }}>
                        {s.signal}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <div>
                        <p style={{ fontSize: 10, color: 'var(--text-3)', marginBottom: 2 }}>LAST CLOSE</p>
                        <p style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-1)' }}>
                          ₹{Number(s.lastClose).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                        </p>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <p style={{ fontSize: 10, color: 'var(--text-3)', marginBottom: 2 }}>DATE</p>
                        <p style={{ fontSize: 11, color: 'var(--text-2)' }}>{s.signalDate}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}

      {/* Empty state before first run */}
      {!running && !results && (
        <div style={{ textAlign: 'center', padding: 80, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12 }}>
          <p style={{ fontSize: 40, marginBottom: 16 }}>📡</p>
          <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-1)', marginBottom: 8 }}>Shadow Mode</p>
          <p style={{ fontSize: 13, color: 'var(--text-2)', maxWidth: 380, margin: '0 auto', lineHeight: 1.6 }}>
            Select a strategy and universe, then run a scan to see which stocks would generate a signal right now — with no orders placed.
          </p>
        </div>
      )}
    </div>
  )
}

const lbl = { display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-2)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.06em' }
const inp = { width: '100%', padding: '9px 12px', borderRadius: 8, background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-1)', fontSize: 13, outline: 'none', boxSizing: 'border-box' }

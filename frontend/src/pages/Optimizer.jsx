import { useState, useEffect, useRef } from 'react'
import { getStrategies, getStrategyTypes, runOptimizer, getOptimizerStatus, getOptimizerResults, getOptimizerHistory } from '../api'

const UNIVERSES = [
  { value: 'NSE:NIFTY50-INDEX', label: 'Nifty 50 Index' },
  { value: 'NSE:RELIANCE-EQ',   label: 'Reliance' },
  { value: 'NSE:HDFCBANK-EQ',   label: 'HDFC Bank' },
  { value: 'NSE:TCS-EQ',        label: 'TCS' },
  { value: 'NSE:INFY-EQ',       label: 'Infosys' },
]

const PERIODS = ['6M','1Y','2Y','3Y']

function RangeConfig({ paramKey, label, defaultMin, defaultMax, defaultStep, value, onChange }) {
  return (
    <div style={{ background: 'var(--surface-hi)', borderRadius: 8, padding: '10px 12px', marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-2)' }}>{label}</span>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--cyan)', cursor: 'pointer' }}>
          <input type="checkbox" checked={value.enabled} onChange={e => onChange({ ...value, enabled: e.target.checked })} style={{ accentColor: 'var(--cyan)' }} />
          Optimize
        </label>
      </div>
      {value.enabled && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
          {[['min', 'Min', defaultMin], ['max', 'Max', defaultMax], ['step', 'Step', defaultStep]].map(([k, l, def]) => (
            <div key={k}>
              <label style={{ fontSize: 10, color: 'var(--text-3)', display: 'block', marginBottom: 3 }}>{l}</label>
              <input type="number" value={value[k] ?? def}
                onChange={e => onChange({ ...value, [k]: Number(e.target.value) })}
                style={{ width: '100%', padding: '5px 8px', borderRadius: 6, background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-1)', fontSize: 12, outline: 'none', boxSizing: 'border-box' }} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Optimizer() {
  const [strategies,  setStrategies]  = useState([])
  const [stratTypes,  setStratTypes]  = useState([])
  const [strategyId,  setStrategyId]  = useState('')
  const [symbol,      setSymbol]      = useState('NSE:NIFTY50-INDEX')
  const [period,      setPeriod]      = useState('1Y')
  const [paramRanges, setParamRanges] = useState({})
  const [running,     setRunning]     = useState(false)
  const [runId,       setRunId]       = useState(null)
  const [results,     setResults]     = useState(null)
  const [history,     setHistory]     = useState([])
  const [error,       setError]       = useState('')
  const [tab,         setTab]         = useState('config')
  const pollRef = useRef(null)

  useEffect(() => {
    Promise.all([getStrategies(), getStrategyTypes(), getOptimizerHistory()])
      .then(([sr, tr, hr]) => {
        setStrategies(sr.data.strategies || [])
        setStratTypes(tr.data.types || [])
        setHistory(hr.data.runs || [])
      })
      .catch(() => {})
  }, [])

  const selectedStrat = strategies.find(s => s.id === Number(strategyId))
  const typeDef       = stratTypes.find(t => t.type === selectedStrat?.strategyType)

  const handleStrategyChange = (id) => {
    setStrategyId(id)
    setParamRanges({})
    setResults(null)
  }

  const updateRange = (key, val) => setParamRanges(p => ({ ...p, [key]: val }))

  const buildParamGrid = () => {
    const grid = {}
    typeDef?.params.forEach(p => {
      const r = paramRanges[p.key]
      if (r?.enabled && r.min != null && r.max != null && r.step > 0) {
        const vals = []
        for (let v = r.min; v <= r.max; v += r.step) vals.push(Number(v.toFixed(4)))
        if (vals.length > 0) grid[p.key] = vals
      }
    })
    return grid
  }

  const handleRun = async () => {
    setError('')
    if (!strategyId) return setError('Select a strategy')
    const paramGrid = buildParamGrid()
    if (Object.keys(paramGrid).length === 0) return setError('Enable and configure at least one parameter range')

    const combos = Object.values(paramGrid).reduce((a, b) => a * b.length, 1)
    if (combos > 500) return setError(`Too many combinations (${combos}). Reduce ranges or increase step size.`)

    setRunning(true)
    setResults(null)
    try {
      const r = await runOptimizer({ strategyId: Number(strategyId), config: { symbol, period, paramGrid } })
      const rid = r.data.runId
      setRunId(rid)
      clearInterval(pollRef.current)
      pollRef.current = setInterval(async () => {
        const s = await getOptimizerStatus(rid)
        if (s.data.status === 'completed') {
          clearInterval(pollRef.current)
          const res = await getOptimizerResults(rid)
          setResults(res.data)
          setRunning(false)
          setTab('results')
        } else if (s.data.status === 'failed') {
          clearInterval(pollRef.current)
          setError(s.data.error || 'Optimization failed')
          setRunning(false)
        }
      }, 3000)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to start optimizer')
      setRunning(false)
    }
  }

  useEffect(() => () => clearInterval(pollRef.current), [])

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>Strategy Optimizer</h1>
        <p style={{ fontSize: 13, color: 'var(--text-2)' }}>Grid-search parameter combinations to find the highest-performing settings</p>
      </div>

      <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
        {[['config','Configure'], ['results','Results'], ['history','History']].map(([k,l]) => (
          <button key={k} onClick={() => setTab(k)} style={{ ...tabBtn, ...(tab === k ? tabActive : {}) }}>{l}</button>
        ))}
      </div>

      {tab === 'config' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 20 }}>
          <div style={card}>
            <h3 style={sectionTitle}>1 · Strategy & Symbol</h3>
            <label style={lbl}>Strategy</label>
            <select value={strategyId} onChange={e => handleStrategyChange(e.target.value)} style={inp}>
              <option value="">Select strategy...</option>
              {strategies.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <label style={lbl}>Test Symbol</label>
            <select value={symbol} onChange={e => setSymbol(e.target.value)} style={inp}>
              {UNIVERSES.map(u => <option key={u.value} value={u.value}>{u.label}</option>)}
            </select>
            <label style={lbl}>Period</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {PERIODS.map(p => (
                <button key={p} onClick={() => setPeriod(p)} style={{ flex: 1, padding: '7px 0', borderRadius: 7, cursor: 'pointer',
                  border: period === p ? '1px solid var(--cyan)' : '1px solid var(--border)',
                  background: period === p ? 'var(--cyan-15)' : 'var(--surface-hi)',
                  color: period === p ? 'var(--cyan)' : 'var(--text-2)', fontSize: 12, fontWeight: period === p ? 700 : 400 }}>
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div style={card}>
            <h3 style={sectionTitle}>2 · Parameter Ranges</h3>
            {!typeDef ? (
              <p style={{ color: 'var(--text-3)', fontSize: 13 }}>Select a strategy to configure parameter ranges</p>
            ) : (
              <>
                {typeDef.params.map(p => (
                  <RangeConfig key={p.key}
                    paramKey={p.key} label={p.label}
                    defaultMin={p.min} defaultMax={p.max}
                    defaultStep={p.default < 10 ? 1 : 5}
                    value={paramRanges[p.key] || { enabled: false, min: p.min, max: p.max, step: p.default < 10 ? 1 : 5 }}
                    onChange={v => updateRange(p.key, v)} />
                ))}
                {error && <div style={errBox}>{error}</div>}
                <button onClick={handleRun} disabled={running} style={{ ...runBtn, opacity: running ? 0.7 : 1 }}>
                  {running ? (
                    <><div style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', animation: 'spin 0.8s linear infinite' }} />
                    Running…</>
                  ) : '▶ Run Optimizer'}
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {tab === 'results' && (
        <div>
          {!results ? (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-3)' }}>
              {running ? 'Optimization in progress...' : 'No results yet — run the optimizer first'}
            </div>
          ) : (
            <>
              <div style={{ marginBottom: 16 }}>
                <span style={{ fontSize: 13, color: 'var(--text-2)' }}>
                  {results.totalCombos} combinations tested — showing top {(results.results || []).length} by score
                </span>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: 'var(--surface)' }}>
                      <th style={th}>#</th>
                      <th style={th}>Parameters</th>
                      <th style={th}>Trades</th>
                      <th style={th}>Win Rate</th>
                      <th style={th}>Avg Return %</th>
                      <th style={th}>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(results.results || []).slice(0, 20).map((r, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid var(--border)', background: i === 0 ? 'var(--emerald-15)' : 'transparent' }}>
                        <td style={td}><span style={{ fontWeight: 700, color: i === 0 ? 'var(--emerald)' : 'var(--text-3)' }}>#{i+1}</span></td>
                        <td style={td}>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                            {Object.entries(r.params).filter(([k]) => typeDef?.params.find(p => p.key === k && paramRanges[k]?.enabled)).map(([k, v]) => (
                              <span key={k} style={{ fontSize: 11, padding: '2px 7px', background: 'var(--surface-hi)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-2)' }}>
                                {k}: {v}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td style={td}>{r.totalTrades}</td>
                        <td style={{ ...td, color: r.winRate >= 50 ? 'var(--emerald)' : 'var(--rose)', fontWeight: 600 }}>{r.winRate}%</td>
                        <td style={{ ...td, color: r.avgReturn >= 0 ? 'var(--emerald)' : 'var(--rose)', fontWeight: 600 }}>{r.avgReturn >= 0 ? '+' : ''}{r.avgReturn}%</td>
                        <td style={{ ...td, fontWeight: 700 }}>{r.score.toFixed(3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {tab === 'history' && (
        <div>
          {history.length === 0 ? (
            <p style={{ color: 'var(--text-3)', fontSize: 13, padding: 20 }}>No optimizer runs yet</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {history.map(h => (
                <div key={h.id} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px', display: 'flex', justifyContent: 'space-between' }}>
                  <div>
                    <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-1)' }}>{h.strategyName}</span>
                    <span style={{ marginLeft: 10, fontSize: 11, color: 'var(--text-3)' }}>
                      {new Date(h.createdAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })}
                    </span>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
                    background: h.status === 'completed' ? 'var(--emerald-15)' : 'var(--rose-15)',
                    color: h.status === 'completed' ? 'var(--emerald)' : 'var(--rose)' }}>
                    {h.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const card        = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 20 }
const sectionTitle= { fontSize: 13, fontWeight: 700, color: 'var(--text-1)', marginBottom: 16 }
const lbl         = { display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-2)', marginBottom: 5, marginTop: 12, textTransform: 'uppercase', letterSpacing: '0.06em' }
const inp         = { width: '100%', padding: '9px 12px', borderRadius: 8, background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-1)', fontSize: 13, outline: 'none', boxSizing: 'border-box', marginBottom: 4 }
const runBtn      = { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 16, width: '100%', padding: '11px', borderRadius: 8, background: 'var(--cyan)', border: 'none', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer' }
const tabBtn      = { padding: '7px 16px', borderRadius: 8, cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--surface-hi)', color: 'var(--text-2)', fontSize: 13, fontWeight: 500 }
const tabActive   = { background: 'var(--cyan-15)', border: '1px solid var(--cyan)', color: 'var(--cyan)', fontWeight: 700 }
const errBox      = { marginTop: 12, padding: '8px 12px', background: 'var(--rose-15)', border: '1px solid var(--rose)', borderRadius: 8, color: 'var(--rose)', fontSize: 13 }
const th          = { padding: '10px 14px', borderBottom: '2px solid var(--border)', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase' }
const td          = { padding: '10px 14px', borderBottom: '1px solid var(--border)', color: 'var(--text-2)' }

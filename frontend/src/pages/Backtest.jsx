import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  getStrategies, searchStocks, runBacktest,
  getBacktestStatus, getBacktestResults,
} from '../api'

const UNIVERSES = [
  { value: 'NIFTY50',  label: 'Nifty 50',  count: 50  },
  { value: 'NIFTY100', label: 'Nifty 100', count: 100 },
  { value: 'NIFTY150', label: 'Nifty 150', count: 150 },
  { value: 'NIFTY200', label: 'Nifty 200', count: 200 },
  { value: 'NIFTY500', label: 'Nifty 500', count: 500 },
  { value: 'INDIVIDUAL', label: 'Individual Stock', count: null },
]

const PERIODS = [
  { value: '6M',  label: '6 Months' },
  { value: '1Y',  label: '1 Year'   },
  { value: '2Y',  label: '2 Years'  },
  { value: '3Y',  label: '3 Years'  },
  { value: 'CUSTOM', label: 'Custom' },
]

const DEFAULT_CONFIG = {
  universe:              'NIFTY50',
  symbol:                '',
  period:                '1Y',
  from_date:             '',
  to_date:               '',
  initial_capital:       100000,
  max_capital_per_trade_pct: 20,
  max_open_positions:    5,
  sl_pct:                2,
  t1_pct:                3,
  t1_qty_pct:            30,
  t1_enabled:            true,
  t2_pct:                5,
  t2_qty_pct:            30,
  t2_enabled:            true,
  t3_pct:                7,
  t3_qty_pct:            40,
  t3_enabled:            true,
  trailing_sl:           false,
  breakeven_after_t1:    false,
}

export default function Backtest() {
  const [searchParams] = useSearchParams()
  const [config,       setConfig]       = useState(DEFAULT_CONFIG)
  const [strategyId,   setStrategyId]   = useState(() => searchParams.get('strategy') || '')
  const [strategies,   setStrategies]   = useState([])
  const [stockQuery,   setStockQuery]   = useState('')
  const [stockResults, setStockResults] = useState([])
  const [selectedStock, setSelectedStock] = useState(null)
  const [showStockDD,  setShowStockDD]  = useState(false)

  const [running,    setRunning]    = useState(false)
  const [runId,      setRunId]      = useState(null)
  const [results,    setResults]    = useState(null)
  const [runStatus,  setRunStatus]  = useState('')
  const [errors,     setErrors]     = useState([])
  const [activeTab,  setActiveTab]  = useState('summary')

  const pollRef   = useRef(null)
  const stockRef  = useRef(null)

  useEffect(() => {
    getStrategies()
      .then(r => setStrategies(r.data.strategies || []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!stockQuery.trim()) { setStockResults([]); return }
    const t = setTimeout(async () => {
      try {
        const r = await searchStocks(stockQuery)
        setStockResults(r.data.results || [])
        setShowStockDD(true)
      } catch { setStockResults([]) }
    }, 250)
    return () => clearTimeout(t)
  }, [stockQuery])

  useEffect(() => {
    const handler = e => {
      if (stockRef.current && !stockRef.current.contains(e.target)) setShowStockDD(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const pollStatus = useCallback(async (id) => {
    try {
      const r = await getBacktestStatus(id)
      if (r.data.status === 'completed') {
        clearInterval(pollRef.current)
        const res = await getBacktestResults(id)
        setResults(res.data)
        setRunning(false)
        setRunStatus('completed')
      } else if (r.data.status === 'failed') {
        clearInterval(pollRef.current)
        setRunning(false)
        setRunStatus('failed')
        setErrors([r.data.error || 'Backtest failed'])
      }
    } catch {
      clearInterval(pollRef.current)
      setRunning(false)
      setRunStatus('failed')
    }
  }, [])

  const handleRun = async () => {
    setErrors([])
    setResults(null)

    const cfg = { ...config }
    if (config.universe === 'INDIVIDUAL') {
      if (!selectedStock) { setErrors(['Please select a stock']); return }
      cfg.symbol = selectedStock.symbol
    }

    if (!strategyId) { setErrors(['Please select a strategy']); return }

    const totalQty = (cfg.t1_enabled ? cfg.t1_qty_pct : 0) + (cfg.t2_enabled ? cfg.t2_qty_pct : 0) + (cfg.t3_enabled ? cfg.t3_qty_pct : 0)
    if (cfg.t1_enabled && cfg.t2_enabled && cfg.t3_enabled && Math.abs(totalQty - 100) > 1) {
      setErrors([`T1 + T2 + T3 quantity must total 100% (currently ${totalQty}%)`])
      return
    }
    if (cfg.period === 'CUSTOM' && cfg.from_date >= cfg.to_date) {
      setErrors(['From date must be earlier than To date'])
      return
    }

    setRunning(true)
    setRunStatus('running')
    try {
      const r = await runBacktest(strategyId, cfg)
      const id = r.data.runId
      setRunId(id)
      clearInterval(pollRef.current)
      pollRef.current = setInterval(() => pollStatus(id), 3000)
    } catch (err) {
      setRunning(false)
      setRunStatus('')
      setErrors([err?.response?.data?.error || 'Failed to start backtest'])
    }
  }

  useEffect(() => () => clearInterval(pollRef.current), [])

  const set = (key, val) => setConfig(c => ({ ...c, [key]: val }))

  const totalQtyCfg = (config.t1_enabled ? config.t1_qty_pct : 0) +
                      (config.t2_enabled ? config.t2_qty_pct : 0) +
                      (config.t3_enabled ? config.t3_qty_pct : 0)
  const qtyOk = !config.t1_enabled || !config.t2_enabled || !config.t3_enabled || Math.abs(totalQtyCfg - 100) <= 1

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>Backtest</h1>
        <p style={{ fontSize: 13, color: 'var(--text-2)' }}>Configure and run historical simulations on your strategies</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* ── Step 1: Universe ── */}
        <Section title="1 · Universe Selection" icon="🌐">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 14 }}>
            {UNIVERSES.map(u => (
              <UnivBtn key={u.value} active={config.universe === u.value && u.value !== 'INDIVIDUAL'}
                       onClick={() => { set('universe', u.value); setSelectedStock(null); setStockQuery('') }}>
                <span style={{ fontWeight: 700, fontSize: 13 }}>{u.label}</span>
                {u.count && <span style={{ fontSize: 10, opacity: 0.7, display: 'block' }}>{u.count} stocks</span>}
              </UnivBtn>
            ))}
          </div>
          {/* Individual stock search */}
          <div ref={stockRef} style={{ position: 'relative' }}>
            <div
              style={{ ...inputStyle, display: 'flex', alignItems: 'center', gap: 8, cursor: 'text',
                border: config.universe === 'INDIVIDUAL' ? '1px solid var(--cyan)' : '1px solid var(--border)' }}
              onClick={() => { set('universe', 'INDIVIDUAL'); setShowStockDD(true) }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--text-3)" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input value={stockQuery}
                onChange={e => { setStockQuery(e.target.value); set('universe', 'INDIVIDUAL') }}
                placeholder="Search individual stock..."
                style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--text)', fontSize: 13 }} />
              {selectedStock && (
                <span style={{ fontSize: 11, color: 'var(--cyan)', fontWeight: 700, background: 'rgba(0,212,255,0.1)', padding: '2px 8px', borderRadius: 10 }}>
                  {selectedStock.display}
                </span>
              )}
              {(stockQuery || selectedStock) && (
                <button onClick={e => { e.stopPropagation(); setStockQuery(''); setSelectedStock(null); setShowStockDD(false) }}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', padding: 0 }}>✕</button>
              )}
            </div>
            {showStockDD && stockResults.length > 0 && (
              <div style={dropdown}>
                {stockResults.map(s => (
                  <div key={s.symbol} style={ddItem}
                    onMouseDown={() => { setSelectedStock(s); setStockQuery(s.display); setShowStockDD(false); set('universe', 'INDIVIDUAL') }}>
                    <span style={{ fontWeight: 700, color: 'var(--text-1)', fontSize: 13 }}>{s.display}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-2)' }}>{s.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Section>

        {/* ── Step 2: Strategy ── */}
        <Section title="2 · Strategy Selection" icon="🧠">
          {strategies.length === 0 ? (
            <p style={{ fontSize: 13, color: 'var(--text-3)', textAlign: 'center', padding: '20px 0' }}>
              No strategies found. <a href="/strategies" style={{ color: 'var(--cyan)' }}>Create one first</a>.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {strategies.filter(s => s.isActive).map(s => (
                <div key={s.id} onClick={() => setStrategyId(s.id)}
                  style={{ ...stratItem, ...(strategyId === s.id ? stratItemActive : {}) }}>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 13, fontWeight: 600, color: strategyId === s.id ? 'var(--text-1)' : 'var(--text-2)' }}>{s.name}</p>
                    <p style={{ fontSize: 11, color: 'var(--text-3)' }}>{s.strategyType} · {s.timeframe}</p>
                  </div>
                  <div style={{ width: 16, height: 16, borderRadius: '50%', border: `2px solid ${strategyId === s.id ? 'var(--cyan)' : 'var(--border)'}`, background: strategyId === s.id ? 'var(--cyan)' : 'transparent' }} />
                </div>
              ))}
            </div>
          )}
        </Section>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* ── Step 3: Backtest Period ── */}
        <Section title="3 · Backtest Period" icon="📅">
          <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
            {PERIODS.map(p => (
              <button key={p.value} onClick={() => set('period', p.value)}
                style={{ flex: 1, ...periodBtn, ...(config.period === p.value ? periodBtnActive : {}) }}>
                {p.label}
              </button>
            ))}
          </div>
          {config.period === 'CUSTOM' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={lbl}>From Date</label>
                <input type="date" value={config.from_date} onChange={e => set('from_date', e.target.value)} style={inputStyle} />
              </div>
              <div>
                <label style={lbl}>To Date</label>
                <input type="date" value={config.to_date} onChange={e => set('to_date', e.target.value)} style={inputStyle} />
              </div>
            </div>
          )}
        </Section>

        {/* ── Step 4: Capital ── */}
        <Section title="4 · Capital & Position Sizing" icon="💰">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={lbl}>Initial Capital (₹)</label>
              <input type="number" min={10000} value={config.initial_capital}
                onChange={e => set('initial_capital', +e.target.value)} style={inputStyle} />
            </div>
            <div>
              <label style={lbl}>Max Capital Per Trade (%)</label>
              <input type="number" min={1} max={100} value={config.max_capital_per_trade_pct}
                onChange={e => set('max_capital_per_trade_pct', +e.target.value)} style={inputStyle} />
            </div>
            <div>
              <label style={lbl}>Max Open Positions</label>
              <input type="number" min={1} max={20} value={config.max_open_positions}
                onChange={e => set('max_open_positions', +e.target.value)} style={inputStyle} />
            </div>
            <div style={{ background: 'var(--surface-hi)', borderRadius: 8, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 3 }}>
              <span style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Capital Per Trade</span>
              <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--cyan)' }}>
                ₹{((config.initial_capital * config.max_capital_per_trade_pct / 100)).toLocaleString('en-IN')}
              </span>
              <span style={{ fontSize: 10, color: 'var(--text-3)' }}>
                Qty ≈ floor(capital / price)
              </span>
            </div>
          </div>
        </Section>
      </div>

      {/* ── Step 5: Risk Management ── */}
      <Section title="5 · Risk Management" icon="🛡️" style={{ marginBottom: 20 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          {/* SL */}
          <div>
            <label style={lbl}>Stop Loss %</label>
            <input type="number" min={0.1} max={20} step={0.1} value={config.sl_pct}
              onChange={e => set('sl_pct', +e.target.value)} style={inputStyle} />
          </div>

          {/* T1 */}
          <TargetRow label="Target 1 %" pct={config.t1_pct} qtyPct={config.t1_qty_pct}
            enabled={config.t1_enabled}
            onPct={v => set('t1_pct', v)} onQty={v => set('t1_qty_pct', v)}
            onToggle={() => set('t1_enabled', !config.t1_enabled)}
            color="var(--emerald)" />

          <TargetRow label="Target 2 %" pct={config.t2_pct} qtyPct={config.t2_qty_pct}
            enabled={config.t2_enabled}
            onPct={v => set('t2_pct', v)} onQty={v => set('t2_qty_pct', v)}
            onToggle={() => set('t2_enabled', !config.t2_enabled)}
            color="var(--amber)" />

          <TargetRow label="Target 3 %" pct={config.t3_pct} qtyPct={config.t3_qty_pct}
            enabled={config.t3_enabled}
            onPct={v => set('t3_pct', v)} onQty={v => set('t3_qty_pct', v)}
            onToggle={() => set('t3_enabled', !config.t3_enabled)}
            color="var(--cyan)" />
        </div>

        {/* Qty allocation bar */}
        <div style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 11, color: 'var(--text-2)' }}>Quantity Allocation</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: qtyOk ? 'var(--emerald)' : 'var(--rose)' }}>
              {totalQtyCfg}% {qtyOk ? '✓' : `(must be 100%)`}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 3, height: 8, borderRadius: 4, overflow: 'hidden', background: 'var(--surface-hi)' }}>
            {config.t1_enabled && <div style={{ width: `${config.t1_qty_pct}%`, background: 'var(--emerald)', transition: 'width 0.2s' }} />}
            {config.t2_enabled && <div style={{ width: `${config.t2_qty_pct}%`, background: 'var(--amber)', transition: 'width 0.2s' }} />}
            {config.t3_enabled && <div style={{ width: `${config.t3_qty_pct}%`, background: 'var(--cyan)', transition: 'width 0.2s' }} />}
          </div>
        </div>

        {/* Options */}
        <div style={{ display: 'flex', gap: 20, marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
          <Toggle checked={config.trailing_sl} onChange={() => set('trailing_sl', !config.trailing_sl)}>
            Trailing Stop Loss
          </Toggle>
          <Toggle checked={config.breakeven_after_t1} onChange={() => set('breakeven_after_t1', !config.breakeven_after_t1)}>
            Move SL to Breakeven after T1
          </Toggle>
        </div>
      </Section>

      {/* ── Step 6: Run ── */}
      {errors.length > 0 && (
        <div style={{ padding: '12px 16px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 10, marginBottom: 16 }}>
          {errors.map((e, i) => <p key={i} style={{ fontSize: 13, color: '#F87171', margin: 0 }}>{e}</p>)}
        </div>
      )}

      <button onClick={handleRun} disabled={running} style={runBtn}>
        {running ? (
          <>
            <div style={{ width: 16, height: 16, border: '2px solid rgba(0,0,0,0.3)', borderTopColor: '#000', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            Running backtest...
          </>
        ) : (
          <>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Run Backtest
          </>
        )}
      </button>

      {/* ── Results ── */}
      {results && results.status === 'completed' && results.results && (
        <ResultsPanel results={results.results} activeTab={activeTab} setActiveTab={setActiveTab} />
      )}
    </div>
  )
}


// ─── Sub-components ──────────────────────────────────────────────────────────

function Section({ title, icon, children, style = {} }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '20px 20px', ...style }}>
      <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 14 }}>
        {icon} {title}
      </p>
      {children}
    </div>
  )
}

function UnivBtn({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{
      padding: '8px 6px', borderRadius: 8, cursor: 'pointer', textAlign: 'center',
      background: active ? 'rgba(0,212,255,0.1)' : 'var(--surface-hi)',
      border: `1px solid ${active ? 'var(--cyan)' : 'var(--border)'}`,
      color: active ? 'var(--cyan)' : 'var(--text-2)',
    }}>
      {children}
    </button>
  )
}

function TargetRow({ label, pct, qtyPct, enabled, onPct, onQty, onToggle, color }) {
  return (
    <div style={{ opacity: enabled ? 1 : 0.4 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <label style={{ ...lbl, color }}>{label}</label>
        <Toggle checked={enabled} onChange={onToggle} small />
      </div>
      <input type="number" min={0.1} max={50} step={0.1} value={pct}
        disabled={!enabled} onChange={e => onPct(+e.target.value)}
        style={{ ...inputStyle, borderColor: enabled ? color : 'var(--border)', marginBottom: 8 }} />
      <label style={{ ...lbl, color: 'var(--text-3)', fontSize: 10 }}>Exit Qty %</label>
      <input type="number" min={1} max={100} value={qtyPct}
        disabled={!enabled} onChange={e => onQty(+e.target.value)}
        style={{ ...inputStyle, borderColor: enabled ? color : 'var(--border)' }} />
    </div>
  )
}

function Toggle({ checked, onChange, children, small }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
      <div onClick={onChange} style={{
        width: small ? 28 : 36, height: small ? 16 : 20, borderRadius: 10, flexShrink: 0,
        background: checked ? 'var(--cyan)' : 'var(--surface-hi)',
        border: `1px solid ${checked ? 'var(--cyan)' : 'var(--border)'}`,
        position: 'relative', cursor: 'pointer', transition: 'all 0.2s',
      }}>
        <div style={{
          position: 'absolute', top: 2, width: small ? 10 : 14, height: small ? 10 : 14,
          borderRadius: '50%', background: checked ? '#000' : 'var(--text-3)',
          left: checked ? (small ? 14 : 18) : 2, transition: 'left 0.2s',
        }} />
      </div>
      {children && <span style={{ fontSize: 12, color: 'var(--text-2)' }}>{children}</span>}
    </label>
  )
}

function ResultsPanel({ results, activeTab, setActiveTab }) {
  const { summary, trades = [] } = results
  if (!summary) return null

  const pnlPositive = summary.totalPnL >= 0

  return (
    <div style={{ marginTop: 28 }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-1)', marginBottom: 20 }}>Results</h2>

      {/* KPI Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        <KPI label="Initial Capital"   value={`₹${fmt(summary.initialCapital)}`}  />
        <KPI label="Final Capital"     value={`₹${fmt(summary.finalCapital)}`}     />
        <KPI label="Total P&L"
             value={`${pnlPositive ? '+' : ''}₹${fmt(summary.totalPnL)}`}
             color={pnlPositive ? 'var(--emerald)' : 'var(--rose)'} />
        <KPI label="Total Return"
             value={`${pnlPositive ? '+' : ''}${summary.totalReturnPct.toFixed(2)}%`}
             color={pnlPositive ? 'var(--emerald)' : 'var(--rose)'} />
        <KPI label="Win Rate"          value={`${summary.winRate.toFixed(1)}%`}     color="var(--cyan)"    />
        <KPI label="Total Trades"      value={summary.totalTrades}                                        />
        <KPI label="Max Drawdown"      value={`${summary.maxDrawdownPct.toFixed(2)}%`} color="var(--rose)" />
        <KPI label="Avg Holding Days"  value={`${summary.avgHoldingDays.toFixed(1)}d`}                     />
        <KPI label="Sharpe Ratio"      value={summary.sharpeRatio.toFixed(3)}       color="var(--amber)"  />
        <KPI label="Sortino Ratio"     value={summary.sortinRatio.toFixed(3)}       color="var(--amber)"  />
        <KPI label="Available Capital" value={`₹${fmt(summary.availableCapital)}`}  />
        <KPI label="Invested Capital"  value={`₹${fmt(summary.investedCapital)}`}   />
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)', marginBottom: 20 }}>
        {['summary', 'trades'].map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            style={{ padding: '10px 20px', border: 'none', background: 'none', cursor: 'pointer',
              fontSize: 13, fontWeight: 600, color: activeTab === t ? 'var(--cyan)' : 'var(--text-2)',
              borderBottom: `2px solid ${activeTab === t ? 'var(--cyan)' : 'transparent'}`,
              textTransform: 'capitalize' }}>
            {t === 'trades' ? `Trades (${trades.length})` : 'Summary'}
          </button>
        ))}
      </div>

      {activeTab === 'summary' && <SummaryTab summary={summary} />}
      {activeTab === 'trades'  && <TradesTab trades={trades} />}
    </div>
  )
}

function SummaryTab({ summary }) {
  const wins    = summary.totalWins
  const losses  = summary.totalLosses
  const total   = summary.totalTrades

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
      <div style={sCard}>
        <p style={sCardTitle}>Win / Loss Breakdown</p>
        <div style={{ display: 'flex', gap: 4, height: 24, borderRadius: 6, overflow: 'hidden', marginBottom: 12 }}>
          <div style={{ width: `${wins/total*100}%`, background: 'var(--emerald)' }} />
          <div style={{ width: `${losses/total*100}%`, background: 'var(--rose)' }} />
        </div>
        <div style={{ display: 'flex', gap: 20 }}>
          <div><p style={{ fontSize: 22, fontWeight: 700, color: 'var(--emerald)' }}>{wins}</p><p style={sLabel}>Wins</p></div>
          <div><p style={{ fontSize: 22, fontWeight: 700, color: 'var(--rose)' }}>{losses}</p><p style={sLabel}>Losses</p></div>
          <div><p style={{ fontSize: 22, fontWeight: 700, color: 'var(--cyan)' }}>{total}</p><p style={sLabel}>Total</p></div>
        </div>
      </div>
      <div style={sCard}>
        <p style={sCardTitle}>Average P&L</p>
        <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
          <div>
            <p style={{ fontSize: 20, fontWeight: 700, color: 'var(--emerald)' }}>₹{fmt(summary.avgWinPnL)}</p>
            <p style={sLabel}>Avg Win</p>
          </div>
          <div>
            <p style={{ fontSize: 20, fontWeight: 700, color: 'var(--rose)' }}>₹{fmt(Math.abs(summary.avgLossPnL))}</p>
            <p style={sLabel}>Avg Loss</p>
          </div>
          {summary.profitFactor != null && (
            <div>
              <p style={{ fontSize: 20, fontWeight: 700, color: 'var(--amber)' }}>{summary.profitFactor.toFixed(2)}x</p>
              <p style={sLabel}>Profit Factor</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function TradesTab({ trades }) {
  const [sort, setSort] = useState({ key: 'entryDate', dir: 'desc' })
  const [page, setPage] = useState(0)
  const PER_PAGE = 25

  const sorted = [...trades].sort((a, b) => {
    const av = a[sort.key], bv = b[sort.key]
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sort.dir === 'asc' ? cmp : -cmp
  })
  const paged = sorted.slice(page * PER_PAGE, (page + 1) * PER_PAGE)
  const totalPages = Math.ceil(sorted.length / PER_PAGE)

  const toggle = key => setSort(s => ({ key, dir: s.key === key && s.dir === 'asc' ? 'desc' : 'asc' }))
  const Th = ({ k, children }) => (
    <th onClick={() => toggle(k)} style={thStyle}>
      {children} {sort.key === k ? (sort.dir === 'asc' ? '↑' : '↓') : ''}
    </th>
  )

  const exitColor = t => {
    if (!t.isClosed) return 'var(--text-3)'
    if (t.exitType === 'SL') return 'var(--rose)'
    if (t.exitType === 'T3') return 'var(--cyan)'
    return 'var(--emerald)'
  }

  return (
    <div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: 'var(--surface-hi)' }}>
              <Th k="strategyName">Strategy</Th>
              <Th k="symbol">Symbol</Th>
              <Th k="direction">B/S</Th>
              <Th k="entryDate">Entry Date</Th>
              <Th k="entryPrice">Entry ₹</Th>
              <Th k="quantity">Qty</Th>
              <Th k="sl">SL</Th>
              <Th k="t1">T1</Th>
              <Th k="t2">T2</Th>
              <Th k="t3">T3</Th>
              <Th k="exitDate">Exit Date</Th>
              <Th k="exitPrice">Exit ₹</Th>
              <Th k="remainingQty">Rem Qty</Th>
              <Th k="exitType">Exit Type</Th>
              <Th k="pnl">P&L</Th>
              <Th k="pnlPct">P&L %</Th>
            </tr>
          </thead>
          <tbody>
            {paged.map((t, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)' }}>
                <td style={tdStyle}>{t.strategyName}</td>
                <td style={{ ...tdStyle, fontWeight: 700, color: 'var(--text-1)' }}>{t.symbol}</td>
                <td style={{ ...tdStyle, color: t.direction === 'BUY' ? 'var(--emerald)' : 'var(--rose)', fontWeight: 700 }}>{t.direction}</td>
                <td style={tdStyle}>{fmtDate(t.entryDate)}</td>
                <td style={tdStyle}>₹{t.entryPrice?.toFixed(2)}</td>
                <td style={tdStyle}>{t.quantity}</td>
                <td style={{ ...tdStyle, color: 'var(--rose)' }}>₹{t.sl?.toFixed(2)}</td>
                <td style={{ ...tdStyle, color: 'var(--emerald)' }}>₹{t.t1?.toFixed(2)}</td>
                <td style={{ ...tdStyle, color: 'var(--amber)' }}>₹{t.t2?.toFixed(2)}</td>
                <td style={{ ...tdStyle, color: 'var(--cyan)' }}>₹{t.t3?.toFixed(2)}</td>
                <td style={tdStyle}>{t.exitDate ? fmtDate(t.exitDate) : '—'}</td>
                <td style={tdStyle}>{t.exitPrice ? `₹${t.exitPrice.toFixed(2)}` : '—'}</td>
                <td style={tdStyle}>{t.remainingQty}</td>
                <td style={{ ...tdStyle, color: exitColor(t), fontWeight: 600 }}>{t.exitType || '—'}</td>
                <td style={{ ...tdStyle, color: t.pnl >= 0 ? 'var(--emerald)' : 'var(--rose)', fontWeight: 700 }}>
                  {t.pnl >= 0 ? '+' : ''}₹{t.pnl?.toFixed(2)}
                </td>
                <td style={{ ...tdStyle, color: t.pnl >= 0 ? 'var(--emerald)' : 'var(--rose)' }}>
                  {t.pnlPct >= 0 ? '+' : ''}{t.pnlPct?.toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
          <button disabled={page === 0} onClick={() => setPage(p => p - 1)} style={pgBtn}>Prev</button>
          <span style={{ fontSize: 12, color: 'var(--text-2)', alignSelf: 'center' }}>
            Page {page + 1} of {totalPages}
          </span>
          <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} style={pgBtn}>Next</button>
        </div>
      )}
    </div>
  )
}

function KPI({ label, value, color }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
      <p style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>{label}</p>
      <p style={{ fontSize: 18, fontWeight: 700, color: color || 'var(--text-1)' }}>{value}</p>
    </div>
  )
}

const fmt     = n => (n == null ? '—' : Math.abs(n) >= 1000 ? (n/1000).toFixed(1) + 'K' : n.toFixed(2))
const fmtDate = d => { if (!d) return '—'; try { return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' }) } catch { return d } }

const inputStyle = { width: '100%', padding: '9px 12px', borderRadius: 8, background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-1)', fontSize: 13, outline: 'none', boxSizing: 'border-box' }
const lbl        = { display: 'block', fontSize: 10, fontWeight: 600, color: 'var(--text-2)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }
const periodBtn  = { padding: '8px 4px', borderRadius: 7, cursor: 'pointer', background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-2)', fontSize: 11 }
const periodBtnActive = { background: 'rgba(0,212,255,0.1)', border: '1px solid var(--cyan)', color: 'var(--cyan)', fontWeight: 700 }
const stratItem  = { display: 'flex', alignItems: 'center', padding: '10px 12px', borderRadius: 8, border: '1px solid var(--border)', cursor: 'pointer', background: 'var(--surface-hi)' }
const stratItemActive = { border: '1px solid var(--cyan)', background: 'rgba(0,212,255,0.05)' }
const runBtn     = { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, width: '100%', padding: '14px', borderRadius: 10, cursor: 'pointer', background: 'var(--cyan)', border: 'none', color: '#000', fontSize: 15, fontWeight: 700, marginBottom: 28 }
const dropdown   = { position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, marginTop: 4, boxShadow: '0 8px 24px rgba(0,0,0,0.3)', maxHeight: 240, overflowY: 'auto' }
const ddItem     = { display: 'flex', flexDirection: 'column', padding: '10px 14px', cursor: 'pointer', borderBottom: '1px solid var(--border)', gap: 2 }
const sCard      = { background: 'var(--surface-hi)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 18px' }
const sCardTitle = { fontSize: 11, fontWeight: 700, color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }
const sLabel     = { fontSize: 11, color: 'var(--text-3)', marginTop: 2 }
const thStyle    = { padding: '10px 12px', textAlign: 'left', fontSize: 10, fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', cursor: 'pointer', whiteSpace: 'nowrap', userSelect: 'none' }
const tdStyle    = { padding: '9px 12px', color: 'var(--text-2)', whiteSpace: 'nowrap' }
const pgBtn      = { padding: '6px 16px', borderRadius: 6, cursor: 'pointer', background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-2)', fontSize: 12 }


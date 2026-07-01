import { useEffect, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, ReferenceLine, CartesianGrid,
} from 'recharts'
import { getPnlChart, getStrategyStats, getTopSymbols, getWeeklySummary, getMonthlySummary, getRiskReport } from '../api'
import StatCard from '../components/StatCard'

const fmtINR  = v => v == null ? '—' : `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
const fmtINR2 = v => v == null ? '—' : `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`

const STRAT_COLORS = ['#00D4FF','#00FF88','#FFB800','#FF3B6B','#7B6FFF','#00D4FF','#FFB800','#00FF88']

function ChartTip({ active, payload, label, fmt }) {
  if (!active || !payload?.length) return null
  const v = payload[0].value
  return (
    <div style={{ background: 'var(--surface-hi)', border: '1px solid var(--border-hi)', borderRadius: 6, padding: '8px 12px' }}>
      <p style={{ fontSize: 10, color: 'var(--text-2)', marginBottom: 4 }}>{label}</p>
      <p style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-mono)', color: v >= 0 ? '#00FF88' : '#FF3B6B' }}>
        {v >= 0 ? '+' : ''}{fmt ? fmt(v) : v}
      </p>
    </div>
  )
}

function PanelTitle({ children }) {
  return <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)', marginBottom: 16 }}>{children}</p>
}

function Panel({ children, style }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '18px 20px', ...style }}>
      {children}
    </div>
  )
}

export default function Analytics() {
  const [chart, setChart]     = useState([])
  const [strategies, setStrats] = useState([])
  const [symbols, setSymbols] = useState([])
  const [weekly, setWeekly]   = useState(null)
  const [monthly, setMonthly] = useState(null)
  const [days, setDays]       = useState(30)
  const [risk, setRisk]       = useState(null)

  useEffect(() => {
    getPnlChart(days).then(r => setChart(r.data.map(d => ({ ...d, pnl: parseFloat(d.pnl) }))))
    getRiskReport(days).then(r => setRisk(r.data)).catch(() => {})
  }, [days])

  useEffect(() => {
    getStrategyStats().then(r => setStrats(r.data))
    getTopSymbols().then(r => setSymbols(r.data))
    getWeeklySummary().then(r => setWeekly(r.data))
    getMonthlySummary().then(r => setMonthly(r.data))
  }, [])

  const cumulativeChart = chart.reduce((acc, d, i) => {
    acc.push({ ...d, cumulative: (i > 0 ? acc[i - 1].cumulative : 0) + d.pnl })
    return acc
  }, [])

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <p style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Performance</p>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.03em' }}>Analytics</h1>
      </div>

      {/* Summary stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <StatCard label="Week P&L"       color={(weekly?.totalPnL ?? 0) >= 0 ? 'cyan' : 'rose'} value={fmtINR(weekly?.totalPnL)} />
        <StatCard label="Week Win Rate"   color="emerald" value={weekly ? `${weekly.winRate}%` : '—'} />
        <StatCard label="Month P&L"      color={(monthly?.totalPnL ?? 0) >= 0 ? 'cyan' : 'rose'} value={fmtINR(monthly?.totalPnL)} />
        <StatCard label="Month Win Rate"  color="emerald" value={monthly ? `${monthly.winRate}%` : '—'} />
      </div>

      {/* Daily P&L bar chart */}
      <Panel>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <PanelTitle>Daily P&L</PanelTitle>
          <div style={{ display: 'flex', gap: 4 }}>
            {[7, 14, 30, 90].map(d => (
              <button key={d} onClick={() => setDays(d)} style={{
                fontSize: 11, fontWeight: 500, padding: '4px 10px', borderRadius: 4, cursor: 'pointer', border: '1px solid',
                borderColor: days === d ? 'rgba(0,212,255,0.4)' : 'var(--border)',
                background:  days === d ? 'rgba(0,212,255,0.1)' : 'transparent',
                color:       days === d ? 'var(--cyan)' : 'var(--text-2)',
                transition: 'all 0.15s ease',
              }}>
                {d}d
              </button>
            ))}
          </div>
        </div>
        {chart.length === 0 ? (
          <div style={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-3)', fontSize: 13 }}>No trade data yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={chart} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="2 8" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 10, fontFamily: 'var(--font-mono)' }} tickFormatter={d => d.slice(5)} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-3)', fontSize: 10, fontFamily: 'var(--font-mono)' }} tickFormatter={v => `${(v/1000).toFixed(0)}k`} axisLine={false} tickLine={false} width={40} />
              <Tooltip content={<ChartTip fmt={fmtINR2} />} />
              <ReferenceLine y={0} stroke="rgba(255,59,107,0.3)" strokeDasharray="3 6" />
              <Bar dataKey="pnl" radius={[3, 3, 0, 0]} maxBarSize={32}>
                {chart.map((d, i) => <Cell key={i} fill={d.pnl >= 0 ? '#00D4FF' : '#FF3B6B'} opacity={d.pnl >= 0 ? 0.85 : 0.75} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Panel>

      {/* Cumulative P&L */}
      <Panel>
        <PanelTitle>Equity Curve — Cumulative P&L</PanelTitle>
        {cumulativeChart.length === 0 ? (
          <div style={{ height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-3)', fontSize: 13 }}>No data</div>
        ) : (
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={cumulativeChart} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="cumGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor="#00D4FF" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#00D4FF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 8" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 10, fontFamily: 'var(--font-mono)' }} tickFormatter={d => d.slice(5)} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-3)', fontSize: 10, fontFamily: 'var(--font-mono)' }} tickFormatter={v => `${(v/1000).toFixed(0)}k`} axisLine={false} tickLine={false} width={40} />
              <Tooltip content={<ChartTip fmt={fmtINR2} />} />
              <ReferenceLine y={0} stroke="rgba(255,59,107,0.3)" strokeDasharray="3 6" />
              <Line type="monotone" dataKey="cumulative" stroke="#00D4FF" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Panel>

      {/* Risk Report */}
      {risk && (
        <Panel>
          <PanelTitle>Risk Report — Last {days}d</PanelTitle>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {[
              { label: 'Max Drawdown',       value: risk.maxDrawdown != null ? `${risk.maxDrawdown.toFixed(1)}%` : '—',   color: risk.maxDrawdown > 10 ? '#FF3B6B' : '#00FF88' },
              { label: 'Sharpe Ratio',        value: risk.sharpeRatio != null ? risk.sharpeRatio.toFixed(2) : '—',          color: risk.sharpeRatio > 1 ? '#00FF88' : risk.sharpeRatio > 0 ? '#FFB800' : '#FF3B6B' },
              { label: 'Profit Factor',       value: risk.profitFactor != null ? risk.profitFactor.toFixed(2) : '—',        color: risk.profitFactor > 1.5 ? '#00FF88' : risk.profitFactor > 1 ? '#FFB800' : '#FF3B6B' },
              { label: 'Max Consec. Losses',  value: risk.maxConsecutiveLosses ?? '—',                                      color: risk.maxConsecutiveLosses > 5 ? '#FF3B6B' : '#FFB800' },
            ].map(m => (
              <div key={m.label} style={{ background: 'var(--surface-hi)', borderRadius: 8, padding: '14px 16px', border: '1px solid var(--border)' }}>
                <p style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>{m.label}</p>
                <p style={{ fontSize: 22, fontWeight: 700, fontFamily: 'var(--font-mono)', color: m.color }}>{m.value}</p>
              </div>
            ))}
          </div>
        </Panel>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {/* Strategy contribution */}
        <Panel>
          <PanelTitle>Strategy Performance</PanelTitle>
          {strategies.length === 0 ? (
            <div style={{ height: 140, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-3)', fontSize: 13 }}>No closed trades yet</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {strategies.map((s, i) => {
                const wr = s.total_trades > 0 ? Math.round(s.wins / s.total_trades * 100) : 0
                const col = STRAT_COLORS[i % STRAT_COLORS.length]
                return (
                  <div key={s.strategy}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                      <span style={{ fontSize: 11, color: 'var(--text-2)', textTransform: 'capitalize' }}>{s.strategy.replace(/_/g, ' ')}</span>
                      <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: col }}>{wr}% <span style={{ color: 'var(--text-3)' }}>({s.total_trades})</span></span>
                    </div>
                    <div style={{ height: 3, background: 'var(--border)', borderRadius: 99 }}>
                      <div style={{ height: 3, borderRadius: 99, width: `${wr}%`, background: col, boxShadow: `0 0 6px ${col}50`, transition: 'width 0.8s ease' }} />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </Panel>

        {/* Top symbols */}
        <Panel>
          <PanelTitle>Top Performing Symbols</PanelTitle>
          {symbols.length === 0 ? (
            <div style={{ height: 140, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-3)', fontSize: 13 }}>No closed trades yet</div>
          ) : (
            <div>
              {symbols.map((s, i) => {
                const pnl = parseFloat(s.total_pnl)
                return (
                  <div key={s.display_symbol} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ width: 20, fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-3)' }}>#{i + 1}</span>
                      <div>
                        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)' }}>{s.display_symbol}</p>
                        <p style={{ fontSize: 10, color: 'var(--text-3)' }}>{s.trades} trades · {s.win_rate}% win</p>
                      </div>
                    </div>
                    <span style={{ fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-mono)', color: pnl >= 0 ? '#00FF88' : '#FF3B6B' }}>
                      {pnl >= 0 ? '+' : ''}{fmtINR2(pnl)}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}


import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts'
import { getSummary, getPnlChart } from '../api'
import StatCard from '../components/StatCard'
import LiveDashboard from '../components/LiveDashboard'

const fmtINR = v => v == null ? '—' : `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
const fmtINR2 = v => v == null ? '—' : `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
const pct    = v => v == null ? '—' : `${Number(v).toFixed(1)}%`
const sign   = v => Number(v) >= 0 ? '+' : ''

function ChartTip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const v = payload[0].value
  return (
    <div style={{ background: 'var(--surface-hi)', border: '1px solid var(--border-hi)', borderRadius: 6, padding: '8px 12px', boxShadow: '0 8px 24px rgba(0,0,0,0.5)' }}>
      <p style={{ fontSize: 10, color: 'var(--text-2)', marginBottom: 4 }}>{label}</p>
      <p style={{ fontSize: 13, fontWeight: 600, fontFamily: 'var(--font-mono)', color: v >= 0 ? '#00FF88' : '#FF3B6B' }}>
        {v >= 0 ? '+' : ''}{fmtINR2(v)}
      </p>
    </div>
  )
}

function SectionLabel({ children }) {
  return (
    <p style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 12 }}>
      {children}
    </p>
  )
}

function PageHeader() {
  const now = new Date()
  const dateStr = now.toLocaleDateString('en-IN', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' })
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 28 }}>
      <div>
        <p style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Dashboard</p>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.03em' }}>Trading Overview</h1>
      </div>
      <div style={{
        fontSize: 11, color: 'var(--text-2)',
        background: 'var(--surface)', border: '1px solid var(--border)',
        padding: '7px 14px', borderRadius: 6,
        fontFamily: 'var(--font-mono)',
      }}>
        {dateStr}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [chart, setChart]     = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getSummary(), getPnlChart(30)])
      .then(([s, c]) => {
        setSummary(s.data)
        setChart(c.data.map(d => ({ ...d, pnl: parseFloat(d.pnl) })))
      })
      .finally(() => setLoading(false))
  }, [])

  const todayPnl = summary?.todayPnL ?? 0
  const totalPnl = summary?.totalProfitLoss ?? 0
  const chartCol = chart.length && chart[chart.length - 1]?.pnl >= 0 ? '#00D4FF' : '#FF3B6B'

  return (
    <div className="fade-up">
      <PageHeader />

      {/* P&L performance row */}
      <div style={{ marginBottom: 28 }}>
        <SectionLabel>Performance</SectionLabel>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          <StatCard isLoading={loading} label="Today's P&L"   color={todayPnl >= 0 ? 'cyan' : 'rose'}    value={`${sign(todayPnl)}${fmtINR(todayPnl)}`} />
          <StatCard isLoading={loading} label="This Week"     color={(summary?.weekPnL ?? 0) >= 0 ? 'cyan' : 'rose'} value={`${sign(summary?.weekPnL ?? 0)}${fmtINR(summary?.weekPnL)}`} />
          <StatCard isLoading={loading} label="This Month"    color={(summary?.monthPnL ?? 0) >= 0 ? 'cyan' : 'rose'} value={`${sign(summary?.monthPnL ?? 0)}${fmtINR(summary?.monthPnL)}`} />
          <StatCard isLoading={loading} label="All-Time P&L"  color={totalPnl >= 0 ? 'emerald' : 'rose'} value={`${sign(totalPnl)}${fmtINR(totalPnl)}`} />
        </div>
      </div>

      {/* Account row */}
      <div style={{ marginBottom: 28 }}>
        <SectionLabel>Account</SectionLabel>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          <StatCard isLoading={loading} label="Balance"         color="violet" value={fmtINR(summary?.accountBalance)} />
          <StatCard isLoading={loading} label="Available"       color="cyan"   value={fmtINR(summary?.availableCapital)} />
          <StatCard isLoading={loading} label="Win Rate"        color="emerald" value={pct(summary?.winRate)} />
          <StatCard isLoading={loading} label="Active Positions" color="amber"  value={String(summary?.activeTrades ?? 0)} sub={`${summary?.closedTrades ?? 0} closed total`} />
        </div>
      </div>

      {/* Chart + summary side by side */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 12, marginBottom: 28 }}>
        {/* P&L Area Chart */}
        <div style={{ background: 'var(--surface)', borderRadius: 10, border: '1px solid var(--border)', padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18 }}>
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)' }}>P&L Performance</p>
              <p style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 3 }}>Last 30 trading days</p>
            </div>
            <span style={{
              fontSize: 12, fontWeight: 700, fontFamily: 'var(--font-mono)',
              color: totalPnl >= 0 ? '#00FF88' : '#FF3B6B',
              background: totalPnl >= 0 ? 'rgba(0,255,136,0.1)' : 'rgba(255,59,107,0.1)',
              padding: '4px 10px', borderRadius: 4, border: `1px solid ${totalPnl >= 0 ? 'rgba(0,255,136,0.2)' : 'rgba(255,59,107,0.2)'}`,
            }}>
              {sign(totalPnl)}{fmtINR(totalPnl)}
            </span>
          </div>

          {chart.length === 0 ? (
            <div style={{ height: 200, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
              {/* Placeholder chart outline */}
              <svg width="200" height="60" viewBox="0 0 200 60" fill="none">
                <path d="M0 50 Q25 40 50 45 T100 30 T150 20 T200 10" stroke="var(--border-hi)" strokeWidth="1.5" strokeDasharray="4 4" fill="none"/>
              </svg>
              <p style={{ fontSize: 13, color: 'var(--text-3)' }}>No trades yet — signals will appear here</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chart} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor={chartCol} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={chartCol} stopOpacity={0}    />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="2 8" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 10, fontFamily: 'var(--font-mono)' }} tickFormatter={d => d.slice(5)} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-3)', fontSize: 10, fontFamily: 'var(--font-mono)' }} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} axisLine={false} tickLine={false} width={40} orientation="right" />
                <Tooltip content={<ChartTip />} />
                <ReferenceLine y={0} stroke="rgba(255,59,107,0.35)" strokeDasharray="3 6" />
                <Area type="monotone" dataKey="pnl" stroke={chartCol} strokeWidth={1.5} fill="url(#pnlGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Trade Summary */}
        <div style={{
          background: 'var(--surface)', borderRadius: 10,
          border: '1px solid var(--border)',
          borderLeft: '2px solid #FFB800',
          boxShadow: '0 4px 20px rgba(0,0,0,0.45), -4px 0 20px rgba(255,184,0,0.2)',
          padding: '20px',
        }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)', marginBottom: 18 }}>Trade Summary</p>
          <div>
            {[
              { label: 'Total Signals',  value: summary?.totalTrades ?? 0,           color: 'var(--text-1)' },
              { label: 'Profitable',     value: summary?.profitableTrades ?? 0,       color: '#00FF88' },
              { label: 'Loss Trades',    value: summary?.lossTrades ?? 0,             color: '#FF3B6B' },
              { label: 'Avg P&L/Trade',  value: fmtINR2(summary?.averageProfitLoss), color: (summary?.averageProfitLoss ?? 0) >= 0 ? '#00FF88' : '#FF3B6B' },
            ].map(r => (
              <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                <span style={{ fontSize: 12, color: 'var(--text-2)' }}>{r.label}</span>
                <span style={{ fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-mono)', color: r.color }}>{r.value}</span>
              </div>
            ))}
          </div>

          {/* Win rate bar */}
          <div style={{ marginTop: 18 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 11, color: 'var(--text-2)' }}>Win Rate</span>
              <span style={{ fontSize: 12, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-1)' }}>{pct(summary?.winRate)}</span>
            </div>
            <div style={{ height: 3, background: 'var(--border)', borderRadius: 99 }}>
              <div style={{
                height: 3, borderRadius: 99,
                width: `${summary?.winRate ?? 0}%`,
                background: 'linear-gradient(90deg, #00D4FF, #00FF88)',
                transition: 'width 0.8s ease',
              }} />
            </div>
            {/* Donut placeholder */}
            <div style={{ display: 'flex', justifyContent: 'center', marginTop: 18 }}>
              <svg width="80" height="80" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="30" fill="none" stroke="var(--border)" strokeWidth="10" />
                {(summary?.winRate ?? 0) > 0 && (
                  <circle cx="40" cy="40" r="30" fill="none" stroke="#00FF88" strokeWidth="10"
                    strokeDasharray={`${(summary.winRate / 100) * 188.5} 188.5`}
                    strokeDashoffset="47.1" strokeLinecap="round"
                    style={{ filter: 'drop-shadow(0 0 4px rgba(0,255,136,0.5))' }}
                  />
                )}
                <text x="40" y="37" textAnchor="middle" fill="currentColor" fontSize="11" fontWeight="700" fontFamily="JetBrains Mono">{pct(summary?.winRate)}</text>
                <text x="40" y="51" textAnchor="middle" fill="var(--text-3)" fontSize="9" fontFamily="Inter">win rate</text>
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Live Positions */}
      <div>
        <SectionLabel>Live Positions</SectionLabel>
        <LiveDashboard />
      </div>
    </div>
  )
}


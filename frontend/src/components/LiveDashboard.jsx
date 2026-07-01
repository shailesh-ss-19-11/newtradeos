import { useEffect, useRef, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

const fmtINR = v => v == null ? '—' : `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
const fmtINR2 = v => v == null ? '—' : `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
const fmtPct  = v => v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(2)}%`

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

function MiniCard({ label, value, color }) {
  return (
    <div style={{
      background: 'var(--surface)', borderRadius: 8, padding: '14px 16px',
      border: '1px solid var(--border)',
      borderLeft: `2px solid ${color}`,
      boxShadow: `0 4px 16px rgba(0,0,0,0.4), -3px 0 14px ${color}40`,
    }}>
      <p style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-2)', textTransform: 'uppercase', letterSpacing: '0.09em', marginBottom: 8 }}>{label}</p>
      <p style={{ fontSize: 20, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-1)', letterSpacing: '-0.02em' }}>{value}</p>
    </div>
  )
}

export default function LiveDashboard() {
  const [data, setData]         = useState(null)
  const [chart, setChart]       = useState([])
  const [connected, setConn]    = useState(false)

  useEffect(() => {
    const es = new EventSource('/api/live')
    es.onopen  = () => setConn(true)
    es.onerror = () => setConn(false)
    es.onmessage = e => {
      try {
        const p = JSON.parse(e.data)
        if (p.error) return
        setData(p)
        setChart(prev => {
          const ts = new Date(p.timestamp).toLocaleTimeString('en-IN', { hour12: false })
          return [...prev, { time: ts, pnl: p.totalUnrealizedPnl }].slice(-60)
        })
      } catch {}
    }
    return () => es.close()
  }, [])

  const noTrades  = !data || data.tradeCount === 0
  const totalPnl  = data?.totalUnrealizedPnl ?? 0
  const pnlUp     = totalPnl >= 0
  const chartCol  = chart.length && chart[chart.length - 1]?.pnl >= 0 ? '#00FF88' : '#FF3B6B'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Status strip */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '4px 12px', borderRadius: 4,
          background: connected ? 'rgba(0,255,136,0.08)' : 'rgba(255,59,107,0.08)',
          border: `1px solid ${connected ? 'rgba(0,255,136,0.2)' : 'rgba(255,59,107,0.2)'}`,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%', flexShrink: 0, display: 'inline-block',
            background: connected ? '#00FF88' : '#FF3B6B',
            boxShadow: connected ? '0 0 6px #00FF88' : 'none',
          }} className={connected ? 'pulse-dot' : ''} />
          <span style={{ fontSize: 11, fontWeight: 600, color: connected ? '#00FF88' : '#FF3B6B' }}>
            {connected ? 'Live' : 'Disconnected'}
          </span>
        </div>
        <span style={{ fontSize: 11, color: 'var(--text-3)' }}>Updates every 2s</span>
        <div className="progress-2s" />
      </div>

      {/* Three mini cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <MiniCard label="Unrealized P&L"   value={`${pnlUp ? '+' : ''}${fmtINR2(totalPnl)}`}    color={pnlUp ? '#00FF88' : '#FF3B6B'} />
        <MiniCard label="Capital Deployed"  value={fmtINR(data?.totalCapitalDeployed)}             color="#00D4FF" />
        <MiniCard label="Open Positions"    value={data?.tradeCount ?? '—'}                         color="#FFB800" />
      </div>

      {/* Live chart */}
      <div style={{ background: 'var(--surface)', borderRadius: 10, border: '1px solid var(--border)', padding: '18px 20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)' }}>Unrealized P&L — Live</p>
          <p style={{ fontSize: 10, color: 'var(--text-3)' }}>Last 2 min</p>
        </div>
        {chart.length < 2 ? (
          <div style={{ height: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <p style={{ fontSize: 13, color: 'var(--text-3)' }}>
              {connected ? `Scanner active — monitoring symbols` : 'Connecting to live feed…'}
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={100}>
            <AreaChart data={chart} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="liveGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor={chartCol} stopOpacity={0.2} />
                  <stop offset="100%" stopColor={chartCol} stopOpacity={0}   />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" tick={{ fill: 'var(--text-3)', fontSize: 9, fontFamily: 'var(--font-mono)' }} interval="preserveStartEnd" axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-3)', fontSize: 9, fontFamily: 'var(--font-mono)' }} tickFormatter={v => `${(v/1000).toFixed(1)}k`} width={38} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTip />} />
              <ReferenceLine y={0} stroke="rgba(255,59,107,0.3)" strokeDasharray="3 6" />
              <Area type="monotone" dataKey="pnl" stroke={chartCol} strokeWidth={1.5} fill="url(#liveGrad)" dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Positions table */}
      <div style={{ background: 'var(--surface)', borderRadius: 10, border: '1px solid var(--border)', overflow: 'hidden' }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)' }}>Open Positions</p>
          {!noTrades && <span style={{ fontSize: 11, color: 'var(--text-3)' }}>{data.tradeCount} active</span>}
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                {['Symbol','Type','Entry','LTP','Stop Loss','Target','Qty','Capital','Unreal. P&L','Chg %','Conf'].map(h => <th key={h}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {noTrades ? (
                <tr>
                  <td colSpan={11} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-3)' }}>
                    <p>Scanner active — no open positions</p>
                  </td>
                </tr>
              ) : data.activeTrades.map(t => {
                const pnlPos  = (t.unrealizedPnl ?? 0) >= 0
                const priceUp = t.currentPrice != null && (t.type === 'BUY' ? t.currentPrice >= t.entryPrice : t.currentPrice <= t.entryPrice)
                return (
                  <tr key={t.tradeId}>
                    <td>
                      <span style={{ fontWeight: 600, color: 'var(--text-1)' }}>{t.displaySymbol}</span>
                      <span style={{ fontSize: 9, fontWeight: 600, marginLeft: 5, padding: '1px 5px', borderRadius: 3, background: 'var(--surface-hi)', color: 'var(--text-2)', border: '1px solid var(--border)' }}>
                        {t.symbol?.split(':')[0] || 'NSE'}
                      </span>
                    </td>
                    <td><span className={`badge badge-${t.type?.toLowerCase()}`}>{t.type}</span></td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-2)' }}>{fmtINR2(t.entryPrice)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: priceUp ? '#00FF88' : '#FF3B6B' }}>{t.currentPrice ? fmtINR2(t.currentPrice) : '—'}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: '#FF3B6B' }}>{fmtINR2(t.stopLoss)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: '#00FF88' }}>{fmtINR2(t.target1)}</td>
                    <td style={{ color: 'var(--text-2)' }}>{t.positionSize}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-2)' }}>{fmtINR(t.capitalRequired)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: pnlPos ? '#00FF88' : '#FF3B6B' }}>
                      {t.unrealizedPnl != null ? `${pnlPos ? '↑ +' : '↓ '}${fmtINR2(t.unrealizedPnl)}` : '—'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: pnlPos ? '#00FF88' : '#FF3B6B' }}>
                      {t.unrealizedPct != null ? fmtPct(t.unrealizedPct) : '—'}
                    </td>
                    <td>
                      <span className={`badge badge-${t.confidence?.toLowerCase()}`}>{t.confidence}</span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}


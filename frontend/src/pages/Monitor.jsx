import { useEffect, useState } from 'react'
import { getHealth, getErrors, getMarketStatus } from '../api'

function StatusCard({ label, ok, value, detail, color }) {
  const c = color || (ok ? '#00FF88' : '#FF3B6B')
  return (
    <div style={{
      background: 'var(--surface)', borderRadius: 10, border: '1px solid var(--border)',
      borderLeft: `2px solid ${c}`, padding: '16px 18px',
      boxShadow: `0 4px 16px rgba(0,0,0,0.4), -3px 0 16px ${c}30`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <p style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.09em' }}>{label}</p>
        <div style={{
          width: 8, height: 8, borderRadius: '50%', background: c,
          boxShadow: ok ? `0 0 8px ${c}` : 'none',
        }} className={ok ? 'pulse-dot' : ''} />
      </div>
      <p style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)', color: c }}>{value}</p>
      {detail && <p style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 5 }}>{detail}</p>}
    </div>
  )
}

function Row({ label, value, valueColor }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: 12, color: 'var(--text-2)' }}>{label}</span>
      <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: valueColor || 'var(--text-1)' }}>{value || '—'}</span>
    </div>
  )
}

export default function Monitor() {
  const [health, setHealth] = useState(null)
  const [errors, setErrors] = useState([])
  const [market, setMarket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(null)

  const load = () => {
    Promise.all([getHealth(), getErrors(), getMarketStatus()]).then(([h, e, m]) => {
      setHealth(h.data); setErrors(e.data.errors); setMarket(m.data)
      setLastRefresh(new Date())
    }).finally(() => setLoading(false))
  }

  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t) }, [])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 280 }}>
      <div className="spin" style={{ width: 20, height: 20, border: '2px solid var(--border)', borderTopColor: 'var(--cyan)', borderRadius: '50%' }} />
    </div>
  )

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
        <div>
          <p style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>System</p>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.03em' }}>Monitor</h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {lastRefresh && (
            <span style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
              Updated {lastRefresh.toLocaleTimeString('en-IN')}
            </span>
          )}
          <button className="btn-ghost" onClick={load} style={{ padding: '7px 14px' }}>↻ Refresh</button>
        </div>
      </div>

      {/* Status cards grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <StatusCard label="API Server"     ok={health?.status === 'ok'}  value={health?.status === 'ok' ? 'Running' : 'Down'} color={health?.status === 'ok' ? '#00FF88' : '#FF3B6B'} />
        <StatusCard label="Upstox Token"   ok={health?.tokenValid}         value={health?.tokenValid ? 'Valid' : 'Expired'} />
        <StatusCard label="Market Status"  ok={market?.isOpen}             value={market?.isOpen ? 'Open' : 'Closed'} />
        <StatusCard label="Active Trades"  ok={(health?.activeTrades ?? 0) > 0}  value={String(health?.activeTrades ?? 0)} color="#00D4FF" ok={true} detail="open positions" />
        <StatusCard label="Last Scan"      ok={!!health?.lastScanTime}     value={health?.lastScanTime || 'Never'} color="#FFB800" ok={true} />
        <StatusCard label="Telegram Bot"   ok={true}                        value="Active" color="#7B6FFF" detail="notifications enabled" />
      </div>

      {/* Detailed info grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {/* System health detail */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '18px 20px' }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)', marginBottom: 4 }}>System Health</p>
          <p style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 14 }}>Live backend status</p>
          <Row label="API Server"     value={health?.status === 'ok' ? 'Running on :8000' : 'Down'} valueColor={health?.status === 'ok' ? '#00FF88' : '#FF3B6B'} />
          <Row label="Upstox Token"   value={health?.tokenValid ? 'Valid' : 'Expired / Missing'} valueColor={health?.tokenValid ? '#00FF88' : '#FF3B6B'} />
          <Row label="Active Trades"  value={health?.activeTrades} valueColor="#00D4FF" />
          <Row label="Last Scan"      value={health?.lastScanTime || 'Not yet run'} valueColor="#FFB800" />
          <Row label="Checked At"     value={health?.timestamp ? new Date(health.timestamp).toLocaleTimeString('en-IN') : '—'} />
        </div>

        {/* Market status detail */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '18px 20px' }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)', marginBottom: 4 }}>Market Hours</p>
          <p style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 14 }}>NSE · BSE · MCX</p>
          <Row label="Status"         value={market?.isOpen ? 'OPEN' : 'CLOSED'} valueColor={market?.isOpen ? '#00FF88' : '#FF3B6B'} />
          <Row label="Current Time"   value={market?.currentTime} />
          <Row label="Date"           value={market?.currentDate} />
          {market?.nextOpen  && <Row label="Next Open"  value={new Date(market.nextOpen).toLocaleString('en-IN')} valueColor="#00FF88" />}
          {market?.nextClose && <Row label="Closes At"  value="15:30 IST" valueColor="#FF3B6B" />}
          <Row label="Market Hours"   value="09:15 – 15:30 IST" />
        </div>
      </div>

      {/* Error log */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)' }}>Error Log</p>
            <p style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 2 }}>Last {errors.length} recorded errors</p>
          </div>
          {errors.length > 0 && (
            <span style={{ fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 4, background: 'rgba(255,59,107,0.1)', color: '#FF3B6B', border: '1px solid rgba(255,59,107,0.2)' }}>
              {errors.length} error{errors.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {errors.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '48px 0', gap: 10 }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#00FF88" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <p style={{ fontSize: 13, color: 'var(--text-3)' }}>No errors logged — system is clean</p>
          </div>
        ) : (
          <div style={{ maxHeight: 360, overflowY: 'auto', padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {errors.map((e, i) => (
              <div key={i} style={{ background: 'rgba(255,59,107,0.04)', border: '1px solid rgba(255,59,107,0.12)', borderRadius: 7, padding: '12px 14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 3, background: 'rgba(255,184,0,0.12)', color: '#FFB800', border: '1px solid rgba(255,184,0,0.2)' }}>{e.module}</span>
                    {e.symbol && <span style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>[{e.symbol}]</span>}
                  </div>
                  <span style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                    {e.timestamp ? new Date(e.timestamp).toLocaleString('en-IN') : ''}
                  </span>
                </div>
                <p style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.5, wordBreak: 'break-all' }}>{e.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <p style={{ fontSize: 11, color: 'var(--text-3)', textAlign: 'center' }}>Auto-refreshes every 30 seconds</p>
    </div>
  )
}


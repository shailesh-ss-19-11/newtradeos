import { useEffect, useState, useRef } from 'react'
import { getTrades, closeTrade, exportTradesCsv } from '../api'

// Sound alert utility
function playSignalSound() {
  if (localStorage.getItem('tradeos-sound') === 'off') return
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain); gain.connect(ctx.destination)
    osc.frequency.setValueAtTime(880, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.2)
    gain.gain.setValueAtTime(0.3, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3)
    osc.start(); osc.stop(ctx.currentTime + 0.3)
  } catch {}
}

const fmtINR2 = v => v == null ? '—' : `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
const fmtTime = iso => { try { if (!iso) return ''; const t = new Date(iso); return isNaN(t) ? '' : t.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) } catch { return '' } }

function TypeBadge({ type }) {
  return <span className={`badge badge-${type?.toLowerCase()}`}>{type}</span>
}

function StatusBadge({ status, profitLoss }) {
  if (status === 'ACTIVE') return <span className="badge badge-active">ACTIVE</span>
  if (status === 'CLOSED' && profitLoss != null) {
    return profitLoss >= 0
      ? <span className="badge badge-profit">PROFIT</span>
      : <span className="badge badge-loss">LOSS</span>
  }
  return <span className="badge badge-closed">CLOSED</span>
}

function ConfBadge({ conf }) {
  if (!conf) return null
  return <span className={`badge badge-${conf.toLowerCase()}`}>{conf}</span>
}

function TargetMilestones({ t1, t2, t3, t1Hit, t2Hit, t3Hit, hitLog }) {
  const hitTimeFor = n => {
    if (!hitLog) return null
    const entry = (Array.isArray(hitLog) ? hitLog : []).find(e => e.target === n)
    return entry ? fmtTime(entry.time) : null
  }
  const row = (label, price, hit) => {
    if (!price || typeof price !== 'number' || !Number.isFinite(price)) return null
    const t = hitTimeFor(parseInt(label.replace('T', '')))
    return (
      <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 5, lineHeight: 1.6 }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
          background: hit ? '#00FF88' : 'var(--border)',
          boxShadow: hit ? '0 0 5px #00FF8877' : 'none',
        }} />
        <span style={{ fontSize: 10, color: 'var(--text-3)', fontWeight: 600, minWidth: 16 }}>{label}</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: hit ? '#00FF88' : 'var(--text-2)' }}>
          {fmtINR2(price)}
        </span>
        {hit && t && <span style={{ fontSize: 9, color: 'var(--text-3)', marginLeft: 2 }}>{t}</span>}
      </span>
    )
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {row('T1', t1, t1Hit)}
      {row('T2', t2, t2Hit)}
      {row('T3', t3, t3Hit)}
    </div>
  )
}

export default function Trades() {
  const [trades, setTrades]     = useState([])
  const [total, setTotal]       = useState(0)
  const [page, setPage]         = useState(1)
  const [pages, setPages]       = useState(1)
  const [loading, setLoading]   = useState(true)
  const [status, setStatus]     = useState('ALL')
  const [symbol, setSymbol]     = useState('')
  const [fromDate, setFrom]     = useState('')
  const [toDate, setTo]         = useState('')
  const [expanded, setExpanded] = useState(null)
  const [selected, setSelected] = useState(null)
  const [exitPrice, setExit]    = useState('')
  const [closing, setClosing]   = useState(false)
  const prevActiveIds = useRef(new Set())

  const load = () => {
    setLoading(true)
    getTrades({ status, symbol, from_date: fromDate, to_date: toDate, page, per_page: 20 })
      .then(r => {
        const incoming = r.data.trades
        setTrades(incoming)
        setTotal(r.data.pagination.total)
        setPages(r.data.pagination.totalPages)
        // Sound alert: play if a new ACTIVE trade appeared
        const newActiveIds = new Set(incoming.filter(t => t.status === 'ACTIVE').map(t => t.tradeId))
        const hasNew = [...newActiveIds].some(id => !prevActiveIds.current.has(id))
        if (hasNew && prevActiveIds.current.size > 0) playSignalSound()
        prevActiveIds.current = newActiveIds
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [status, page])

  const handleClose = async () => {
    if (!exitPrice || !selected) return
    setClosing(true)
    await closeTrade(selected.tradeId, { exitPrice: parseFloat(exitPrice), exitReason: 'MANUAL_CLOSE' })
    setSelected(null); setExit(''); setClosing(false); load()
  }

  return (
    <div className="fade-up" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ marginBottom: 4 }}>
        <p style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Records</p>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.03em' }}>Trades</h1>
          <p style={{ fontSize: 13, color: 'var(--text-2)' }}>{total} total records</p>
        </div>
      </div>

      {/* Filter bar */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 20px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end' }}>
          <div>
            <label style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em', display: 'block', marginBottom: 6 }}>Status</label>
            <select className="form-select" value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}>
              <option value="ALL">All</option>
              <option value="ACTIVE">Active</option>
              <option value="CLOSED">Closed</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em', display: 'block', marginBottom: 6 }}>Symbol</label>
            <input className="form-input" value={symbol} onChange={e => setSymbol(e.target.value)} placeholder="e.g. RELIANCE" style={{ width: 140 }} />
          </div>
          <div>
            <label style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em', display: 'block', marginBottom: 6 }}>From</label>
            <input type="date" className="form-input" value={fromDate} onChange={e => setFrom(e.target.value)} style={{ width: 148 }} />
          </div>
          <div>
            <label style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em', display: 'block', marginBottom: 6 }}>To</label>
            <input type="date" className="form-input" value={toDate} onChange={e => setTo(e.target.value)} style={{ width: 148 }} />
          </div>
          <button className="btn-primary" onClick={() => { setPage(1); load() }}>Search</button>
          <button className="btn-ghost" onClick={() => { setStatus('ALL'); setSymbol(''); setFrom(''); setTo(''); setPage(1); }}>Clear</button>
          <button className="btn-ghost" onClick={() => exportTradesCsv({ status, symbol, from_date: fromDate, to_date: toDate })}
            style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Export CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th><th>Type</th><th>Status</th>
                <th>Entry</th><th>Stop Loss</th><th>Targets</th><th>Exit</th>
                <th>P&amp;L</th><th>Votes</th><th>Conf</th><th>Date</th><th></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={12} style={{ textAlign: 'center', padding: 60 }}>
                  <div className="spin" style={{ width: 20, height: 20, border: '2px solid var(--border)', borderTopColor: 'var(--cyan)', borderRadius: '50%', margin: '0 auto' }} />
                </td></tr>
              ) : trades.length === 0 ? (
                <tr><td colSpan={12} style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-3)' }}>No trades found</td></tr>
              ) : trades.map(t => (
                <>
                  <tr key={t.tradeId} onClick={() => setExpanded(expanded === t.tradeId ? null : t.tradeId)} style={{ cursor: 'pointer' }}>
                    <td>
                      <span style={{ fontWeight: 600, color: 'var(--text-1)' }}>{t.displaySymbol}</span>
                      <span style={{ fontSize: 9, marginLeft: 5, padding: '1px 4px', borderRadius: 3, background: 'var(--surface-hi)', color: 'var(--text-3)', border: '1px solid var(--border)' }}>
                        {t.symbol?.split(':')[0] || 'NSE'}
                      </span>
                    </td>
                    <td><TypeBadge type={t.type} /></td>
                    <td><StatusBadge status={t.status} profitLoss={t.profitLoss} /></td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-2)' }}>{fmtINR2(t.entryPrice)}</td>
                    <td>
                      <span style={{ fontFamily: 'var(--font-mono)', color: '#FF3B6B' }}>{fmtINR2(t.stopLoss)}</span>
                      {t.exitReason === 'STOP_LOSS_HIT' && (
                        <span style={{ marginLeft: 5, fontSize: 9, fontWeight: 700, color: '#FF3B6B', background: 'rgba(255,59,107,0.12)', border: '1px solid rgba(255,59,107,0.35)', borderRadius: 3, padding: '1px 4px' }}>HIT</span>
                      )}
                    </td>
                    <td><TargetMilestones t1={t.target1} t2={t.target2} t3={t.target3} t1Hit={t.target1Hit} t2Hit={t.target2Hit} t3Hit={t.target3Hit} hitLog={t.targetHitLog} /></td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-2)' }}>{fmtINR2(t.exitPrice)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: t.profitLoss == null ? 'var(--text-3)' : t.profitLoss >= 0 ? '#00FF88' : '#FF3B6B' }}>
                      {t.profitLoss == null ? '—' : `${t.profitLoss >= 0 ? '↑ +' : '↓ '}${fmtINR2(t.profitLoss)}`}
                    </td>
                    <td style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>{t.votes ?? '—'}/8</td>
                    <td><ConfBadge conf={t.confidence} /></td>
                    <td style={{ color: 'var(--text-3)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>{t.date}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <span style={{ fontSize: 10, color: 'var(--text-3)' }}>{expanded === t.tradeId ? '▲' : '▼'}</span>
                        {t.status === 'ACTIVE' && (
                          <button className="btn-ghost" style={{ padding: '3px 10px', fontSize: 11 }}
                            onClick={e => { e.stopPropagation(); setSelected(t) }}>
                            Close
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {/* Expanded row — strategy breakdown */}
                  {expanded === t.tradeId && (
                    <tr key={`${t.tradeId}-exp`} style={{ background: 'var(--surface-hi)' }}>
                      <td colSpan={12} style={{ padding: '14px 18px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 }}>
                          {[
                            { k: 'Strategy',      v: t.strategy },
                            { k: 'Position Size', v: t.positionSize },
                            { k: 'Capital',       v: fmtINR2(t.capitalRequired) },
                            { k: 'Exit Reason',   v: t.exitReason },
                            { k: 'Trade ID',      v: t.tradeId },
                          ].map(r => r.v && (
                            <div key={r.k}>
                              <p style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 3 }}>{r.k}</p>
                              <p style={{ fontSize: 12, color: 'var(--text-2)', fontFamily: r.k === 'Trade ID' ? 'var(--font-mono)' : 'inherit' }}>{r.v}</p>
                            </div>
                          ))}

                          {/* Target milestone hit log */}
                          <div>
                            <p style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>Milestones</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                              {[
                                { label: 'SL',  price: t.stopLoss,  hit: t.exitReason === 'STOP_LOSS_HIT', hitColor: '#FF3B6B', time: t.exitReason === 'STOP_LOSS_HIT' ? fmtTime(t.exitTime) : null },
                                { label: 'T1',  price: t.target1,   hit: t.target1Hit, hitColor: '#00FF88', time: (Array.isArray(t.targetHitLog) ? t.targetHitLog : []).find(e => e.target === 1)?.time },
                                { label: 'T2',  price: t.target2,   hit: t.target2Hit, hitColor: '#00FF88', time: (Array.isArray(t.targetHitLog) ? t.targetHitLog : []).find(e => e.target === 2)?.time },
                                { label: 'T3',  price: t.target3,   hit: t.target3Hit, hitColor: '#00FF88', time: (Array.isArray(t.targetHitLog) ? t.targetHitLog : []).find(e => e.target === 3)?.time },
                              ].filter(m => m.price).map(m => (
                                <span key={m.label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                                  <span style={{ width: 7, height: 7, borderRadius: '50%', flexShrink: 0, background: m.hit ? m.hitColor : 'var(--border)', boxShadow: m.hit ? `0 0 5px ${m.hitColor}77` : 'none' }} />
                                  <span style={{ color: 'var(--text-3)', fontWeight: 600, minWidth: 20 }}>{m.label}</span>
                                  <span style={{ fontFamily: 'var(--font-mono)', color: m.hit ? m.hitColor : 'var(--text-2)' }}>{fmtINR2(m.price)}</span>
                                  {m.hit && m.time && <span style={{ fontSize: 9, color: 'var(--text-3)' }}>@ {fmtTime(m.time)}</span>}
                                  {!m.hit && <span style={{ fontSize: 9, color: 'var(--text-3)' }}>pending</span>}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>

        {pages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
            <span style={{ fontSize: 12, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>Page {page} / {pages} · {total} records</span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn-ghost" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ padding: '6px 12px', fontSize: 12 }}>← Prev</button>
              <button className="btn-ghost" onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page === pages} style={{ padding: '6px 12px', fontSize: 12 }}>Next →</button>
            </div>
          </div>
        )}
      </div>

      {/* Close modal */}
      {selected && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}
          onClick={e => e.target === e.currentTarget && setSelected(null)}>
          <div className="fade-up" style={{ background: 'var(--surface)', borderRadius: 12, border: '1px solid var(--border-hi)', padding: '28px 28px', width: 380, boxShadow: '0 24px 64px rgba(0,0,0,0.7)' }}>
            <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-1)', marginBottom: 6 }}>Close Position</p>
            <p style={{ fontSize: 13, color: 'var(--text-2)', marginBottom: 22 }}>
              <span style={{ fontWeight: 600 }}>{selected.displaySymbol}</span>
              {' · '}<TypeBadge type={selected.type} />
              {' · Entry '}<span style={{ fontFamily: 'var(--font-mono)' }}>{fmtINR2(selected.entryPrice)}</span>
            </p>
            <label style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em', display: 'block', marginBottom: 8 }}>Exit Price (₹)</label>
            <input type="number" className="form-input" value={exitPrice} onChange={e => setExit(e.target.value)}
              placeholder={String(selected.entryPrice)} autoFocus style={{ fontSize: 16, padding: '10px 14px', marginBottom: 22 }} />
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn-primary" onClick={handleClose} disabled={closing || !exitPrice} style={{ flex: 1, padding: 12 }}>
                {closing ? 'Closing…' : 'Confirm Close'}
              </button>
              <button className="btn-ghost" onClick={() => setSelected(null)} style={{ flex: 1, padding: 12 }}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


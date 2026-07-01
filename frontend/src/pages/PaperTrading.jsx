import { useState, useEffect } from 'react'
import { getPaperPortfolio, openPaperTrade, closePaperTrade, resetPaperPortfolio } from '../api'

const fmt  = n => (n ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })
const fmtP = n => `${n >= 0 ? '+' : ''}${(n ?? 0).toFixed(2)}%`

export default function PaperTrading() {
  const [portfolio, setPortfolio]   = useState(null)
  const [positions, setPositions]   = useState([])
  const [history,   setHistory]     = useState([])
  const [loading,   setLoading]     = useState(true)
  const [showNew,   setShowNew]     = useState(false)
  const [closeModal,setCloseModal]  = useState(null)
  const [exitPrice, setExitPrice]   = useState('')
  const [tab,       setTab]         = useState('open')
  const [saving,    setSaving]      = useState(false)
  const [error,     setError]       = useState('')

  const defaultForm = { symbol: '', quantity: '', entryPrice: '', slPct: 2, t1Pct: 3, t2Pct: 5, t3Pct: 7, strategyName: '', notes: '' }
  const [form, setForm] = useState(defaultForm)

  const load = async () => {
    setLoading(true)
    try {
      const r = await getPaperPortfolio()
      setPortfolio(r.data.portfolio)
      setPositions(r.data.positions || [])
      setHistory(r.data.history || [])
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleOpenTrade = async () => {
    setError('')
    if (!form.symbol || !form.entryPrice || !form.quantity) return setError('Symbol, price and quantity are required')
    setSaving(true)
    try {
      await openPaperTrade({ ...form, entryPrice: Number(form.entryPrice), quantity: Number(form.quantity) })
      setShowNew(false)
      setForm(defaultForm)
      await load()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to open trade')
    }
    setSaving(false)
  }

  const handleClose = async () => {
    if (!exitPrice) return
    try {
      await closePaperTrade(closeModal.id, { exitPrice: Number(exitPrice), exitType: 'MANUAL' })
      setCloseModal(null)
      setExitPrice('')
      await load()
    } catch {}
  }

  const handleReset = async () => {
    if (!confirm('Reset portfolio? All open positions will be closed.')) return
    await resetPaperPortfolio()
    await load()
  }

  const totalPnL  = positions.reduce((s, p) => s + (p.pnl || 0), 0)
  const closedPnL = history.reduce((s, p) => s + (p.pnl || 0), 0)

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>Paper Trading</h1>
          <p style={{ fontSize: 13, color: 'var(--text-2)' }}>Practice trading with virtual capital — no real money involved</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={handleReset} style={{ ...btn, background: 'var(--surface-hi)', color: 'var(--text-2)' }}>Reset</button>
          <button onClick={() => setShowNew(true)} style={btn}>+ New Trade</button>
        </div>
      </div>

      {/* Portfolio summary */}
      {portfolio && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
          {[
            { label: 'Initial Capital', value: `₹${fmt(portfolio.initialCapital)}`, color: null },
            { label: 'Available Capital', value: `₹${fmt(portfolio.availableCapital)}`, color: null },
            { label: 'Open P&L', value: `₹${fmt(totalPnL)}`, color: totalPnL >= 0 ? 'var(--emerald)' : 'var(--rose)' },
            { label: 'Closed P&L', value: `₹${fmt(closedPnL)}`, color: closedPnL >= 0 ? 'var(--emerald)' : 'var(--rose)' },
          ].map(s => (
            <div key={s.label} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
              <p style={{ fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>{s.label}</p>
              <p style={{ fontSize: 20, fontWeight: 700, color: s.color || 'var(--text-1)' }}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid var(--border)', paddingBottom: 8 }}>
        {[['open', `Open (${positions.length})`], ['history', `History (${history.length})`]].map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} style={{
            padding: '7px 16px', borderRadius: '8px 8px 0 0', cursor: 'pointer',
            border: 'none', background: tab === key ? 'var(--cyan-15)' : 'transparent',
            color: tab === key ? 'var(--cyan)' : 'var(--text-2)',
            fontSize: 13, fontWeight: tab === key ? 700 : 400,
            borderBottom: tab === key ? '2px solid var(--cyan)' : '2px solid transparent',
          }}>
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-2)', fontSize: 13 }}>Loading...</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--surface)' }}>
                {(tab === 'open'
                  ? ['Symbol', 'Entry ₹', 'Qty', 'Last ₹', 'P&L', 'P&L%', 'SL%', 'T1%', 'Strategy', 'Opened', '']
                  : ['Symbol', 'Entry ₹', 'Exit ₹', 'Qty', 'P&L', 'P&L%', 'Exit Type', 'Closed']
                ).map(h => <th key={h} style={thStyle}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {(tab === 'open' ? positions : history).map(t => (
                <tr key={t.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={tdStyle}><span style={{ fontWeight: 700, color: 'var(--text-1)' }}>{t.symbol}</span></td>
                  <td style={tdStyle}>₹{fmt(t.entryPrice)}</td>
                  {tab === 'history' && <td style={tdStyle}>₹{fmt(t.exitPrice)}</td>}
                  <td style={tdStyle}>{t.quantity}</td>
                  {tab === 'open' && <td style={tdStyle}>₹{fmt(t.lastPrice)}</td>}
                  <td style={{ ...tdStyle, color: t.pnl >= 0 ? 'var(--emerald)' : 'var(--rose)', fontWeight: 700 }}>
                    {t.pnl >= 0 ? '+' : ''}₹{fmt(t.pnl)}
                  </td>
                  <td style={{ ...tdStyle, color: t.pnlPct >= 0 ? 'var(--emerald)' : 'var(--rose)' }}>{fmtP(t.pnlPct)}</td>
                  {tab === 'open' && <>
                    <td style={tdStyle}>{t.slPct}%</td>
                    <td style={tdStyle}>{t.t1Pct}%</td>
                    <td style={tdStyle}><span style={{ fontSize: 11, color: 'var(--text-3)' }}>{t.strategyName || '—'}</span></td>
                    <td style={tdStyle}>{new Date(t.openedAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}</td>
                    <td style={tdStyle}>
                      <button onClick={() => { setCloseModal(t); setExitPrice(String(t.lastPrice)) }}
                        style={{ padding: '4px 10px', borderRadius: 6, background: 'var(--rose-15)', border: '1px solid var(--rose)', color: 'var(--rose)', fontSize: 11, cursor: 'pointer' }}>
                        Close
                      </button>
                    </td>
                  </>}
                  {tab === 'history' && <>
                    <td style={tdStyle}><span style={{ fontSize: 11, color: 'var(--text-3)' }}>{t.exitType || 'MANUAL'}</span></td>
                    <td style={tdStyle}>{t.closedAt ? new Date(t.closedAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '—'}</td>
                  </>}
                </tr>
              ))}
              {(tab === 'open' ? positions : history).length === 0 && (
                <tr><td colSpan={10} style={{ textAlign: 'center', padding: 40, color: 'var(--text-3)', fontSize: 13 }}>
                  {tab === 'open' ? 'No open positions' : 'No closed trades yet'}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* New Trade Modal */}
      {showNew && (
        <div style={overlay} onClick={e => e.target === e.currentTarget && setShowNew(false)}>
          <div style={modal}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
              <h2 style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-1)' }}>New Paper Trade</h2>
              <button onClick={() => setShowNew(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-2)' }}>✕</button>
            </div>
            {error && <div style={errorBox}>{error}</div>}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              {[
                { key: 'symbol', label: 'Symbol', placeholder: 'e.g. RELIANCE' },
                { key: 'quantity', label: 'Quantity', placeholder: '10', type: 'number' },
                { key: 'entryPrice', label: 'Entry Price (₹)', placeholder: '2500', type: 'number' },
                { key: 'slPct', label: 'SL %', placeholder: '2', type: 'number' },
                { key: 't1Pct', label: 'T1 % gain', placeholder: '3', type: 'number' },
                { key: 't2Pct', label: 'T2 % gain', placeholder: '5', type: 'number' },
                { key: 't3Pct', label: 'T3 % gain', placeholder: '7', type: 'number' },
                { key: 'strategyName', label: 'Strategy Name', placeholder: 'EMA Cross (optional)' },
              ].map(f => (
                <div key={f.key}>
                  <label style={labelStyle}>{f.label}</label>
                  <input type={f.type || 'text'} value={form[f.key]}
                    onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                    placeholder={f.placeholder} style={inputStyle} />
                </div>
              ))}
            </div>
            <div style={{ marginTop: 14 }}>
              <label style={labelStyle}>Notes</label>
              <textarea value={form.notes} onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
                rows={2} placeholder="Trade rationale..." style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }} />
            </div>
            <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
              <button onClick={() => setShowNew(false)} style={cancelBtn}>Cancel</button>
              <button onClick={handleOpenTrade} disabled={saving} style={{ ...btn, flex: 1, justifyContent: 'center', opacity: saving ? 0.7 : 1 }}>
                {saving ? 'Opening...' : 'Open Trade'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Close Trade Modal */}
      {closeModal && (
        <div style={overlay} onClick={e => e.target === e.currentTarget && setCloseModal(null)}>
          <div style={{ ...modal, maxWidth: 360 }}>
            <h2 style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-1)', marginBottom: 16 }}>
              Close {closeModal.symbol}
            </h2>
            <label style={labelStyle}>Exit Price (₹)</label>
            <input type="number" value={exitPrice} onChange={e => setExitPrice(e.target.value)}
              style={{ ...inputStyle, marginBottom: 16 }} />
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setCloseModal(null)} style={cancelBtn}>Cancel</button>
              <button onClick={handleClose} style={{ ...btn, flex: 1, justifyContent: 'center', background: 'var(--rose)' }}>
                Close Position
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const btn       = { display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', borderRadius: 8, cursor: 'pointer', background: 'var(--cyan)', border: 'none', color: '#fff', fontSize: 13, fontWeight: 700 }
const overlay   = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20 }
const modal     = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: '24px', width: '100%', maxWidth: 560, maxHeight: '90vh', overflowY: 'auto' }
const cancelBtn = { flex: 1, padding: '10px 0', borderRadius: 8, cursor: 'pointer', background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-2)', fontSize: 13 }
const errorBox  = { padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, color: 'var(--rose)', fontSize: 13, marginBottom: 16 }
const labelStyle= { display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-2)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.06em' }
const inputStyle= { width: '100%', padding: '9px 12px', borderRadius: 8, background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-1)', fontSize: 13, outline: 'none', boxSizing: 'border-box' }
const thStyle   = { padding: '10px 14px', borderBottom: '2px solid var(--border)', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em' }
const tdStyle   = { padding: '10px 14px', borderBottom: '1px solid var(--border)', color: 'var(--text-2)', fontSize: 13 }

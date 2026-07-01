import { useState, useEffect } from 'react'
import { getJournalEntries, createJournalEntry, updateJournalEntry, deleteJournalEntry } from '../api'

const RATINGS = [1, 2, 3, 4, 5]
const OUTCOMES = ['profit', 'loss', 'breakeven']

function Stars({ value, onChange, readonly }) {
  return (
    <div style={{ display: 'flex', gap: 2 }}>
      {RATINGS.map(r => (
        <span key={r} onClick={() => !readonly && onChange(r)}
          style={{ fontSize: 16, cursor: readonly ? 'default' : 'pointer', color: r <= value ? 'var(--amber)' : 'var(--border)' }}>
          ★
        </span>
      ))}
    </div>
  )
}

const emptyForm = { symbol: '', date: new Date().toISOString().split('T')[0], entryPrice: '', exitPrice: '', quantity: '', outcome: 'profit', pnl: '', setupDescription: '', lessonsLearned: '', emotionalState: '', tags: '', rating: 3 }

export default function Journal() {
  const [entries, setEntries]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [filter,  setFilter]    = useState({ symbol: '', rating: '', outcome: '' })
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing]   = useState(null)
  const [form,    setForm]      = useState(emptyForm)
  const [saving,  setSaving]    = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filter.symbol)  params.symbol  = filter.symbol
      if (filter.rating)  params.rating  = filter.rating
      if (filter.outcome) params.outcome = filter.outcome
      const r = await getJournalEntries(params)
      setEntries(r.data.entries || [])
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [filter])

  const openNew = () => {
    setEditing(null)
    setForm(emptyForm)
    setShowModal(true)
  }

  const openEdit = (e) => {
    setEditing(e.id)
    setForm({
      symbol: e.symbol, date: e.tradeDate?.split('T')[0] || '',
      entryPrice: e.entryPrice || '', exitPrice: e.exitPrice || '',
      quantity: e.quantity || '', outcome: e.outcome || 'profit',
      pnl: e.pnl || '', setupDescription: e.setupDescription || '',
      lessonsLearned: e.lessonsLearned || '', emotionalState: e.emotionalState || '',
      tags: (e.tags || []).join(', '), rating: e.rating || 3,
    })
    setShowModal(true)
  }

  const handleSave = async () => {
    if (!form.symbol || !form.date) return
    setSaving(true)
    const payload = {
      ...form,
      entryPrice: form.entryPrice ? Number(form.entryPrice) : null,
      exitPrice:  form.exitPrice  ? Number(form.exitPrice)  : null,
      quantity:   form.quantity   ? Number(form.quantity)   : null,
      pnl:        form.pnl        ? Number(form.pnl)        : null,
      tags:       form.tags ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
    }
    try {
      if (editing) await updateJournalEntry(editing, payload)
      else         await createJournalEntry(payload)
      setShowModal(false)
      load()
    } catch {}
    setSaving(false)
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this journal entry?')) return
    await deleteJournalEntry(id)
    setEntries(e => e.filter(x => x.id !== id))
  }

  const pnlSum = entries.reduce((s, e) => s + (e.pnl || 0), 0)
  const wins   = entries.filter(e => e.outcome === 'profit').length
  const losses = entries.filter(e => e.outcome === 'loss').length

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>Trade Journal</h1>
          <p style={{ fontSize: 13, color: 'var(--text-2)' }}>Log every trade, review your decisions, learn from patterns</p>
        </div>
        <button onClick={openNew} style={btn}>+ Log Trade</button>
      </div>

      {/* Summary stats */}
      {entries.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
          {[
            { label: 'Total Trades', value: entries.length, color: null },
            { label: 'Wins', value: wins, color: 'var(--emerald)' },
            { label: 'Losses', value: losses, color: 'var(--rose)' },
            { label: 'Net P&L', value: `${pnlSum >= 0 ? '+' : ''}₹${pnlSum.toLocaleString('en-IN')}`, color: pnlSum >= 0 ? 'var(--emerald)' : 'var(--rose)' },
          ].map(s => (
            <div key={s.label} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 16px' }}>
              <p style={{ fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{s.label}</p>
              <p style={{ fontSize: 20, fontWeight: 700, color: s.color || 'var(--text-1)' }}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
        <input value={filter.symbol} onChange={e => setFilter(f => ({ ...f, symbol: e.target.value }))}
          placeholder="Filter by symbol..." style={{ ...inp, maxWidth: 200 }} />
        <select value={filter.outcome} onChange={e => setFilter(f => ({ ...f, outcome: e.target.value }))} style={{ ...inp, maxWidth: 160 }}>
          <option value="">All outcomes</option>
          {OUTCOMES.map(o => <option key={o} value={o} style={{ textTransform: 'capitalize' }}>{o}</option>)}
        </select>
        <select value={filter.rating} onChange={e => setFilter(f => ({ ...f, rating: e.target.value }))} style={{ ...inp, maxWidth: 160 }}>
          <option value="">All ratings</option>
          {RATINGS.map(r => <option key={r} value={r}>{r} Star{r > 1 ? 's' : ''}</option>)}
        </select>
        {(filter.symbol || filter.outcome || filter.rating) && (
          <button onClick={() => setFilter({ symbol: '', rating: '', outcome: '' })} style={{ ...inp, maxWidth: 80, cursor: 'pointer', color: 'var(--rose)', border: '1px solid var(--rose)' }}>
            Clear
          </button>
        )}
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-2)', fontSize: 13 }}>Loading...</p>
      ) : entries.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-3)' }}>
          <p style={{ fontSize: 15, marginBottom: 8 }}>No journal entries yet</p>
          <button onClick={openNew} style={btn}>Log your first trade</button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {entries.map(e => (
            <div key={e.id} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px 20px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)' }}>{e.symbol}</span>
                    <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10, textTransform: 'capitalize',
                      background: e.outcome === 'profit' ? 'var(--emerald-15)' : e.outcome === 'loss' ? 'var(--rose-15)' : 'var(--surface-hi)',
                      color: e.outcome === 'profit' ? 'var(--emerald)' : e.outcome === 'loss' ? 'var(--rose)' : 'var(--text-2)' }}>
                      {e.outcome}
                    </span>
                    {e.pnl != null && (
                      <span style={{ fontSize: 13, fontWeight: 700, color: e.pnl >= 0 ? 'var(--emerald)' : 'var(--rose)' }}>
                        {e.pnl >= 0 ? '+' : ''}₹{Number(e.pnl).toLocaleString('en-IN')}
                      </span>
                    )}
                    <span style={{ fontSize: 11, color: 'var(--text-3)', marginLeft: 'auto' }}>
                      {e.tradeDate ? new Date(e.tradeDate).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' }) : ''}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: e.setupDescription ? 8 : 0 }}>
                    {e.entryPrice && <span style={{ fontSize: 12, color: 'var(--text-3)' }}>Entry: ₹{e.entryPrice}</span>}
                    {e.exitPrice  && <span style={{ fontSize: 12, color: 'var(--text-3)' }}>Exit: ₹{e.exitPrice}</span>}
                    {e.quantity   && <span style={{ fontSize: 12, color: 'var(--text-3)' }}>Qty: {e.quantity}</span>}
                  </div>
                  {e.setupDescription && <p style={{ fontSize: 12, color: 'var(--text-2)', marginBottom: 4, lineHeight: 1.5 }}>{e.setupDescription}</p>}
                  {e.lessonsLearned  && <p style={{ fontSize: 12, color: 'var(--text-2)', fontStyle: 'italic' }}>Lesson: {e.lessonsLearned}</p>}
                  {e.tags?.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
                      {e.tags.map(t => <span key={t} style={{ fontSize: 10, padding: '2px 7px', background: 'var(--cyan-15)', borderRadius: 8, color: 'var(--cyan)' }}>{t}</span>)}
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
                  <Stars value={e.rating || 0} readonly />
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button onClick={() => openEdit(e)} style={iconBtn}>✏</button>
                    <button onClick={() => handleDelete(e.id)} style={{ ...iconBtn, color: 'var(--rose)', borderColor: 'var(--rose)' }}>✕</button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div style={overlay} onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div style={modal}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
              <h2 style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-1)' }}>{editing ? 'Edit' : 'Log'} Trade</h2>
              <button onClick={() => setShowModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-2)' }}>✕</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[
                { key: 'symbol',     label: 'Symbol *',   placeholder: 'RELIANCE' },
                { key: 'date',       label: 'Trade Date *', type: 'date' },
                { key: 'entryPrice', label: 'Entry Price', placeholder: '2500', type: 'number' },
                { key: 'exitPrice',  label: 'Exit Price',  placeholder: '2650', type: 'number' },
                { key: 'quantity',   label: 'Quantity',    placeholder: '10',   type: 'number' },
                { key: 'pnl',        label: 'P&L (₹)',     placeholder: '1500', type: 'number' },
              ].map(f => (
                <div key={f.key}>
                  <label style={lbl}>{f.label}</label>
                  <input type={f.key === 'date' ? 'date' : (f.type || 'text')} value={form[f.key]}
                    onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                    placeholder={f.placeholder} style={inp} />
                </div>
              ))}
            </div>

            <div style={{ marginTop: 12 }}>
              <label style={lbl}>Outcome</label>
              <div style={{ display: 'flex', gap: 8 }}>
                {OUTCOMES.map(o => (
                  <button key={o} onClick={() => setForm(f => ({ ...f, outcome: o }))} style={{
                    flex: 1, padding: '7px 0', borderRadius: 7, cursor: 'pointer', textTransform: 'capitalize',
                    border: form.outcome === o ? '1px solid var(--cyan)' : '1px solid var(--border)',
                    background: form.outcome === o ? 'var(--cyan-15)' : 'var(--surface-hi)',
                    color: form.outcome === o ? 'var(--cyan)' : 'var(--text-2)', fontSize: 12,
                  }}>{o}</button>
                ))}
              </div>
            </div>

            <div style={{ marginTop: 12 }}>
              <label style={lbl}>Rating</label>
              <Stars value={form.rating} onChange={r => setForm(f => ({ ...f, rating: r }))} />
            </div>

            <div style={{ marginTop: 12 }}>
              <label style={lbl}>Setup Description</label>
              <textarea value={form.setupDescription} onChange={e => setForm(f => ({ ...f, setupDescription: e.target.value }))}
                rows={2} placeholder="Describe the setup / reason for entry..." style={{ ...inp, resize: 'vertical', fontFamily: 'inherit' }} />
            </div>

            <div style={{ marginTop: 12 }}>
              <label style={lbl}>Lessons Learned</label>
              <textarea value={form.lessonsLearned} onChange={e => setForm(f => ({ ...f, lessonsLearned: e.target.value }))}
                rows={2} placeholder="What would you do differently?" style={{ ...inp, resize: 'vertical', fontFamily: 'inherit' }} />
            </div>

            <div style={{ marginTop: 12 }}>
              <label style={lbl}>Emotional State</label>
              <input value={form.emotionalState} onChange={e => setForm(f => ({ ...f, emotionalState: e.target.value }))}
                placeholder="calm, anxious, FOMO..." style={inp} />
            </div>

            <div style={{ marginTop: 12, marginBottom: 20 }}>
              <label style={lbl}>Tags (comma separated)</label>
              <input value={form.tags} onChange={e => setForm(f => ({ ...f, tags: e.target.value }))}
                placeholder="breakout, earnings, news..." style={inp} />
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setShowModal(false)} style={cancelBtn}>Cancel</button>
              <button onClick={handleSave} disabled={saving} style={{ ...btn, flex: 1, justifyContent: 'center', opacity: saving ? 0.7 : 1 }}>
                {saving ? 'Saving...' : editing ? 'Save Changes' : 'Log Trade'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const btn       = { display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', borderRadius: 8, cursor: 'pointer', background: 'var(--cyan)', border: 'none', color: '#fff', fontSize: 13, fontWeight: 700 }
const cancelBtn = { flex: 1, padding: '10px 0', borderRadius: 8, cursor: 'pointer', background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-2)', fontSize: 13 }
const iconBtn   = { background: 'var(--surface-hi)', border: '1px solid var(--border)', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', color: 'var(--text-2)', fontSize: 12 }
const overlay   = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20 }
const modal     = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 24, width: '100%', maxWidth: 560, maxHeight: '90vh', overflowY: 'auto' }
const lbl       = { display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-2)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.06em' }
const inp       = { width: '100%', padding: '9px 12px', borderRadius: 8, background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-1)', fontSize: 13, outline: 'none', boxSizing: 'border-box' }

import { useState, useEffect } from 'react'
import { getAlerts, createAlert, deleteAlert, toggleAlert } from '../api'

const CONDITIONS = [
  { value: 'above', label: 'Price goes above', icon: '↑' },
  { value: 'below', label: 'Price goes below',  icon: '↓' },
]

export default function Alerts() {
  const [alerts,  setAlerts]  = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm,setShowForm]= useState(false)
  const [form,    setForm]    = useState({ symbol: '', targetPrice: '', condition: 'above', notes: '' })
  const [saving,  setSaving]  = useState(false)
  const [error,   setError]   = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const r = await getAlerts()
      setAlerts(r.data.alerts || [])
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    setError('')
    if (!form.symbol || !form.targetPrice) return setError('Symbol and target price are required')
    setSaving(true)
    try {
      await createAlert({ ...form, targetPrice: Number(form.targetPrice) })
      setForm({ symbol: '', targetPrice: '', condition: 'above', notes: '' })
      setShowForm(false)
      load()
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to create alert')
    }
    setSaving(false)
  }

  const handleToggle = async (id) => {
    try {
      const r = await toggleAlert(id)
      setAlerts(a => a.map(x => x.id === id ? { ...x, isActive: r.data.isActive } : x))
    } catch {}
  }

  const handleDelete = async (id) => {
    await deleteAlert(id)
    setAlerts(a => a.filter(x => x.id !== id))
  }

  const active   = alerts.filter(a => a.isActive && !a.isTriggered)
  const triggered = alerts.filter(a => a.isTriggered)
  const inactive = alerts.filter(a => !a.isActive && !a.isTriggered)

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>Price Alerts</h1>
          <p style={{ fontSize: 13, color: 'var(--text-2)' }}>Get notified when stocks hit your target prices</p>
        </div>
        <button onClick={() => setShowForm(f => !f)} style={btn}>
          {showForm ? '✕ Cancel' : '+ New Alert'}
        </button>
      </div>

      {/* Create form (inline) */}
      {showForm && (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 20, marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)', marginBottom: 14 }}>Create Price Alert</h3>
          {error && <div style={{ padding: '8px 12px', background: 'var(--rose-15)', border: '1px solid var(--rose)', borderRadius: 8, color: 'var(--rose)', fontSize: 13, marginBottom: 12 }}>{error}</div>}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div>
              <label style={lbl}>Symbol</label>
              <input value={form.symbol} onChange={e => setForm(f => ({ ...f, symbol: e.target.value.toUpperCase() }))}
                placeholder="NIFTY, RELIANCE..." style={inp} />
            </div>
            <div>
              <label style={lbl}>Target Price (₹)</label>
              <input type="number" value={form.targetPrice} onChange={e => setForm(f => ({ ...f, targetPrice: e.target.value }))}
                placeholder="e.g. 2500" style={inp} />
            </div>
            <div>
              <label style={lbl}>Condition</label>
              <select value={form.condition} onChange={e => setForm(f => ({ ...f, condition: e.target.value }))} style={inp}>
                {CONDITIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
          </div>
          <div style={{ marginBottom: 14 }}>
            <label style={lbl}>Notes (optional)</label>
            <input value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              placeholder="Reason for this alert..." style={inp} />
          </div>
          <button onClick={handleCreate} disabled={saving} style={{ ...btn, opacity: saving ? 0.7 : 1 }}>
            {saving ? 'Creating...' : 'Create Alert'}
          </button>
        </div>
      )}

      {loading ? (
        <p style={{ color: 'var(--text-2)', fontSize: 13 }}>Loading...</p>
      ) : alerts.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-3)' }}>
          <p style={{ fontSize: 40, marginBottom: 12 }}>🔔</p>
          <p style={{ fontSize: 15, marginBottom: 8 }}>No price alerts yet</p>
          <p style={{ fontSize: 13, marginBottom: 20 }}>Set alerts to get notified when stocks hit your target price</p>
          <button onClick={() => setShowForm(true)} style={btn}>Create First Alert</button>
        </div>
      ) : (
        <div>
          {[
            { items: active,    title: `Active (${active.length})`,       color: 'var(--emerald)' },
            { items: triggered, title: `Triggered (${triggered.length})`, color: 'var(--amber)'  },
            { items: inactive,  title: `Paused (${inactive.length})`,     color: 'var(--text-3)' },
          ].filter(g => g.items.length > 0).map(group => (
            <div key={group.title} style={{ marginBottom: 24 }}>
              <h3 style={{ fontSize: 12, fontWeight: 700, color: group.color, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>{group.title}</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {group.items.map(a => <AlertRow key={a.id} alert={a} onToggle={handleToggle} onDelete={handleDelete} />)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function AlertRow({ alert: a, onToggle, onDelete }) {
  const cond = CONDITIONS.find(c => c.value === a.condition) || CONDITIONS[0]
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 18px',
      display: 'flex', alignItems: 'center', gap: 14,
      opacity: a.isTriggered ? 0.7 : 1,
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 8, flexShrink: 0,
        background: a.isTriggered ? 'var(--amber-15)' : a.isActive ? 'var(--emerald-15)' : 'var(--surface-hi)',
        border: `1px solid ${a.isTriggered ? 'var(--amber)' : a.isActive ? 'var(--emerald)' : 'var(--border)'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 16, color: a.isTriggered ? 'var(--amber)' : a.isActive ? 'var(--emerald)' : 'var(--text-3)',
      }}>
        {a.isTriggered ? '✓' : cond.icon}
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)' }}>{a.symbol}</span>
          <span style={{ fontSize: 12, color: 'var(--text-2)' }}>{cond.label}</span>
          <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--cyan)' }}>₹{Number(a.targetPrice).toLocaleString('en-IN')}</span>
        </div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {a.notes && <span style={{ fontSize: 11, color: 'var(--text-3)' }}>{a.notes}</span>}
          <span style={{ fontSize: 11, color: 'var(--text-3)' }}>
            Created {new Date(a.createdAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
          </span>
          {a.triggeredAt && (
            <span style={{ fontSize: 11, color: 'var(--amber)', fontWeight: 600 }}>
              Triggered {new Date(a.triggeredAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        {!a.isTriggered && (
          <button
            onClick={() => onToggle(a.id)}
            style={{
              padding: '5px 12px', borderRadius: 7, cursor: 'pointer', fontSize: 11, fontWeight: 600,
              background: a.isActive ? 'var(--surface-hi)' : 'var(--emerald-15)',
              border: a.isActive ? '1px solid var(--border)' : '1px solid var(--emerald)',
              color: a.isActive ? 'var(--text-2)' : 'var(--emerald)',
            }}
          >
            {a.isActive ? 'Pause' : 'Resume'}
          </button>
        )}
        <button onClick={() => onDelete(a.id)} style={{ padding: '5px 10px', borderRadius: 7, cursor: 'pointer', background: 'var(--rose-15)', border: '1px solid var(--rose)', color: 'var(--rose)', fontSize: 11 }}>
          Delete
        </button>
      </div>
    </div>
  )
}

const btn = { display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', borderRadius: 8, cursor: 'pointer', background: 'var(--cyan)', border: 'none', color: '#fff', fontSize: 13, fontWeight: 700 }
const lbl = { display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-2)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.06em' }
const inp = { width: '100%', padding: '9px 12px', borderRadius: 8, background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-1)', fontSize: 13, outline: 'none', boxSizing: 'border-box' }

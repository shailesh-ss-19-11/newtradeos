import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getStrategies, createStrategy, updateStrategy, deleteStrategy,
  getStrategyTypes, getStrategiesPerformance,
} from '../api'

const TIMEFRAMES = [
  { value: 'D',  label: 'Daily' },
  { value: '60', label: '60 Min' },
  { value: '15', label: '15 Min' },
  { value: '5',  label: '5 Min' },
]

export default function Strategies() {
  const navigate = useNavigate()
  const [strategies,    setStrategies]    = useState([])
  const [stratTypes,    setStratTypes]    = useState([])
  const [performance,   setPerformance]   = useState({})
  const [loading,       setLoading]       = useState(true)
  const [showModal,     setShowModal]     = useState(false)
  const [editing,       setEditing]       = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const [saving,        setSaving]        = useState(false)
  const [error,         setError]         = useState('')

  const defaultForm = { name: '', description: '', strategyType: '', timeframe: 'D', parameters: {} }
  const [form, setForm] = useState(defaultForm)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [stratRes, typesRes] = await Promise.all([getStrategies(), getStrategyTypes()])
      setStrategies(stratRes.data.strategies || [])
      setStratTypes(typesRes.data.types || [])
      // Load performance after we have strategies
      getStrategiesPerformance().then(r => setPerformance(r.data.performance || {})).catch(() => {})
    } catch {
      setError('Failed to load strategies')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const openCreate = () => {
    setEditing(null)
    setForm(defaultForm)
    setError('')
    setShowModal(true)
  }

  const openEdit = s => {
    setEditing(s)
    setForm({
      name: s.name, description: s.description || '',
      strategyType: s.strategyType, timeframe: s.timeframe,
      parameters: s.parameters || {},
    })
    setError('')
    setShowModal(true)
  }

  const handleTypeChange = typeKey => {
    const tDef = stratTypes.find(t => t.type === typeKey)
    const defaults = {}
    if (tDef) tDef.params.forEach(p => { defaults[p.key] = p.default })
    setForm(f => ({ ...f, strategyType: typeKey, parameters: defaults }))
  }

  const handleParamChange = (key, value) => {
    setForm(f => ({ ...f, parameters: { ...f.parameters, [key]: Number(value) } }))
  }

  const handleSave = async () => {
    setError('')
    if (!form.name.trim())  return setError('Name is required')
    if (!form.strategyType) return setError('Strategy type is required')
    setSaving(true)
    try {
      if (editing) {
        const res = await updateStrategy(editing.id, form)
        setStrategies(prev => prev.map(s => s.id === editing.id ? { ...s, ...res.data } : s))
      } else {
        const res = await createStrategy(form)
        setStrategies(prev => [res.data, ...prev])
      }
      setShowModal(false)
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to save strategy')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async id => {
    try {
      await deleteStrategy(id)
      setStrategies(prev => prev.filter(s => s.id !== id))
      setDeleteConfirm(null)
    } catch {
      alert('Failed to delete strategy')
    }
  }

  const selectedType = stratTypes.find(t => t.type === form.strategyType)

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>Strategies</h1>
          <p style={{ fontSize: 13, color: 'var(--text-2)' }}>Create and manage your trading strategies for backtesting</p>
        </div>
        <button onClick={openCreate} style={btnStyle}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          New Strategy
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-2)', fontSize: 13 }}>Loading...</div>
      ) : strategies.length === 0 ? (
        <div style={emptyState}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: 16 }}>
            <path d="M3 3v18h18"/><path d="M7 16l4-5 4 4 5-6"/>
          </svg>
          <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-2)', marginBottom: 8 }}>No strategies yet</p>
          <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 20 }}>Create your first strategy to start backtesting</p>
          <button onClick={openCreate} style={btnStyle}>Create Strategy</button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
          {strategies.map(s => (
            <StrategyCard
              key={s.id}
              strategy={s}
              perf={performance[s.id]}
              stratTypes={stratTypes}
              onEdit={openEdit}
              onDelete={id => setDeleteConfirm(id)}
              onRunBacktest={id => navigate(`/backtest?strategy=${id}`)}
            />
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div style={overlay} onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div style={modal}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-1)' }}>
                {editing ? 'Edit Strategy' : 'New Strategy'}
              </h2>
              <button onClick={() => setShowModal(false)} style={closeBtn}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>

            {error && <div style={errorBox}>{error}</div>}

            <div style={field}>
              <label style={labelStyle}>Strategy Name *</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g. EMA Golden Cross" style={input} />
            </div>

            <div style={field}>
              <label style={labelStyle}>Description</label>
              <textarea value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Optional description..." rows={2}
                style={{ ...input, resize: 'vertical', fontFamily: 'inherit' }} />
            </div>

            <div style={field}>
              <label style={labelStyle}>Strategy Type *</label>
              <select value={form.strategyType} onChange={e => handleTypeChange(e.target.value)} style={input}>
                <option value="">Select type...</option>
                {stratTypes.map(t => <option key={t.type} value={t.type}>{t.label}</option>)}
              </select>
              {selectedType && <p style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}>{selectedType.description}</p>}
            </div>

            <div style={field}>
              <label style={labelStyle}>Timeframe</label>
              <div style={{ display: 'flex', gap: 8 }}>
                {TIMEFRAMES.map(tf => (
                  <button key={tf.value} onClick={() => setForm(f => ({ ...f, timeframe: tf.value }))}
                    style={{ ...tfBtn, ...(form.timeframe === tf.value ? tfBtnActive : {}) }}>
                    {tf.label}
                  </button>
                ))}
              </div>
            </div>

            {selectedType && selectedType.params.length > 0 && (
              <div style={field}>
                <label style={labelStyle}>Parameters</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  {selectedType.params.map(p => (
                    <div key={p.key}>
                      <label style={{ fontSize: 11, color: 'var(--text-2)', display: 'block', marginBottom: 4 }}>{p.label}</label>
                      <input type="number" min={p.min} max={p.max}
                        step={p.type === 'number' ? (p.default < 10 ? 0.1 : 1) : 1}
                        value={form.parameters[p.key] ?? p.default}
                        onChange={e => handleParamChange(p.key, e.target.value)}
                        style={{ ...input, padding: '8px 10px' }} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: 10, marginTop: 24 }}>
              <button onClick={() => setShowModal(false)} style={cancelBtn}>Cancel</button>
              <button onClick={handleSave} disabled={saving}
                style={{ ...btnStyle, flex: 1, justifyContent: 'center', opacity: saving ? 0.7 : 1 }}>
                {saving ? 'Saving...' : (editing ? 'Save Changes' : 'Create Strategy')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm */}
      {deleteConfirm && (
        <div style={overlay} onClick={e => e.target === e.currentTarget && setDeleteConfirm(null)}>
          <div style={{ ...modal, maxWidth: 380 }}>
            <h2 style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-1)', marginBottom: 10 }}>Delete Strategy</h2>
            <p style={{ fontSize: 13, color: 'var(--text-2)', marginBottom: 24 }}>
              Are you sure? This will also remove all backtest runs associated with this strategy.
            </p>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setDeleteConfirm(null)} style={cancelBtn}>Cancel</button>
              <button onClick={() => handleDelete(deleteConfirm)}
                style={{ ...btnStyle, background: 'var(--rose)', flex: 1, justifyContent: 'center' }}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function StrategyCard({ strategy: s, perf, stratTypes, onEdit, onDelete, onRunBacktest }) {
  const typeDef  = stratTypes.find(t => t.type === s.strategyType)
  const params   = s.parameters || {}
  const hasParams = Object.keys(params).length > 0
  const hasPerf  = perf && perf.totalRuns > 0

  return (
    <div style={card}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-1)' }}>{s.name}</h3>
            <span style={{ ...badge, background: s.isActive ? 'var(--emerald-15)' : 'var(--surface-hi)', color: s.isActive ? 'var(--emerald)' : 'var(--text-3)' }}>
              {s.isActive ? 'Active' : 'Inactive'}
            </span>
          </div>
          <span style={{ fontSize: 11, color: 'var(--cyan)', background: 'var(--cyan-15)', padding: '2px 8px', borderRadius: 10, fontWeight: 600 }}>
            {typeDef?.label || s.strategyType}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0, marginLeft: 8 }}>
          <button onClick={() => onEdit(s)} style={iconBtn} title="Edit">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button onClick={() => onDelete(s.id)} style={{ ...iconBtn, color: 'var(--rose)' }} title="Delete">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
          </button>
        </div>
      </div>

      {s.description && (
        <p style={{ fontSize: 12, color: 'var(--text-2)', marginBottom: 12, lineHeight: 1.5 }}>{s.description}</p>
      )}

      <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
        <div style={metaItem}>
          <span style={metaLabel}>Timeframe</span>
          <span style={metaVal}>{s.timeframe}</span>
        </div>
        <div style={metaItem}>
          <span style={metaLabel}>Created</span>
          <span style={metaVal}>{new Date(s.createdAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })}</span>
        </div>
        <div style={metaItem}>
          <span style={metaLabel}>Backtests</span>
          <span style={metaVal}>{perf ? perf.totalRuns : '—'}</span>
        </div>
      </div>

      {/* Performance badges */}
      {hasPerf && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
          {perf.bestPnl !== null && (
            <span style={{
              fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20,
              background: perf.bestPnl >= 0 ? 'var(--emerald-15)' : 'var(--rose-15)',
              color: perf.bestPnl >= 0 ? 'var(--emerald)' : 'var(--rose)',
              border: `1px solid ${perf.bestPnl >= 0 ? 'var(--emerald)' : 'var(--rose)'}22`,
            }}>
              Best P&L: {perf.bestPnl >= 0 ? '+' : ''}₹{perf.bestPnl.toLocaleString('en-IN')}
            </span>
          )}
          {perf.bestWinRate !== null && (
            <span style={{
              fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20,
              background: 'var(--amber-15)', color: 'var(--amber)',
              border: '1px solid var(--amber)22',
            }}>
              Win: {perf.bestWinRate.toFixed(1)}%
            </span>
          )}
          {perf.lastRunAt && (
            <span style={{ fontSize: 11, color: 'var(--text-3)', padding: '3px 0' }}>
              Last: {new Date(perf.lastRunAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
            </span>
          )}
        </div>
      )}

      {hasParams && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, paddingTop: 10, marginBottom: 12, borderTop: '1px solid var(--border)' }}>
          {Object.entries(params).map(([k, v]) => (
            <span key={k} style={paramChip}>
              <span style={{ color: 'var(--text-3)' }}>{k}:</span> {v}
            </span>
          ))}
        </div>
      )}

      {/* Run Backtest CTA */}
      <div style={{ paddingTop: 12, borderTop: '1px solid var(--border)' }}>
        <button onClick={() => onRunBacktest(s.id)} style={runBtn}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          Run Backtest
        </button>
      </div>
    </div>
  )
}

const card       = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 18 }
const badge      = { fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 10 }
const iconBtn    = { background: 'var(--surface-hi)', border: '1px solid var(--border)', borderRadius: 6, padding: '5px 7px', cursor: 'pointer', color: 'var(--text-2)' }
const metaItem   = { display: 'flex', flexDirection: 'column', gap: 2 }
const metaLabel  = { fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }
const metaVal    = { fontSize: 12, fontWeight: 600, color: 'var(--text-2)' }
const paramChip  = { fontSize: 11, padding: '2px 8px', background: 'var(--surface-hi)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-2)' }
const emptyState = { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '80px 20px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12 }
const overlay    = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20 }
const modal      = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: '28px 28px', width: '100%', maxWidth: 500, maxHeight: '90vh', overflowY: 'auto' }
const closeBtn   = { background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-2)', padding: 4 }
const cancelBtn  = { flex: 1, padding: '10px 0', borderRadius: 8, cursor: 'pointer', background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-2)', fontSize: 14 }
const field      = { marginBottom: 18 }
const labelStyle = { display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-2)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }
const input      = { width: '100%', padding: '9px 12px', borderRadius: 8, background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-1)', fontSize: 13, outline: 'none', boxSizing: 'border-box' }
const errorBox   = { padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8, color: 'var(--rose)', fontSize: 13, marginBottom: 18 }
const tfBtn      = { flex: 1, padding: '7px 0', borderRadius: 7, cursor: 'pointer', background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-2)', fontSize: 12 }
const tfBtnActive = { background: 'var(--cyan-15)', border: '1px solid var(--cyan)', color: 'var(--cyan)', fontWeight: 700 }
const btnStyle   = { display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', borderRadius: 8, cursor: 'pointer', background: 'var(--cyan)', border: 'none', color: '#fff', fontSize: 13, fontWeight: 700 }
const runBtn     = { display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 7, cursor: 'pointer', background: 'var(--cyan-15)', border: '1px solid var(--cyan-25)', color: 'var(--cyan)', fontSize: 12, fontWeight: 600, width: '100%', justifyContent: 'center' }

import { useState, useEffect } from 'react'
import { browseMarketplace, getMyPublished, publishStrategy, subscribeStrategy, unpublishStrategy, getStrategies } from '../api'

const CATEGORIES = ['All', 'trend', 'momentum', 'reversal', 'breakout', 'ml', 'general']

export default function Marketplace() {
  const [tab,       setTab]       = useState('browse')
  const [strategies,setStrategies]= useState([])
  const [mine,      setMine]      = useState([])
  const [myStrats,  setMyStrats]  = useState([])
  const [category,  setCategory]  = useState('All')
  const [loading,   setLoading]   = useState(true)
  const [showPublish,setShowPublish]=useState(false)
  const [pubForm,   setPubForm]   = useState({ strategyId: '', title: '', description: '', category: 'general' })
  const [publishing,setPublishing]= useState(false)
  const [subbing,   setSubbing]   = useState(null)
  const [msg,       setMsg]       = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [br, mr, sr] = await Promise.all([
        browseMarketplace(category !== 'All' ? { category } : {}),
        getMyPublished(),
        getStrategies(),
      ])
      setStrategies(br.data.strategies || [])
      setMine(mr.data.strategies || [])
      setMyStrats(sr.data.strategies || [])
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [category])

  const handlePublish = async () => {
    if (!pubForm.strategyId || !pubForm.title) return
    setPublishing(true)
    try {
      await publishStrategy({ ...pubForm, strategyId: Number(pubForm.strategyId) })
      setShowPublish(false)
      setPubForm({ strategyId: '', title: '', description: '', category: 'general' })
      setMsg('Strategy published!')
      setTab('mine')
      load()
    } catch (err) {
      setMsg(err?.response?.data?.error || 'Publish failed')
    }
    setPublishing(false)
  }

  const handleSubscribe = async (id) => {
    setSubbing(id)
    try {
      const r = await subscribeStrategy(id)
      setMsg(r.data.message || 'Strategy added to your account!')
      setStrategies(s => s.map(x => x.id === id ? { ...x, isSubscribed: true, subscribers: x.subscribers + 1 } : x))
    } catch (err) {
      setMsg(err?.response?.data?.error || 'Subscribe failed')
    }
    setSubbing(null)
  }

  const handleUnpublish = async (id) => {
    await unpublishStrategy(id)
    setMine(m => m.filter(x => x.id !== id))
    setMsg('Strategy unpublished')
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>Strategy Marketplace</h1>
          <p style={{ fontSize: 13, color: 'var(--text-2)' }}>Discover community strategies or share your own</p>
        </div>
        <button onClick={() => setShowPublish(true)} style={btn}>+ Publish Strategy</button>
      </div>

      {msg && (
        <div style={{ padding: '10px 16px', background: 'var(--emerald-15)', border: '1px solid var(--emerald)', borderRadius: 8, color: 'var(--emerald)', fontSize: 13, marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          {msg} <button onClick={() => setMsg('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--emerald)' }}>✕</button>
        </div>
      )}

      <div style={{ display: 'flex', gap: 4, marginBottom: 20 }}>
        {[['browse','Browse'], ['mine','My Published']].map(([k,l]) => (
          <button key={k} onClick={() => setTab(k)} style={{ ...tabBtn, ...(tab === k ? tabActive : {}) }}>{l}</button>
        ))}
      </div>

      {tab === 'browse' && (
        <>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
            {CATEGORIES.map(c => (
              <button key={c} onClick={() => setCategory(c)} style={{
                padding: '5px 14px', borderRadius: 20, cursor: 'pointer', border: '1px solid',
                borderColor: category === c ? 'var(--cyan)' : 'var(--border)',
                background: category === c ? 'var(--cyan-15)' : 'var(--surface-hi)',
                color: category === c ? 'var(--cyan)' : 'var(--text-2)',
                fontSize: 12, fontWeight: category === c ? 700 : 400,
                textTransform: 'capitalize',
              }}>
                {c}
              </button>
            ))}
          </div>

          {loading ? (
            <p style={{ color: 'var(--text-2)', fontSize: 13 }}>Loading...</p>
          ) : strategies.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-3)' }}>
              <p style={{ fontSize: 15, marginBottom: 8 }}>No strategies published yet</p>
              <p style={{ fontSize: 13 }}>Be the first to share your strategy!</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
              {strategies.map(s => <MarketplaceCard key={s.id} strategy={s} onSubscribe={handleSubscribe} subbing={subbing} />)}
            </div>
          )}
        </>
      )}

      {tab === 'mine' && (
        <div>
          {mine.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-3)' }}>
              <p style={{ marginBottom: 12, fontSize: 13 }}>You haven't published any strategies yet</p>
              <button onClick={() => setShowPublish(true)} style={btn}>Publish Your First Strategy</button>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 14 }}>
              {mine.map(s => (
                <div key={s.id} style={card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)' }}>{s.title}</h3>
                    <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
                      background: s.isPublished ? 'var(--emerald-15)' : 'var(--rose-15)',
                      color: s.isPublished ? 'var(--emerald)' : 'var(--rose)' }}>
                      {s.isPublished ? 'Live' : 'Draft'}
                    </span>
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 10 }}>{s.strategyName}</p>
                  <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                    <MetaStat label="Subscribers" value={s.subscribers} />
                    {s.avgWinRate && <MetaStat label="Best Win Rate" value={`${s.avgWinRate}%`} />}
                    {s.avgPnl && <MetaStat label="Best P&L" value={`₹${s.avgPnl?.toLocaleString('en-IN')}`} />}
                  </div>
                  <button onClick={() => handleUnpublish(s.id)} style={{ width: '100%', padding: '7px', borderRadius: 7, cursor: 'pointer', background: 'transparent', border: '1px solid var(--rose)', color: 'var(--rose)', fontSize: 12, fontWeight: 600 }}>
                    Unpublish
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Publish Modal */}
      {showPublish && (
        <div style={overlay} onClick={e => e.target === e.currentTarget && setShowPublish(false)}>
          <div style={modal}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
              <h2 style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-1)' }}>Publish Strategy</h2>
              <button onClick={() => setShowPublish(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-2)' }}>✕</button>
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={lbl}>Your Strategy</label>
              <select value={pubForm.strategyId} onChange={e => setPubForm(f => ({ ...f, strategyId: e.target.value }))} style={inp}>
                <option value="">Select strategy...</option>
                {myStrats.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={lbl}>Display Title</label>
              <input value={pubForm.title} onChange={e => setPubForm(f => ({ ...f, title: e.target.value }))} placeholder="Catchy title for your strategy" style={inp} />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={lbl}>Description</label>
              <textarea value={pubForm.description} onChange={e => setPubForm(f => ({ ...f, description: e.target.value }))} rows={3} style={{ ...inp, resize: 'vertical', fontFamily: 'inherit' }} placeholder="Describe your strategy's approach..." />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={lbl}>Category</label>
              <select value={pubForm.category} onChange={e => setPubForm(f => ({ ...f, category: e.target.value }))} style={inp}>
                {CATEGORIES.slice(1).map(c => <option key={c} value={c} style={{ textTransform: 'capitalize' }}>{c}</option>)}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setShowPublish(false)} style={cancelBtn}>Cancel</button>
              <button onClick={handlePublish} disabled={publishing} style={{ ...btn, flex: 1, justifyContent: 'center', opacity: publishing ? 0.7 : 1 }}>
                {publishing ? 'Publishing...' : 'Publish'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function MarketplaceCard({ strategy: s, onSubscribe, subbing }) {
  return (
    <div style={card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)', flex: 1 }}>{s.title}</h3>
        <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 10, background: 'var(--cyan-15)', color: 'var(--cyan)', marginLeft: 8, flexShrink: 0, textTransform: 'capitalize' }}>{s.category}</span>
      </div>
      <p style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 4 }}>by {s.authorName} · {s.strategyType}</p>
      {s.description && <p style={{ fontSize: 12, color: 'var(--text-2)', marginBottom: 12, lineHeight: 1.5 }}>{s.description}</p>}
      <div style={{ display: 'flex', gap: 12, marginBottom: 14, flexWrap: 'wrap' }}>
        <MetaStat label="Subscribers" value={s.subscribers} />
        {s.avgWinRate && <MetaStat label="Win Rate" value={`${s.avgWinRate}%`} color="var(--emerald)" />}
        {s.avgPnl && <MetaStat label="Best P&L" value={`₹${s.avgPnl?.toLocaleString('en-IN')}`} color={s.avgPnl >= 0 ? 'var(--emerald)' : 'var(--rose)'} />}
      </div>
      <button
        onClick={() => onSubscribe(s.id)}
        disabled={s.isSubscribed || subbing === s.id}
        style={{
          width: '100%', padding: '8px', borderRadius: 8, cursor: s.isSubscribed ? 'default' : 'pointer',
          background: s.isSubscribed ? 'var(--surface-hi)' : 'var(--cyan)',
          border: '1px solid var(--border)', color: s.isSubscribed ? 'var(--text-3)' : '#fff',
          fontSize: 13, fontWeight: 600, opacity: subbing === s.id ? 0.7 : 1,
        }}
      >
        {s.isSubscribed ? '✓ Added to Your Account' : subbing === s.id ? 'Adding...' : 'Add to My Strategies'}
      </button>
    </div>
  )
}

function MetaStat({ label, value, color }) {
  return (
    <div>
      <p style={{ fontSize: 10, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>{label}</p>
      <p style={{ fontSize: 13, fontWeight: 700, color: color || 'var(--text-1)' }}>{value}</p>
    </div>
  )
}

const btn       = { display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', borderRadius: 8, cursor: 'pointer', background: 'var(--cyan)', border: 'none', color: '#fff', fontSize: 13, fontWeight: 700 }
const card      = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 18 }
const overlay   = { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: 20 }
const modal     = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 24, width: '100%', maxWidth: 480, maxHeight: '90vh', overflowY: 'auto' }
const cancelBtn = { flex: 1, padding: '10px 0', borderRadius: 8, cursor: 'pointer', background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-2)', fontSize: 13 }
const tabBtn    = { padding: '7px 16px', borderRadius: 8, cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--surface-hi)', color: 'var(--text-2)', fontSize: 13 }
const tabActive = { background: 'var(--cyan-15)', border: '1px solid var(--cyan)', color: 'var(--cyan)', fontWeight: 700 }
const lbl       = { display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-2)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.06em' }
const inp       = { width: '100%', padding: '9px 12px', borderRadius: 8, background: 'var(--surface-hi)', border: '1px solid var(--border)', color: 'var(--text-1)', fontSize: 13, outline: 'none', boxSizing: 'border-box' }

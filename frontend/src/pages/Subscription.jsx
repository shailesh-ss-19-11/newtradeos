import { useEffect, useState } from 'react'
import { getCurrentSubscription, upgradeSubscription } from '../api'

const TIER_ORDER = ['free', 'basic', 'pro']

const PLAN_META = {
  free:  { color: 'var(--text-3)', badge: null },
  basic: { color: 'var(--amber)',  badge: 'Popular' },
  pro:   { color: 'var(--cyan)',   badge: 'Best Value' },
}

const FEATURE_ROWS = [
  { label: 'Saved strategies',    key: s => s.max_strategies === null ? 'Unlimited' : String(s.max_strategies) },
  { label: 'Backtests / month',   key: s => s.backtests_per_month === null ? 'Unlimited' : String(s.backtests_per_month) },
  { label: 'Max universe',        key: s => {
    const u = s.allowed_universes
    if (u.includes('NIFTY500')) return 'Nifty 500'
    if (u.includes('NIFTY200'))  return 'Nifty 200'
    return 'Nifty 50'
  }},
  { label: 'Max history period',  key: s => `${s.max_period_months / 12} yr${s.max_period_months > 12 ? 's' : ''}` },
]

function UsageBar({ used, total, label, color }) {
  const pct = total == null ? 0 : Math.min(100, Math.round((used / total) * 100))
  const over = total != null && used >= total
  return (
    <div style={{ flex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: 'var(--text-2)', fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 700, color: over ? 'var(--rose)' : 'var(--text-1)' }}>
          {used} / {total == null ? '∞' : total}
        </span>
      </div>
      <div style={{ height: 6, borderRadius: 4, background: 'var(--surface-hi)', overflow: 'hidden' }}>
        {total != null && (
          <div style={{
            width: `${pct}%`, height: '100%', borderRadius: 4,
            background: over ? 'var(--rose)' : color,
            transition: 'width 0.5s ease',
          }} />
        )}
        {total == null && (
          <div style={{ width: '100%', height: '100%', borderRadius: 4, background: `${color}40` }} />
        )}
      </div>
    </div>
  )
}

export default function Subscription() {
  const [sub, setSub]       = useState(null)
  const [plans, setPlans]   = useState({})
  const [loading, setLoading]   = useState(true)
  const [upgrading, setUpgrading] = useState(null)
  const [msg, setMsg]       = useState('')
  const [error, setError]   = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [subRes, plansRes] = await Promise.all([
        getCurrentSubscription(),
        import('../api').then(m => m.getSubscriptionPlans()),
      ])
      setSub(subRes.data)
      setPlans(plansRes.data.plans)
    } catch {
      setError('Failed to load subscription data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleUpgrade = async (tier) => {
    setUpgrading(tier)
    setMsg('')
    setError('')
    try {
      const res = await upgradeSubscription(tier)
      setMsg(res.data.message)
      await load()
    } catch (err) {
      setError(err?.response?.data?.error || 'Upgrade failed')
    } finally {
      setUpgrading(null)
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300 }}>
        <div style={{ width: 28, height: 28, borderRadius: '50%', border: '3px solid var(--border)', borderTopColor: 'var(--cyan)', animation: 'spin 0.8s linear infinite' }} />
      </div>
    )
  }

  const currentTier  = sub?.tier || 'free'
  const currentPlan  = sub?.plan || {}
  const usage        = sub?.usage || { strategies: 0, backtestsThisMonth: 0 }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 4 }}>
          Subscription & Plans
        </h1>
        <p style={{ fontSize: 14, color: 'var(--text-2)' }}>
          Manage your TradeOS plan and unlock more strategies, universes, and history.
        </p>
      </div>

      {(msg || error) && (
        <div style={{
          padding: '10px 16px', borderRadius: 8, marginBottom: 20, fontSize: 14,
          background: msg ? 'rgba(0,200,80,0.1)' : 'rgba(220,38,38,0.1)',
          border: `1px solid ${msg ? 'var(--emerald)' : 'var(--rose)'}`,
          color: msg ? 'var(--emerald)' : 'var(--rose)',
        }}>
          {msg || error}
        </div>
      )}

      {/* Current plan + usage */}
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 12, padding: '20px 24px', marginBottom: 28,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <div>
            <p style={{ fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
              Current Plan
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-1)' }}>
                {currentPlan.name || 'Free'}
              </span>
              <span style={{
                padding: '2px 8px', borderRadius: 20, fontSize: 11, fontWeight: 700,
                background: 'var(--cyan-15)', color: 'var(--cyan)',
                border: '1px solid var(--cyan-25)',
              }}>
                {currentTier.toUpperCase()}
              </span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 2 }}>Price</p>
            <p style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-1)' }}>
              {currentPlan.price_inr === 0 ? 'Free' : `₹${currentPlan.price_inr}/mo`}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 20 }}>
          <UsageBar
            used={usage.strategies}
            total={currentPlan.max_strategies}
            label="Strategies"
            color="var(--cyan)"
          />
          <UsageBar
            used={usage.backtestsThisMonth}
            total={currentPlan.backtests_per_month}
            label="Backtests this month"
            color="var(--amber)"
          />
        </div>
      </div>

      {/* Plan comparison cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {TIER_ORDER.map(tier => {
          const plan   = plans[tier]
          if (!plan) return null
          const meta   = PLAN_META[tier]
          const isCurr = tier === currentTier
          const isUp   = TIER_ORDER.indexOf(tier) > TIER_ORDER.indexOf(currentTier)
          const isDown = TIER_ORDER.indexOf(tier) < TIER_ORDER.indexOf(currentTier)

          return (
            <div key={tier} style={{
              background: 'var(--surface)',
              border: `1px solid ${isCurr ? 'var(--cyan)' : 'var(--border)'}`,
              borderRadius: 14,
              padding: '24px 20px',
              position: 'relative',
              boxShadow: isCurr ? '0 0 0 1px var(--cyan-25)' : 'none',
            }}>
              {/* Badge */}
              {meta.badge && (
                <div style={{
                  position: 'absolute', top: -10, left: '50%', transform: 'translateX(-50%)',
                  padding: '3px 12px', borderRadius: 20, fontSize: 11, fontWeight: 700,
                  background: 'var(--cyan)', color: '#fff', whiteSpace: 'nowrap',
                }}>
                  {meta.badge}
                </div>
              )}
              {isCurr && (
                <div style={{
                  position: 'absolute', top: -10, right: 16,
                  padding: '3px 10px', borderRadius: 20, fontSize: 10, fontWeight: 700,
                  background: 'var(--surface-hi)', color: 'var(--cyan)',
                  border: '1px solid var(--cyan-25)',
                }}>
                  Current
                </div>
              )}

              {/* Plan name & price */}
              <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-2)', marginBottom: 4 }}>
                {plan.name}
              </p>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 20 }}>
                <span style={{ fontSize: 28, fontWeight: 800, color: 'var(--text-1)' }}>
                  {plan.price_inr === 0 ? '₹0' : `₹${plan.price_inr}`}
                </span>
                {plan.price_inr > 0 && (
                  <span style={{ fontSize: 12, color: 'var(--text-3)' }}>/month</span>
                )}
              </div>

              {/* Feature rows */}
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16, marginBottom: 20 }}>
                {FEATURE_ROWS.map(row => (
                  <div key={row.label} style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '6px 0', borderBottom: '1px solid var(--border)',
                    fontSize: 12,
                  }}>
                    <span style={{ color: 'var(--text-2)' }}>{row.label}</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-1)' }}>{row.key(plan)}</span>
                  </div>
                ))}
              </div>

              {/* Feature list */}
              <ul style={{ listStyle: 'none', marginBottom: 20 }}>
                {plan.features.map(f => (
                  <li key={f} style={{ display: 'flex', gap: 8, fontSize: 12, color: 'var(--text-2)', marginBottom: 6 }}>
                    <span style={{ color: 'var(--emerald)', flexShrink: 0, marginTop: 1 }}>✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              {/* CTA button */}
              {isCurr ? (
                <button disabled style={{
                  width: '100%', padding: '10px', borderRadius: 8, cursor: 'not-allowed',
                  background: 'var(--surface-hi)', border: '1px solid var(--border)',
                  color: 'var(--text-3)', fontSize: 13, fontWeight: 600,
                }}>
                  Current Plan
                </button>
              ) : isUp ? (
                <button
                  onClick={() => handleUpgrade(tier)}
                  disabled={upgrading === tier}
                  style={{
                    width: '100%', padding: '10px', borderRadius: 8, cursor: upgrading === tier ? 'not-allowed' : 'pointer',
                    background: 'var(--cyan)', border: 'none',
                    color: '#fff', fontSize: 13, fontWeight: 700,
                    opacity: upgrading === tier ? 0.7 : 1,
                  }}
                >
                  {upgrading === tier ? 'Upgrading…' : `Upgrade to ${plan.name}`}
                </button>
              ) : (
                <button
                  onClick={() => handleUpgrade(tier)}
                  disabled={upgrading === tier}
                  style={{
                    width: '100%', padding: '10px', borderRadius: 8, cursor: upgrading === tier ? 'not-allowed' : 'pointer',
                    background: 'transparent', border: '1px solid var(--border)',
                    color: 'var(--text-2)', fontSize: 13, fontWeight: 600,
                    opacity: upgrading === tier ? 0.7 : 1,
                  }}
                >
                  {upgrading === tier ? 'Switching…' : `Switch to ${plan.name}`}
                </button>
              )}
            </div>
          )
        })}
      </div>

      {/* Note */}
      <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-3)', marginTop: 24 }}>
        All plans include a 30-day subscription period. Billing is simulated — no actual charges.
      </p>
    </div>
  )
}

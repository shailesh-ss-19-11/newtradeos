import { useEffect, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useTheme } from '../App'
import { useAuth } from '../contexts/AuthContext'
import NotificationBell from './NotificationBell'

const NAV = [
  {
    to: '/', label: 'Dashboard',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>,
  },
  {
    to: '/trades', label: 'Trades',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 014-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 01-4 4H3"/></svg>,
  },
  {
    to: '/analytics', label: 'Analytics',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="M7 16l4-5 4 4 5-6"/></svg>,
  },
  {
    to: '/chart', label: 'Charts',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="8" width="4" height="13" rx="1"/><rect x="10" y="3" width="4" height="18" rx="1"/><rect x="18" y="12" width="4" height="9" rx="1"/></svg>,
  },
]

const EXTRA_NAV = [
  {
    to: '/screener', label: 'Screener',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
  },
  {
    to: '/heatmap', label: 'Heat Map',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="4" height="4" rx="1"/><rect x="10" y="3" width="4" height="4" rx="1"/><rect x="17" y="3" width="4" height="4" rx="1"/><rect x="3" y="10" width="4" height="4" rx="1"/><rect x="10" y="10" width="4" height="4" rx="1"/><rect x="17" y="10" width="4" height="4" rx="1"/><rect x="3" y="17" width="4" height="4" rx="1"/><rect x="10" y="17" width="4" height="4" rx="1"/><rect x="17" y="17" width="4" height="4" rx="1"/></svg>,
  },
]

const STRATEGY_NAV = [
  {
    to: '/strategies', label: 'Strategies',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="M7 16l4-5 4 4 5-6"/><circle cx="7" cy="16" r="1.5" fill="currentColor"/><circle cx="11" cy="11" r="1.5" fill="currentColor"/><circle cx="15" cy="15" r="1.5" fill="currentColor"/><circle cx="20" cy="9" r="1.5" fill="currentColor"/></svg>,
  },
  {
    to: '/backtest', label: 'Backtest',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>,
  },
  {
    to: '/backtest-history', label: 'History',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  },
  {
    to: '/optimizer', label: 'Optimizer',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M5.34 18.66l-1.41 1.41M20 12h-2M6 12H4M19.07 19.07l-1.41-1.41M5.34 5.34L3.93 3.93"/></svg>,
  },
  {
    to: '/subscription', label: 'Subscription',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>,
  },
]

const TRADING_NAV = [
  {
    to: '/paper-trading', label: 'Paper Trading',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>,
  },
  {
    to: '/journal', label: 'Trade Journal',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>,
  },
  {
    to: '/alerts', label: 'Price Alerts',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>,
  },
  {
    to: '/marketplace', label: 'Marketplace',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg>,
  },
  {
    to: '/forward-test', label: 'Forward Test',
    icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/><line x1="19" y1="3" x2="19" y2="21"/></svg>,
  },
]

const MONITOR = {
  to: '/monitor', label: 'Monitor',
  icon: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
}

function NavItem({ to, label, icon }) {
  const location = useLocation()
  const exact  = to === '/'
  const active = exact ? location.pathname === '/' : location.pathname.startsWith(to)

  return (
    <NavLink to={to} style={{ textDecoration: 'none' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '9px 20px',
        fontSize: 13, fontWeight: active ? 600 : 400,
        color: active ? 'var(--text-1)' : 'var(--text-2)',
        background: active ? 'var(--surface-hi)' : 'transparent',
        borderLeft: `2px solid ${active ? 'var(--cyan)' : 'transparent'}`,
        transition: 'all 0.15s ease',
        cursor: 'pointer',
      }}
        onMouseEnter={e => { if (!active) { e.currentTarget.style.background = 'var(--surface)'; e.currentTarget.style.color = 'var(--text-1)' } }}
        onMouseLeave={e => { if (!active) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-2)' } }}
      >
        <span style={{ color: active ? 'var(--cyan)' : 'inherit', flexShrink: 0, opacity: active ? 1 : 0.7 }}>
          {icon}
        </span>
        {label}
      </div>
    </NavLink>
  )
}

function ISTClock() {
  const [time, setTime] = useState('')
  useEffect(() => {
    const tick = () => {
      const t = new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
      setTime(t)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])
  return <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-2)', letterSpacing: '0.03em' }}>{time}</span>
}

export default function Navbar({ marketOpen }) {
  const { theme, toggle } = useTheme()
  const { user, logout }  = useAuth()
  const navigate          = useNavigate()
  const [soundOn, setSoundOn] = useState(() => localStorage.getItem('tradeos-sound') !== 'off')

  const handleLogout = () => { logout(); navigate('/login') }

  const toggleSound = () => {
    const next = !soundOn
    setSoundOn(next)
    localStorage.setItem('tradeos-sound', next ? 'on' : 'off')
  }

  return (
    <aside style={{
      width: 220, minWidth: 220, height: '100vh',
      background: 'var(--bg)',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Logo */}
      <div style={{ padding: '20px 20px 18px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 8, flexShrink: 0,
            background: 'var(--cyan-15)',
            border: '1px solid var(--cyan-25)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 16px var(--cyan-glow)',
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
              <polyline points="16 7 22 7 22 13"/>
            </svg>
          </div>
          <div>
            <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-1)', letterSpacing: '-0.02em', lineHeight: 1.2 }}>TradeOS</p>
            <p style={{ fontSize: 10, color: 'var(--text-2)', letterSpacing: '0.03em', marginTop: 2 }}>v3 · FYERS</p>
          </div>
        </div>
      </div>

      {/* Nav links */}
      <nav style={{ flex: 1, paddingTop: 8, overflowY: 'auto' }}>
        <p style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', padding: '10px 20px 6px' }}>
          Navigation
        </p>
        {NAV.map(n => <NavItem key={n.to} {...n} />)}

        <div style={{ height: 1, background: 'var(--border)', margin: '8px 16px' }} />
        <p style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', padding: '10px 20px 6px' }}>
          Tools
        </p>
        {EXTRA_NAV.map(n => <NavItem key={n.to} {...n} />)}

        <div style={{ height: 1, background: 'var(--border)', margin: '8px 16px' }} />
        <p style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', padding: '10px 20px 6px' }}>
          Backtest
        </p>
        {STRATEGY_NAV.map(n => <NavItem key={n.to} {...n} />)}

        <div style={{ height: 1, background: 'var(--border)', margin: '8px 16px' }} />
        <p style={{ fontSize: 10, fontWeight: 500, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.1em', padding: '10px 20px 6px' }}>
          Trading
        </p>
        {TRADING_NAV.map(n => <NavItem key={n.to} {...n} />)}

        <div style={{ height: 1, background: 'var(--border)', margin: '8px 16px' }} />
        <NavItem {...MONITOR} />
      </nav>

      {/* Bottom: controls + market status + IST clock */}
      <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border)' }}>
        {/* Theme + Sound toggles */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
          <button onClick={toggle} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            style={{ flex: 1, padding: '6px 0', background: 'var(--surface-hi)',
              border: '1px solid var(--border)', borderRadius: 6, cursor: 'pointer',
              fontSize: 13, color: 'var(--text-2)', display: 'flex', alignItems: 'center',
              justifyContent: 'center', gap: 4 }}>
            {theme === 'dark' ? '☀️' : '🌙'} <span style={{ fontSize: 10 }}>{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
          <button onClick={toggleSound} title={soundOn ? 'Mute alerts' : 'Enable alerts'}
            style={{ flex: 1, padding: '6px 0', background: 'var(--surface-hi)',
              border: '1px solid var(--border)', borderRadius: 6, cursor: 'pointer',
              fontSize: 13, color: soundOn ? 'var(--cyan)' : 'var(--text-3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
            {soundOn ? '🔔' : '🔕'} <span style={{ fontSize: 10 }}>{soundOn ? 'Sound' : 'Muted'}</span>
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <div style={{
              width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
              background: marketOpen ? 'var(--emerald)' : 'var(--rose)',
              boxShadow: marketOpen ? '0 0 8px var(--emerald)' : 'none',
            }} className={marketOpen ? 'pulse-dot' : ''} />
            <span style={{ fontSize: 11, fontWeight: 600, color: marketOpen ? 'var(--emerald)' : 'var(--text-2)' }}>
              {marketOpen ? 'Market Open' : 'Market Closed'}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 10, color: 'var(--text-3)' }}>NSE · BSE · MCX</span>
          <ISTClock />
        </div>

        {/* User info */}
        {user && (
          <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <div>
                <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-1)', lineHeight: 1.3 }}>{user.name}</p>
                <p style={{ fontSize: 10, color: 'var(--text-3)' }}>{user.subscription_tier}</p>
              </div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <NotificationBell />
                <button onClick={handleLogout} title="Sign out"
                  style={{ background: 'none', border: '1px solid var(--border)', borderRadius: 6, padding: '4px 6px', cursor: 'pointer', color: 'var(--text-3)' }}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}

import { useState, useEffect, useRef } from 'react'
import { getNotifications, markAllRead, deleteNotification } from '../api'

const TYPE_ICON = {
  backtest_completed: '✅',
  strategy_limit:     '⚠️',
  subscription:       '💳',
  price_alert:        '🔔',
  default:            '📢',
}

export default function NotificationBell() {
  const [open,        setOpen]        = useState(false)
  const [notifs,      setNotifs]      = useState([])
  const [unread,      setUnread]      = useState(0)
  const panelRef = useRef(null)

  const load = async () => {
    try {
      const r = await getNotifications()
      setNotifs(r.data.notifications || [])
      setUnread(r.data.unreadCount || 0)
    } catch {}
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 30_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const handler = e => {
      if (panelRef.current && !panelRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleMarkAll = async () => {
    await markAllRead()
    setNotifs(n => n.map(x => ({ ...x, isRead: true })))
    setUnread(0)
  }

  const handleDelete = async (id) => {
    await deleteNotification(id)
    setNotifs(n => n.filter(x => x.id !== id))
  }

  return (
    <div ref={panelRef} style={{ position: 'relative' }}>
      <button
        onClick={() => { setOpen(o => !o); if (!open) load() }}
        style={{
          position: 'relative', background: 'var(--surface-hi)',
          border: '1px solid var(--border)', borderRadius: 8,
          width: 34, height: 34, cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--text-2)',
        }}
        title="Notifications"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/>
        </svg>
        {unread > 0 && (
          <span style={{
            position: 'absolute', top: -4, right: -4,
            background: 'var(--rose)', color: '#fff',
            borderRadius: '50%', fontSize: 10, fontWeight: 700,
            width: 16, height: 16, display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: '2px solid var(--bg)',
          }}>
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div style={{
          position: 'absolute', right: 0, top: 42, width: 320, zIndex: 2000,
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
          overflow: 'hidden',
        }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-1)' }}>Notifications</span>
            {unread > 0 && (
              <button onClick={handleMarkAll} style={{ fontSize: 11, color: 'var(--cyan)', background: 'none', border: 'none', cursor: 'pointer' }}>
                Mark all read
              </button>
            )}
          </div>

          <div style={{ maxHeight: 380, overflowY: 'auto' }}>
            {notifs.length === 0 ? (
              <p style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-3)', fontSize: 13 }}>
                No notifications
              </p>
            ) : notifs.map(n => (
              <div key={n.id} style={{
                padding: '12px 16px', borderBottom: '1px solid var(--border)',
                background: n.isRead ? 'transparent' : 'var(--cyan-15)',
                display: 'flex', gap: 10, alignItems: 'flex-start',
              }}>
                <span style={{ fontSize: 18, flexShrink: 0 }}>{TYPE_ICON[n.type] || TYPE_ICON.default}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-1)', marginBottom: 2 }}>{n.title}</p>
                  {n.message && <p style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.4 }}>{n.message}</p>}
                  <p style={{ fontSize: 10, color: 'var(--text-3)', marginTop: 4 }}>
                    {new Date(n.createdAt).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
                <button onClick={() => handleDelete(n.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', flexShrink: 0, padding: 2 }}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

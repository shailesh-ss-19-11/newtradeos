/* Stat card with glowing left border — the design signature */
const ACCENT = {
  cyan:    { color: '#00D4FF', glow: 'rgba(0,212,255,0.25)'   },
  emerald: { color: '#00FF88', glow: 'rgba(0,255,136,0.25)'   },
  rose:    { color: '#FF3B6B', glow: 'rgba(255,59,107,0.25)'  },
  amber:   { color: '#FFB800', glow: 'rgba(255,184,0,0.25)'   },
  violet:  { color: '#7B6FFF', glow: 'rgba(123,111,255,0.25)' },
  default: { color: '#3D5280', glow: 'rgba(61,82,128,0.2)'    },
}

export default function StatCard({ label, value, sub, color = 'default', trend, isLoading }) {
  const a = ACCENT[color] || ACCENT.default

  if (isLoading) {
    return (
      <div className="shimmer" style={{ borderRadius: 10, height: 88 }} />
    )
  }

  return (
    <div style={{
      background: 'var(--surface)',
      borderRadius: 10,
      border: '1px solid var(--border)',
      borderLeft: `2px solid ${a.color}`,
      boxShadow: `0 4px 20px rgba(0,0,0,0.45), -4px 0 20px ${a.glow}`,
      padding: '16px 18px',
      position: 'relative', overflow: 'hidden',
      transition: 'box-shadow 0.15s ease, border-color 0.15s ease',
    }}
      onMouseEnter={e => {
        e.currentTarget.style.boxShadow = `0 6px 28px rgba(0,0,0,0.5), -6px 0 28px ${a.glow}`
        e.currentTarget.style.borderColor = 'var(--border-hi)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = `0 4px 20px rgba(0,0,0,0.45), -4px 0 20px ${a.glow}`
        e.currentTarget.style.borderColor = 'var(--border)'
      }}
    >
      {/* Subtle radial glow in top-right corner */}
      <div style={{
        position: 'absolute', top: -16, right: -16, width: 64, height: 64,
        borderRadius: '50%', background: a.glow, filter: 'blur(20px)',
        pointerEvents: 'none',
      }} />

      {/* Label */}
      <p style={{
        fontSize: 10, fontWeight: 500, color: 'var(--text-2)',
        textTransform: 'uppercase', letterSpacing: '0.09em', marginBottom: 10,
      }}>
        {label}
      </p>

      {/* Value */}
      <p style={{
        fontSize: 26, fontWeight: 700, color: 'var(--text-1)',
        fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums',
        letterSpacing: '-0.03em', lineHeight: 1,
      }}>
        {value}
      </p>

      {/* Sub / trend */}
      {(sub || trend != null) && (
        <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          {trend != null && (
            <span style={{
              fontSize: 10, fontWeight: 600,
              color: trend >= 0 ? '#00FF88' : '#FF3B6B',
              background: trend >= 0 ? 'rgba(0,255,136,0.1)' : 'rgba(255,59,107,0.1)',
              padding: '2px 6px', borderRadius: 4,
              fontFamily: 'var(--font-mono)',
            }}>
              {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}%
            </span>
          )}
          {sub && <p style={{ fontSize: 11, color: 'var(--text-3)' }}>{sub}</p>}
        </div>
      )}
    </div>
  )
}


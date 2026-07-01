import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authRegister } from '../api'
import { useAuth } from '../contexts/AuthContext'

export default function Register() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [form, setForm]     = useState({ name: '', email: '', password: '', confirm: '' })
  const [error, setError]   = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) {
      setError('Passwords do not match')
      return
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }
    setLoading(true)
    try {
      const res = await authRegister(form.name, form.email, form.password)
      login(res.data.token, res.data.user)
      navigate('/')
    } catch (err) {
      setError(err?.response?.data?.error || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.logo}>
          <div style={styles.logoIcon}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
              <polyline points="16 7 22 7 22 13"/>
            </svg>
          </div>
          <div>
            <p style={styles.logoTitle}>TradeOS</p>
            <p style={styles.logoSub}>Backtesting Platform</p>
          </div>
        </div>

        <h1 style={styles.heading}>Create account</h1>
        <p style={styles.subheading}>Start building your trading strategies</p>

        {error && <div style={styles.errorBox}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <div style={styles.field}>
            <label style={styles.label}>Full Name</label>
            <input type="text" required value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="John Doe" style={styles.input} />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Email</label>
            <input type="email" required value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              placeholder="you@example.com" style={styles.input} />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Password</label>
            <input type="password" required value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              placeholder="Minimum 6 characters" style={styles.input} />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Confirm Password</label>
            <input type="password" required value={form.confirm}
              onChange={e => setForm(f => ({ ...f, confirm: e.target.value }))}
              placeholder="Repeat password" style={styles.input} />
          </div>
          <button type="submit" disabled={loading} style={{...styles.btn, opacity: loading ? 0.7 : 1}}>
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p style={styles.switchText}>
          Already have an account?{' '}
          <Link to="/login" style={styles.link}>Sign in</Link>
        </p>
      </div>
    </div>
  )
}

const styles = {
  page: {
    minHeight: '100vh', display: 'flex', alignItems: 'center',
    justifyContent: 'center', background: 'var(--bg)', padding: 20,
  },
  card: {
    width: '100%', maxWidth: 420,
    background: 'var(--surface)', border: '1px solid var(--border)',
    borderRadius: 16, padding: '40px 36px',
  },
  logo: { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 32 },
  logoIcon: {
    width: 44, height: 44, borderRadius: 10, flexShrink: 0,
    background: 'var(--cyan-15)', border: '1px solid var(--cyan-25)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  logoTitle: { fontSize: 16, fontWeight: 700, color: 'var(--text-1)', lineHeight: 1.2 },
  logoSub:   { fontSize: 11, color: 'var(--text-2)', marginTop: 2 },
  heading:   { fontSize: 22, fontWeight: 700, color: 'var(--text-1)', marginBottom: 6 },
  subheading:{ fontSize: 13, color: 'var(--text-2)', marginBottom: 28 },
  errorBox: {
    padding: '10px 14px', background: 'rgba(239,68,68,0.1)',
    border: '1px solid rgba(239,68,68,0.3)', borderRadius: 8,
    color: '#F87171', fontSize: 13, marginBottom: 20,
  },
  field:  { marginBottom: 18 },
  label:  { display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-2)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' },
  input: {
    width: '100%', padding: '10px 14px', borderRadius: 8, boxSizing: 'border-box',
    background: 'var(--surface-hi)', border: '1px solid var(--border)',
    color: 'var(--text-1)', fontSize: 14, outline: 'none',
  },
  btn: {
    width: '100%', padding: '12px', borderRadius: 8, cursor: 'pointer',
    background: 'var(--cyan)', border: 'none', color: '#000',
    fontSize: 14, fontWeight: 700, marginTop: 8,
  },
  switchText: { textAlign: 'center', fontSize: 13, color: 'var(--text-2)', marginTop: 24 },
  link: { color: 'var(--cyan)', textDecoration: 'none', fontWeight: 600 },
}

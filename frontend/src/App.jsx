import { useEffect, useState, createContext, useContext } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Navbar     from './components/Navbar'
import Dashboard  from './pages/Dashboard'
import Trades     from './pages/Trades'
import Analytics  from './pages/Analytics'
import Monitor    from './pages/Monitor'
import Chart      from './pages/Chart'
import Screener   from './pages/Screener'
import Heatmap    from './pages/Heatmap'
import Strategies      from './pages/Strategies'
import Backtest        from './pages/Backtest'
import Subscription    from './pages/Subscription'
import BacktestHistory from './pages/BacktestHistory'
import PaperTrading    from './pages/PaperTrading'
import Optimizer       from './pages/Optimizer'
import Marketplace     from './pages/Marketplace'
import Journal         from './pages/Journal'
import Alerts          from './pages/Alerts'
import ForwardTest     from './pages/ForwardTest'
import Login           from './pages/Login'
import Register        from './pages/Register'
import { getMarketStatus } from './api'

export const ThemeContext = createContext({ theme: 'dark', toggle: () => {} })
export const useTheme = () => useContext(ThemeContext)

function AppLayout() {
  const { isAuthenticated } = useAuth()
  const [marketOpen, setMarketOpen] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) return
    const check = () =>
      getMarketStatus().then(r => setMarketOpen(r.data.isOpen)).catch(() => {})
    check()
    const t = setInterval(check, 60_000)
    return () => clearInterval(t)
  }, [isAuthenticated])

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg)' }}>
      <Navbar marketOpen={marketOpen} />
      <main style={{ flex: 1, overflowY: 'auto', background: 'var(--bg)' }}>
        <div style={{ maxWidth: 1400, margin: '0 auto', padding: '28px 32px' }}>
          <Routes>
            <Route path="/"           element={<ProtectedRoute><Dashboard  /></ProtectedRoute>} />
            <Route path="/trades"     element={<ProtectedRoute><Trades     /></ProtectedRoute>} />
            <Route path="/analytics"  element={<ProtectedRoute><Analytics  /></ProtectedRoute>} />
            <Route path="/monitor"    element={<ProtectedRoute><Monitor    /></ProtectedRoute>} />
            <Route path="/chart"      element={<ProtectedRoute><Chart      /></ProtectedRoute>} />
            <Route path="/screener"   element={<ProtectedRoute><Screener   /></ProtectedRoute>} />
            <Route path="/heatmap"    element={<ProtectedRoute><Heatmap    /></ProtectedRoute>} />
            <Route path="/strategies"        element={<ProtectedRoute><Strategies      /></ProtectedRoute>} />
            <Route path="/backtest"          element={<ProtectedRoute><Backtest        /></ProtectedRoute>} />
            <Route path="/subscription"      element={<ProtectedRoute><Subscription    /></ProtectedRoute>} />
            <Route path="/backtest-history"  element={<ProtectedRoute><BacktestHistory /></ProtectedRoute>} />
            <Route path="/paper-trading"     element={<ProtectedRoute><PaperTrading    /></ProtectedRoute>} />
            <Route path="/optimizer"         element={<ProtectedRoute><Optimizer       /></ProtectedRoute>} />
            <Route path="/marketplace"       element={<ProtectedRoute><Marketplace     /></ProtectedRoute>} />
            <Route path="/journal"           element={<ProtectedRoute><Journal         /></ProtectedRoute>} />
            <Route path="/alerts"            element={<ProtectedRoute><Alerts          /></ProtectedRoute>} />
            <Route path="/forward-test"      element={<ProtectedRoute><ForwardTest     /></ProtectedRoute>} />
            <Route path="*"                  element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('tradeos-theme') || 'dark')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('tradeos-theme', theme)
  }, [theme])

  const toggle = () => setTheme(t => t === 'dark' ? 'light' : 'dark')

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login"    element={<Login    />} />
            <Route path="/register" element={<Register />} />
            <Route path="/*"        element={<AppLayout />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeContext.Provider>
  )
}

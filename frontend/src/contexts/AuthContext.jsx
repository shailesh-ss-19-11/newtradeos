import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authMe, apiSetToken } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [loading, setLoading] = useState(true)

  const initAuth = useCallback(async () => {
    const token = localStorage.getItem('tradeos-token')
    if (!token) { setLoading(false); return }
    apiSetToken(token)
    try {
      const res = await authMe()
      setUser(res.data.user)
    } catch {
      localStorage.removeItem('tradeos-token')
      apiSetToken(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { initAuth() }, [initAuth])

  const login = useCallback((token, userData) => {
    localStorage.setItem('tradeos-token', token)
    apiSetToken(token)
    setUser(userData)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('tradeos-token')
    apiSetToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

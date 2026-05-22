import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { api, User, TOKEN_KEY } from '../api/client'

interface AuthContextType {
  user: User | null
  token: string | null
  login: (token: string) => Promise<void>
  logout: () => void
  loading: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
    window.location.href = '/login'
  }, [])

  const login = useCallback(async (newToken: string) => {
    localStorage.setItem(TOKEN_KEY, newToken)
    setToken(newToken)
    try {
      const userData = await api.auth.me()
      setUser(userData)
    } catch {
      localStorage.removeItem(TOKEN_KEY)
      setToken(null)
    }
  }, [])

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY)
    if (storedToken) {
      api.auth
        .me()
        .then((userData) => {
          setUser(userData)
          setToken(storedToken)
        })
        .catch(() => {
          localStorage.removeItem(TOKEN_KEY)
          setToken(null)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

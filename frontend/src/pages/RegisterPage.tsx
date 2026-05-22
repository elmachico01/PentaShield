import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Shield, AlertCircle } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../hooks/useAuth'

export default function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirm) {
      setError('Le password non coincidono')
      return
    }
    if (password.length < 8) {
      setError('La password deve contenere almeno 8 caratteri')
      return
    }

    setLoading(true)
    try {
      const data = await api.auth.register(email, password)
      await login(data.access_token)
      navigate('/', { replace: true })
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(axiosErr.response?.data?.detail ?? axiosErr.message ?? 'Errore durante la registrazione')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0f1e] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center justify-center w-16 h-16 bg-cyan-500/10 rounded-2xl border border-cyan-500/30 mb-4">
            <Shield className="w-8 h-8 text-cyan-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">PentaShield</h1>
          <p className="text-gray-500 text-sm mt-1">Sicurezza Automatizzata per PMI</p>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold text-white mb-6">Crea il tuo account</h2>

          {error && (
            <div className="flex items-center gap-2 bg-red-900/30 border border-red-700 text-red-400 rounded-lg px-4 py-3 mb-5 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label" htmlFor="email">Email aziendale</label>
              <input
                id="email"
                type="email"
                className="input"
                placeholder="nome@azienda.it"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <div>
              <label className="label" htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                className="input"
                placeholder="Minimo 8 caratteri"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            <div>
              <label className="label" htmlFor="confirm">Conferma password</label>
              <input
                id="confirm"
                type="password"
                className="input"
                placeholder="Ripeti la password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>

            <button
              type="submit"
              className="btn-primary w-full mt-2"
              disabled={loading}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-[#0a0f1e] border-t-transparent rounded-full animate-spin" />
                  Registrazione in corso...
                </span>
              ) : (
                'Registrati'
              )}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500 mt-6">
            Hai già un account?{' '}
            <Link to="/login" className="text-cyan-400 hover:text-cyan-300 font-medium">
              Accedi
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

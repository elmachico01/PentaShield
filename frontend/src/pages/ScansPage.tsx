import { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Plus, X, ChevronRight, AlertCircle } from 'lucide-react'
import { api, Scan, Target } from '../api/client'
import StatusBadge from '../components/StatusBadge'

const scopeLabels: Record<string, string> = {
  recon: 'Ricognizione',
  network: 'Rete',
  web: 'Web',
  full: 'Completo',
}

const scopeColors: Record<string, string> = {
  recon: 'bg-gray-800 text-gray-400',
  network: 'bg-blue-900/50 text-blue-400',
  web: 'bg-purple-900/50 text-purple-400',
  full: 'bg-cyan-900/50 text-cyan-400',
}

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function ScansPage() {
  const navigate = useNavigate()
  const [scans, setScans] = useState<Scan[]>([])
  const [targets, setTargets] = useState<Target[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // New scan form
  const [showForm, setShowForm] = useState(false)
  const [selectedTarget, setSelectedTarget] = useState('')
  const [selectedScope, setSelectedScope] = useState('full')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchScans = useCallback(async () => {
    try {
      const data = await api.scans.list()
      setScans(data)
    } catch {
      // Silently fail on auto-refresh
    }
  }, [])

  const fetchAll = useCallback(async () => {
    try {
      const [s, t] = await Promise.all([api.scans.list(), api.targets.list()])
      setScans(s)
      setTargets(t)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(axiosErr.response?.data?.detail ?? axiosErr.message ?? 'Errore nel caricamento')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  // Auto-refresh running scans
  useEffect(() => {
    const hasRunning = scans.some((s) => s.status === 'running' || s.status === 'pending')
    if (hasRunning) {
      intervalRef.current = setInterval(fetchScans, 10000)
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [scans, fetchScans])

  const verifiedTargets = targets.filter((t) => t.verified)

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreateError('')
    if (!selectedTarget) {
      setCreateError('Seleziona un target')
      return
    }
    setCreating(true)
    try {
      const scan = await api.scans.create(selectedTarget, selectedScope)
      setScans((prev) => [scan, ...prev])
      setShowForm(false)
      setSelectedTarget('')
      setSelectedScope('full')
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
      setCreateError(axiosErr.response?.data?.detail ?? axiosErr.message ?? 'Errore nella creazione')
    } finally {
      setCreating(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-400 text-sm">Caricamento scansioni...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Scansioni</h1>
          <p className="text-gray-400 text-sm mt-1">Gestisci e monitora le scansioni di sicurezza</p>
        </div>
        <button
          onClick={() => { setShowForm(true); setCreateError('') }}
          className="btn-primary flex items-center gap-2"
          disabled={verifiedTargets.length === 0}
          title={verifiedTargets.length === 0 ? 'Aggiungi e verifica un target prima' : ''}
        >
          <Plus className="w-4 h-4" />
          Avvia nuovo scan
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-400 rounded-xl px-4 py-3 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {verifiedTargets.length === 0 && (
        <div className="bg-amber-900/20 border border-amber-700/50 text-amber-400 rounded-xl px-4 py-3 text-sm">
          Nessun target verificato. Vai alla sezione{' '}
          <button
            onClick={() => navigate('/targets')}
            className="underline hover:text-amber-300 transition-colors"
          >
            Target
          </button>{' '}
          per aggiungere e verificare un dominio.
        </div>
      )}

      {/* New scan form */}
      {showForm && (
        <div className="card border-cyan-500/30">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Nuova scansione</h2>
            <button onClick={() => setShowForm(false)} className="text-gray-500 hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          {createError && (
            <div className="bg-red-900/30 border border-red-700 text-red-400 rounded-lg px-4 py-3 mb-4 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {createError}
            </div>
          )}

          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">Target</label>
                <select
                  className="input"
                  value={selectedTarget}
                  onChange={(e) => setSelectedTarget(e.target.value)}
                  required
                >
                  <option value="">Seleziona un dominio...</option>
                  {verifiedTargets.map((t) => (
                    <option key={t.id} value={t.id}>{t.domain}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Tipo di scansione</label>
                <select
                  className="input"
                  value={selectedScope}
                  onChange={(e) => setSelectedScope(e.target.value)}
                >
                  <option value="recon">Ricognizione — solo info pubbliche</option>
                  <option value="network">Rete — porte e servizi</option>
                  <option value="web">Web — vulnerabilità applicative</option>
                  <option value="full">Completo — analisi approfondita</option>
                </select>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button type="submit" className="btn-primary" disabled={creating}>
                {creating ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-[#0a0f1e] border-t-transparent rounded-full animate-spin" />
                    Avvio in corso...
                  </span>
                ) : (
                  'Avvia scansione'
                )}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">
                Annulla
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Scans table */}
      {scans.length === 0 ? (
        <div className="card text-center py-16">
          <Search className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-300 font-medium">Nessuna scansione avviata</p>
          <p className="text-gray-500 text-sm mt-2">
            {verifiedTargets.length > 0
              ? 'Avvia la tua prima scansione di sicurezza'
              : 'Prima verifica un target, poi avvia la scansione'}
          </p>
        </div>
      ) : (
        <div className="card p-0">
          <div className="px-6 py-4 border-b border-[#1f2937]">
            <h2 className="text-base font-semibold text-white">
              Tutte le scansioni{' '}
              <span className="text-gray-500 font-normal text-sm">({scans.length})</span>
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#1f2937]">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Dominio</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tipo</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stato</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Avviata il</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Azione</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2937]">
                {scans.map((scan) => (
                  <tr
                    key={scan.id}
                    className="hover:bg-[#1f2937]/40 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <span className="text-white font-medium">{scan.target}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${scopeColors[scan.scope] ?? 'bg-gray-800 text-gray-400'}`}>
                        {scopeLabels[scan.scope] ?? scan.scope}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={scan.status} />
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-400">
                      {formatDate(scan.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => navigate(`/scans/${scan.id}`)}
                        className="inline-flex items-center gap-1.5 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                      >
                        Dettagli
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

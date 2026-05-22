import { useEffect, useState, useCallback } from 'react'
import { Globe, CheckCircle, AlertTriangle, Copy, Trash2, Shield, Plus, X } from 'lucide-react'
import { api, Target } from '../api/client'

function formatDate(s: string) {
  return new Date(s).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

interface VerifyResult {
  targetId: string
  verified: boolean
  detail: string
}

export default function TargetsPage() {
  const [targets, setTargets] = useState<Target[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Add form
  const [showForm, setShowForm] = useState(false)
  const [newDomain, setNewDomain] = useState('')
  const [newMethod, setNewMethod] = useState('dns_txt')
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState('')

  // Verify / delete state
  const [verifying, setVerifying] = useState<string | null>(null)
  const [verifyResults, setVerifyResults] = useState<Record<string, VerifyResult>>({})
  const [deleting, setDeleting] = useState<string | null>(null)

  // Copy state
  const [copied, setCopied] = useState<string | null>(null)

  const fetchTargets = useCallback(async () => {
    try {
      const data = await api.targets.list()
      setTargets(data)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(axiosErr.response?.data?.detail ?? axiosErr.message ?? 'Errore nel caricamento')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTargets()
  }, [fetchTargets])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    setAddError('')
    if (!newDomain.trim()) return
    setAdding(true)
    try {
      const target = await api.targets.create(newDomain.trim(), newMethod)
      setTargets((prev) => [target, ...prev])
      setNewDomain('')
      setNewMethod('dns_txt')
      setShowForm(false)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
      setAddError(axiosErr.response?.data?.detail ?? axiosErr.message ?? 'Errore nella creazione')
    } finally {
      setAdding(false)
    }
  }

  const handleVerify = async (id: string) => {
    setVerifying(id)
    try {
      const result = await api.targets.verify(id)
      setVerifyResults((prev) => ({ ...prev, [id]: { targetId: id, ...result } }))
      if (result.verified) {
        setTargets((prev) =>
          prev.map((t) => (t.id === id ? { ...t, verified: true, verified_at: new Date().toISOString() } : t))
        )
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
      setVerifyResults((prev) => ({
        ...prev,
        [id]: { targetId: id, verified: false, detail: axiosErr.response?.data?.detail ?? axiosErr.message ?? 'Errore di verifica' },
      }))
    } finally {
      setVerifying(null)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Eliminare questo target? Tutte le scansioni associate verranno rimosse.')) return
    setDeleting(id)
    try {
      await api.targets.delete(id)
      setTargets((prev) => prev.filter((t) => t.id !== id))
      setVerifyResults((prev) => {
        const next = { ...prev }
        delete next[id]
        return next
      })
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
      alert(axiosErr.response?.data?.detail ?? axiosErr.message ?? 'Errore durante l\'eliminazione')
    } finally {
      setDeleting(null)
    }
  }

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key)
      setTimeout(() => setCopied(null), 2000)
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-400 text-sm">Caricamento target...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Target</h1>
          <p className="text-gray-400 text-sm mt-1">Gestisci i domini da monitorare</p>
        </div>
        <button
          onClick={() => { setShowForm(true); setAddError('') }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Aggiungi target
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-400 rounded-xl px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Add form */}
      {showForm && (
        <div className="card border-cyan-500/30">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Nuovo target</h2>
            <button onClick={() => setShowForm(false)} className="text-gray-500 hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          {addError && (
            <div className="bg-red-900/30 border border-red-700 text-red-400 rounded-lg px-4 py-3 mb-4 text-sm">
              {addError}
            </div>
          )}

          <form onSubmit={handleAdd} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">Dominio</label>
                <input
                  type="text"
                  className="input"
                  placeholder="esempio.it"
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="label">Metodo di verifica</label>
                <select
                  className="input"
                  value={newMethod}
                  onChange={(e) => setNewMethod(e.target.value)}
                >
                  <option value="dns_txt">Record DNS TXT</option>
                  <option value="file">File HTTP</option>
                </select>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button type="submit" className="btn-primary" disabled={adding}>
                {adding ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-[#0a0f1e] border-t-transparent rounded-full animate-spin" />
                    Aggiunta in corso...
                  </span>
                ) : (
                  'Aggiungi'
                )}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">
                Annulla
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Targets list */}
      {targets.length === 0 ? (
        <div className="card text-center py-16">
          <Globe className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-300 font-medium">Nessun target aggiunto</p>
          <p className="text-gray-500 text-sm mt-2">Aggiungi il dominio della tua azienda per iniziare</p>
          <button
            onClick={() => setShowForm(true)}
            className="btn-primary mt-4"
          >
            Aggiungi il primo target
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {targets.map((target) => {
            const vResult = verifyResults[target.id]
            return (
              <div key={target.id} className="card space-y-4">
                {/* Header row */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`flex items-center justify-center w-10 h-10 rounded-lg border flex-shrink-0 ${
                      target.verified
                        ? 'bg-emerald-500/10 border-emerald-500/30'
                        : 'bg-amber-500/10 border-amber-500/30'
                    }`}>
                      {target.verified
                        ? <CheckCircle className="w-5 h-5 text-emerald-400" />
                        : <AlertTriangle className="w-5 h-5 text-amber-400" />
                      }
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-white font-semibold text-lg truncate">{target.domain}</h3>
                      <div className="flex items-center gap-3 mt-0.5">
                        {target.verified ? (
                          <span className="text-xs text-emerald-400 flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" /> Verificato
                            {target.verified_at && ` — ${formatDate(target.verified_at)}`}
                          </span>
                        ) : (
                          <span className="text-xs text-amber-400 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" /> Non verificato
                          </span>
                        )}
                        <span className="text-xs text-gray-500">
                          {target.verification_method === 'dns_txt' ? 'DNS TXT' : 'File HTTP'}
                        </span>
                        <span className="text-xs text-gray-600">
                          Aggiunto il {formatDate(target.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {!target.verified && (
                      <button
                        onClick={() => handleVerify(target.id)}
                        disabled={verifying === target.id}
                        className="btn-secondary text-sm flex items-center gap-1.5"
                      >
                        {verifying === target.id ? (
                          <>
                            <span className="w-3.5 h-3.5 border border-white border-t-transparent rounded-full animate-spin" />
                            Verifica...
                          </>
                        ) : (
                          <>
                            <Shield className="w-3.5 h-3.5" />
                            Verifica
                          </>
                        )}
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(target.id)}
                      disabled={deleting === target.id}
                      className="btn-danger text-sm flex items-center gap-1.5"
                    >
                      {deleting === target.id ? (
                        <span className="w-3.5 h-3.5 border border-white border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <Trash2 className="w-3.5 h-3.5" />
                      )}
                      Elimina
                    </button>
                  </div>
                </div>

                {/* Verify result */}
                {vResult && (
                  <div className={`rounded-lg px-4 py-3 text-sm ${
                    vResult.verified
                      ? 'bg-emerald-900/30 border border-emerald-700 text-emerald-400'
                      : 'bg-red-900/30 border border-red-700 text-red-400'
                  }`}>
                    {vResult.verified ? '✓ ' : '✗ '}{vResult.detail}
                  </div>
                )}

                {/* Verification instructions */}
                {!target.verified && (
                  <div className="bg-[#0a0f1e] border border-[#1f2937] rounded-lg p-4 space-y-3">
                    <div>
                      <p className="text-gray-400 text-sm font-medium mb-2">
                        {target.verification_method === 'dns_txt'
                          ? 'Aggiungi il seguente record DNS TXT al tuo dominio:'
                          : 'Carica il seguente file nella root del tuo dominio:'}
                      </p>
                      <div className="flex items-center gap-2 bg-[#111827] border border-[#374151] rounded-lg px-3 py-2">
                        <code className="text-xs text-cyan-300 font-mono flex-1 break-all">
                          {target.verification_method === 'dns_txt'
                            ? `pentashield-verify=${target.verification_token}`
                            : `/.well-known/pentashield-verify.txt → ${target.verification_token}`}
                        </code>
                        <button
                          onClick={() => handleCopy(
                            target.verification_method === 'dns_txt'
                              ? `pentashield-verify=${target.verification_token}`
                              : target.verification_token,
                            target.id
                          )}
                          className="flex-shrink-0 text-gray-500 hover:text-cyan-400 transition-colors"
                          title="Copia"
                        >
                          {copied === target.id
                            ? <CheckCircle className="w-4 h-4 text-emerald-400" />
                            : <Copy className="w-4 h-4" />
                          }
                        </button>
                      </div>
                    </div>
                    {target.verification_method === 'dns_txt' && (
                      <p className="text-xs text-gray-500">
                        Nota: la propagazione DNS può richiedere fino a 48 ore. Attendi prima di verificare.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

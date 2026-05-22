import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { api, Scan, Finding } from '../api/client'
import SeverityBadge from '../components/SeverityBadge'
import StatusBadge from '../components/StatusBadge'

const SEV_COLORS: Record<string, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#f59e0b',
  LOW: '#3b82f6',
  INFO: '#6b7280',
}

const SEV_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']

function formatDate(s: string | null) {
  if (!s) return '—'
  return new Date(s).toLocaleDateString('it-IT', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

interface ExpandedFinding { [id: string]: boolean }

export default function ScanDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [scan, setScan] = useState<Scan | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading, setLoading] = useState(true)
  const [activeSev, setActiveSev] = useState<string>('ALL')
  const [expanded, setExpanded] = useState<ExpandedFinding>({})
  const [triggeringReport, setTriggeringReport] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchScan = useCallback(async () => {
    if (!id) return
    try {
      const s = await api.scans.get(id)
      setScan(s)
      return s
    } catch { return null }
  }, [id])

  const fetchFindings = useCallback(async () => {
    if (!id) return
    try {
      const f = await api.scans.getFindings(id)
      setFindings(f)
    } catch { /* ignore */ }
  }, [id])

  useEffect(() => {
    if (!id) return
    Promise.all([
      api.scans.get(id),
      api.scans.getFindings(id),
    ]).then(([s, f]) => {
      setScan(s)
      setFindings(f)
    }).finally(() => setLoading(false))
  }, [id])

  // Poll while running
  useEffect(() => {
    if (!scan) return
    if (scan.status === 'running' || scan.status === 'pending') {
      intervalRef.current = setInterval(async () => {
        const updated = await fetchScan()
        if (updated && updated.status !== 'running' && updated.status !== 'pending') {
          clearInterval(intervalRef.current!)
          fetchFindings()
        }
      }, 8000)
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [scan?.status, fetchScan, fetchFindings])

  const handleGenerateReport = async () => {
    if (!id) return
    setTriggeringReport(true)
    try {
      await api.reports.trigger(id)
      navigate(`/scans/${id}/report`)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      const msg = e.response?.data?.detail ?? e.message ?? ''
      // If 409 (already exists), just navigate
      navigate(`/scans/${id}/report`)
      console.log('Report trigger:', msg)
    } finally {
      setTriggeringReport(false)
    }
  }

  const toggleExpand = (fid: string) => setExpanded((prev) => ({ ...prev, [fid]: !prev[fid] }))

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!scan) {
    return <div className="text-red-400">Scansione non trovata.</div>
  }

  // Severity counts for chart
  const sevCounts: Record<string, number> = {}
  findings.forEach((f) => { sevCounts[f.severity] = (sevCounts[f.severity] || 0) + 1 })
  const chartData = SEV_ORDER.filter((s) => sevCounts[s]).map((s) => ({ name: s, value: sevCounts[s] }))

  const filteredFindings = activeSev === 'ALL' ? findings : findings.filter((f) => f.severity === activeSev)

  const scopeLabels: Record<string, string> = { recon: 'Ricognizione', network: 'Rete', web: 'Web', full: 'Completo' }
  const scopeColors: Record<string, string> = {
    recon: 'bg-gray-800 text-gray-400', network: 'bg-blue-900/50 text-blue-400',
    web: 'bg-purple-900/50 text-purple-400', full: 'bg-cyan-900/50 text-cyan-400',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <button
            onClick={() => navigate('/scans')}
            className="flex items-center gap-1.5 text-gray-500 hover:text-white transition-colors text-sm mb-3"
          >
            <ArrowLeft className="w-4 h-4" /> Tutte le scansioni
          </button>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold text-white">{scan.target}</h1>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${scopeColors[scan.scope] ?? 'bg-gray-800 text-gray-400'}`}>
              {scopeLabels[scan.scope] ?? scan.scope}
            </span>
            <StatusBadge status={scan.status} />
          </div>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
            <span>Avviata: {formatDate(scan.created_at)}</span>
            {scan.finished_at && <span>Completata: {formatDate(scan.finished_at)}</span>}
          </div>
        </div>
        {scan.status === 'completed' && (
          <button
            onClick={handleGenerateReport}
            disabled={triggeringReport}
            className="btn-primary flex items-center gap-2 flex-shrink-0"
          >
            {triggeringReport ? (
              <span className="w-4 h-4 border-2 border-[#0a0f1e] border-t-transparent rounded-full animate-spin" />
            ) : (
              <FileText className="w-4 h-4" />
            )}
            {triggeringReport ? 'Avvio...' : 'Report AI'}
          </button>
        )}
      </div>

      {/* Running progress */}
      {(scan.status === 'running' || scan.status === 'pending') && (
        <div className="card border-blue-500/20">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse" />
            <span className="text-blue-400 font-medium text-sm">Scansione in corso...</span>
          </div>
          <div className="w-full bg-[#1f2937] rounded-full h-2">
            <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2 rounded-full animate-pulse w-2/3 transition-all" />
          </div>
          <p className="text-gray-500 text-xs mt-2">I risultati appariranno man mano che la scansione procede</p>
        </div>
      )}

      {/* Findings */}
      {findings.length > 0 && (
        <>
          {/* Chart + filter row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="card lg:col-span-1">
              <h3 className="text-sm font-medium text-gray-400 mb-4">Vulnerabilità per gravità</h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={chartData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} dataKey="value" paddingAngle={2}>
                    {chartData.map((entry) => (
                      <Cell key={entry.name} fill={SEV_COLORS[entry.name] ?? '#6b7280'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 8 }}
                    labelStyle={{ color: '#e5e7eb' }}
                    itemStyle={{ color: '#9ca3af' }}
                  />
                  <Legend
                    formatter={(value) => <span className="text-xs text-gray-400">{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="card lg:col-span-2">
              <h3 className="text-sm font-medium text-gray-400 mb-4">Riepilogo</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {SEV_ORDER.map((sev) => (
                  <div key={sev} className="bg-[#0a0f1e] border border-[#1f2937] rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold" style={{ color: SEV_COLORS[sev] }}>
                      {sevCounts[sev] ?? 0}
                    </p>
                    <SeverityBadge severity={sev} />
                  </div>
                ))}
                <div className="bg-[#0a0f1e] border border-[#1f2937] rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-white">{findings.length}</p>
                  <span className="text-xs text-gray-500">Totali</span>
                </div>
              </div>
            </div>
          </div>

          {/* Filter tabs */}
          <div className="card p-0">
            <div className="flex overflow-x-auto border-b border-[#1f2937]">
              {['ALL', ...SEV_ORDER].map((sev) => {
                const count = sev === 'ALL' ? findings.length : (sevCounts[sev] ?? 0)
                const isActive = activeSev === sev
                return (
                  <button
                    key={sev}
                    onClick={() => setActiveSev(sev)}
                    className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium whitespace-nowrap transition-colors border-b-2 -mb-px ${
                      isActive
                        ? 'border-cyan-500 text-cyan-400'
                        : 'border-transparent text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    {sev === 'ALL' ? 'Tutti' : <SeverityBadge severity={sev} />}
                    <span className={`px-1.5 py-0.5 rounded text-xs ${isActive ? 'bg-cyan-500/20 text-cyan-400' : 'bg-[#1f2937] text-gray-500'}`}>
                      {count}
                    </span>
                  </button>
                )
              })}
            </div>

            {/* Findings table */}
            <div className="divide-y divide-[#1f2937]">
              {filteredFindings.length === 0 ? (
                <div className="py-12 text-center text-gray-500 text-sm">Nessuna vulnerabilità in questa categoria</div>
              ) : (
                filteredFindings.map((f) => (
                  <div key={f.id} className="hover:bg-[#1f2937]/30 transition-colors">
                    <button
                      onClick={() => toggleExpand(f.id)}
                      className="w-full px-6 py-4 text-left flex items-start gap-4"
                    >
                      <div className="flex-shrink-0 pt-0.5">
                        <SeverityBadge severity={f.severity} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-white text-sm font-medium truncate">{f.title}</p>
                        <div className="flex items-center gap-3 mt-1 flex-wrap">
                          <span className="text-xs text-gray-500">{f.affected_component}</span>
                          {f.cvss_score != null && (
                            <span className="text-xs text-gray-600">CVSS {f.cvss_score.toFixed(1)}</span>
                          )}
                          {f.nis2_control && (
                            <span className="text-xs bg-purple-900/40 text-purple-400 px-2 py-0.5 rounded-full">
                              NIS2 {f.nis2_control}
                            </span>
                          )}
                          <span className="text-xs text-gray-700 capitalize">{f.source}</span>
                        </div>
                      </div>
                      <div className="flex-shrink-0 text-gray-600">
                        {expanded[f.id] ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </div>
                    </button>
                    {expanded[f.id] && (
                      <div className="px-6 pb-5 space-y-3">
                        {f.description && (
                          <div>
                            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1 font-medium">Descrizione</p>
                            <p className="text-sm text-gray-300 whitespace-pre-wrap">{f.description}</p>
                          </div>
                        )}
                        {f.fix_suggestion && (
                          <div className="bg-emerald-900/20 border border-emerald-900/50 rounded-lg p-3">
                            <p className="text-xs text-emerald-500 uppercase tracking-wider mb-1 font-medium">Rimedio</p>
                            <p className="text-sm text-emerald-300 whitespace-pre-wrap">{f.fix_suggestion}</p>
                          </div>
                        )}
                        {f.proof && (
                          <div>
                            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1 font-medium">Prova</p>
                            <pre className="text-xs text-gray-400 bg-[#0a0f1e] border border-[#1f2937] rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all">{f.proof}</pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}

      {findings.length === 0 && scan.status === 'completed' && (
        <div className="card text-center py-16">
          <p className="text-gray-400 font-medium">Nessuna vulnerabilità trovata</p>
          <p className="text-gray-600 text-sm mt-1">La scansione è completata senza rilevare problemi di sicurezza</p>
        </div>
      )}
    </div>
  )
}

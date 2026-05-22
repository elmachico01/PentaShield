import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, AlertTriangle, Shield, Clock, CheckCircle } from 'lucide-react'
import { api, Report } from '../api/client'

const RISK_COLORS: Record<string, string> = {
  CRITICO: 'bg-red-900/40 border-red-700 text-red-400',
  ALTO: 'bg-orange-900/40 border-orange-700 text-orange-400',
  MEDIO: 'bg-amber-900/40 border-amber-700 text-amber-400',
  BASSO: 'bg-blue-900/40 border-blue-700 text-blue-400',
  ACCETTABILE: 'bg-emerald-900/40 border-emerald-700 text-emerald-400',
}

const SEV_COLORS: Record<string, string> = {
  CRITICAL: 'text-red-400 bg-red-900/20 border-red-800',
  HIGH: 'text-orange-400 bg-orange-900/20 border-orange-800',
  MEDIUM: 'text-amber-400 bg-amber-900/20 border-amber-800',
  LOW: 'text-blue-400 bg-blue-900/20 border-blue-800',
  INFO: 'text-gray-400 bg-gray-800/50 border-gray-700',
}

const TIMEFRAME_LABELS: Record<string, string> = {
  immediato: 'Immediato (72h)',
  '30_giorni': '30 giorni',
  '90_giorni': '90 giorni',
}
const TIMEFRAME_COLORS: Record<string, string> = {
  immediato: 'border-red-700/50 bg-red-900/10',
  '30_giorni': 'border-amber-700/50 bg-amber-900/10',
  '90_giorni': 'border-blue-700/50 bg-blue-900/10',
}

interface AISummary {
  executive_summary?: string
  risk_level?: string
  findings_by_severity?: Record<string, number>
  top_priorities?: Array<{
    rank: number; title: string; severity: string
    cvss_score?: number; affected_component: string; fix_suggestion: string; nis2_control?: string
  }>
  nis2_gap_analysis?: string
  technical_details?: string
  remediation_roadmap?: Array<{ timeframe: string; action: string; priority: string }>
}

export default function ReportPage() {
  const { id: scanId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [showTech, setShowTech] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchReport = useCallback(async () => {
    if (!scanId) return
    try {
      const r = await api.reports.get(scanId)
      setReport(r)
      return r
    } catch { return null }
  }, [scanId])

  useEffect(() => {
    if (!scanId) return
    api.reports.get(scanId)
      .then((r) => { setReport(r) })
      .catch(() => { /* will show error state */ })
      .finally(() => setLoading(false))
  }, [scanId])

  // Poll while pending/generating
  useEffect(() => {
    if (!report) return
    if (report.status === 'pending' || report.status === 'generating') {
      intervalRef.current = setInterval(async () => {
        const updated = await fetchReport()
        if (updated && updated.status !== 'pending' && updated.status !== 'generating') {
          clearInterval(intervalRef.current!)
        }
      }, 3000)
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [report?.status, fetchReport])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const back = (
    <button
      onClick={() => navigate(`/scans/${scanId}`)}
      className="flex items-center gap-1.5 text-gray-500 hover:text-white transition-colors text-sm mb-5"
    >
      <ArrowLeft className="w-4 h-4" /> Torna alla scansione
    </button>
  )

  if (!report) {
    return (
      <div className="space-y-4">
        {back}
        <div className="bg-red-900/30 border border-red-700 text-red-400 rounded-xl px-5 py-4">
          Report non trovato.
        </div>
      </div>
    )
  }

  if (report.status === 'pending' || report.status === 'generating') {
    return (
      <div className="space-y-4">
        {back}
        <div className="card text-center py-20">
          <div className="flex items-center justify-center w-16 h-16 bg-purple-500/10 border border-purple-500/30 rounded-2xl mx-auto mb-5">
            <Shield className="w-8 h-8 text-purple-400 animate-pulse" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Generazione report in corso</h2>
          <p className="text-gray-400 text-sm">
            L'AI sta analizzando le vulnerabilità e generando il report in italiano...
          </p>
          <div className="mt-6 flex items-center justify-center gap-2 text-purple-400 text-sm">
            <div className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            Attendere prego
          </div>
        </div>
      </div>
    )
  }

  if (report.status === 'failed') {
    return (
      <div className="space-y-4">
        {back}
        <div className="bg-red-900/30 border border-red-700 rounded-xl px-5 py-4">
          <div className="flex items-center gap-2 text-red-400 font-semibold mb-1">
            <AlertTriangle className="w-5 h-5" /> Generazione report fallita
          </div>
          <p className="text-red-300 text-sm">{report.error_message ?? 'Errore sconosciuto'}</p>
        </div>
      </div>
    )
  }

  const summary = report.ai_summary as AISummary | null
  if (!summary) return <div className="text-gray-400">Nessun contenuto nel report.</div>

  const riskClass = RISK_COLORS[summary.risk_level ?? ''] ?? 'bg-gray-800 border-gray-600 text-gray-400'
  const sevMap = summary.findings_by_severity ?? {}
  const roadmap = summary.remediation_roadmap ?? []
  const grouped: Record<string, typeof roadmap> = {}
  roadmap.forEach((item) => { grouped[item.timeframe] = [...(grouped[item.timeframe] ?? []), item] })

  return (
    <div className="space-y-6 max-w-5xl">
      {back}

      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-white">Report di Sicurezza</h1>
        {report.completed_at && (
          <span className="flex items-center gap-1.5 text-xs text-gray-500">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
            Generato il {new Date(report.completed_at).toLocaleDateString('it-IT')}
          </span>
        )}
      </div>

      {/* Risk level banner */}
      <div className={`border rounded-xl px-6 py-5 flex items-center gap-4 ${riskClass}`}>
        <Shield className="w-8 h-8 flex-shrink-0" />
        <div>
          <p className="text-xs uppercase tracking-widest font-bold opacity-70 mb-0.5">Livello di rischio complessivo</p>
          <p className="text-2xl font-bold">{summary.risk_level ?? '—'}</p>
        </div>
      </div>

      {/* Severity stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {['CRITICAL','HIGH','MEDIUM','LOW','INFO'].map((sev) => (
          <div key={sev} className={`border rounded-xl p-4 text-center ${SEV_COLORS[sev]}`}>
            <p className="text-2xl font-bold">{sevMap[sev] ?? 0}</p>
            <p className="text-xs font-semibold mt-1 uppercase tracking-wide opacity-80">{sev}</p>
          </div>
        ))}
      </div>

      {/* Executive summary */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Shield className="w-5 h-5 text-cyan-400" /> Sommario Esecutivo
        </h2>
        <p className="text-gray-300 leading-relaxed whitespace-pre-wrap">{summary.executive_summary}</p>
      </div>

      {/* Top priorities */}
      {summary.top_priorities && summary.top_priorities.length > 0 && (
        <div className="card p-0">
          <div className="px-6 py-4 border-b border-[#1f2937]">
            <h2 className="text-lg font-semibold text-white">Vulnerabilità Prioritarie</h2>
          </div>
          <div className="divide-y divide-[#1f2937]">
            {summary.top_priorities.map((p) => (
              <div key={p.rank} className="px-6 py-4 flex items-start gap-4">
                <div className="flex-shrink-0 w-7 h-7 rounded-full bg-[#1f2937] flex items-center justify-center text-xs font-bold text-gray-400">
                  {p.rank}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start gap-2 flex-wrap">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${SEV_COLORS[p.severity] ?? 'text-gray-400 bg-gray-800 border-gray-700'}`}>
                      {p.severity}
                    </span>
                    {p.cvss_score != null && (
                      <span className="text-xs text-gray-600">CVSS {p.cvss_score.toFixed(1)}</span>
                    )}
                    {p.nis2_control && (
                      <span className="text-xs bg-purple-900/40 text-purple-400 px-2 py-0.5 rounded-full border border-purple-800/50">
                        NIS2 {p.nis2_control}
                      </span>
                    )}
                  </div>
                  <p className="text-white font-medium mt-1.5 text-sm">{p.title}</p>
                  <p className="text-gray-500 text-xs mt-0.5">{p.affected_component}</p>
                  <div className="mt-2 bg-emerald-900/20 border border-emerald-900/50 rounded-lg px-3 py-2">
                    <p className="text-xs text-emerald-500 font-medium mb-0.5">Rimedio</p>
                    <p className="text-xs text-emerald-300">{p.fix_suggestion}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* NIS2 gap analysis */}
      {summary.nis2_gap_analysis && (
        <div className="card border-purple-800/30">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-purple-400" /> Analisi Gap NIS2 — Art. 21
          </h2>
          <p className="text-gray-300 leading-relaxed whitespace-pre-wrap text-sm">{summary.nis2_gap_analysis}</p>
        </div>
      )}

      {/* Remediation roadmap */}
      {roadmap.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-white">Piano di Rimedio</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {['immediato', '30_giorni', '90_giorni'].map((tf) => {
              const items = grouped[tf] ?? []
              return (
                <div key={tf} className={`border rounded-xl p-4 ${TIMEFRAME_COLORS[tf]}`}>
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-semibold text-white">{TIMEFRAME_LABELS[tf]}</span>
                  </div>
                  {items.length === 0 ? (
                    <p className="text-xs text-gray-600">Nessuna azione</p>
                  ) : (
                    <ul className="space-y-2">
                      {items.map((item, i) => (
                        <li key={i} className="flex items-start gap-2 text-xs text-gray-300">
                          <span className="flex-shrink-0 mt-0.5 w-1.5 h-1.5 rounded-full bg-gray-500 mt-1.5" />
                          {item.action}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Technical details (collapsible) */}
      {summary.technical_details && (
        <div className="card">
          <button
            onClick={() => setShowTech(!showTech)}
            className="w-full flex items-center justify-between text-left"
          >
            <h2 className="text-lg font-semibold text-white">Dettagli Tecnici</h2>
            <span className="text-gray-500 text-sm">{showTech ? 'Nascondi' : 'Mostra'}</span>
          </button>
          {showTech && (
            <pre className="mt-4 text-xs text-gray-400 whitespace-pre-wrap leading-relaxed font-mono bg-[#0a0f1e] border border-[#1f2937] rounded-lg p-4 overflow-x-auto">
              {summary.technical_details}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

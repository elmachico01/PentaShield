import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Globe, Activity, AlertTriangle, CheckCircle, ChevronRight } from 'lucide-react'
import { api, Target, Scan } from '../api/client'
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

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: number | string
  color: string
}

function StatCard({ icon, label, value, color }: StatCardProps) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`flex items-center justify-center w-12 h-12 rounded-xl ${color}`}>
        {icon}
      </div>
      <div>
        <p className="text-gray-400 text-sm">{label}</p>
        <p className="text-2xl font-bold text-white mt-0.5">{value}</p>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const [targets, setTargets] = useState<Target[]>([])
  const [scans, setScans] = useState<Scan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    try {
      const [t, s] = await Promise.all([api.targets.list(), api.scans.list()])
      setTargets(t)
      setScans(s)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(axiosErr.response?.data?.detail ?? axiosErr.message ?? 'Errore nel caricamento')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const activeScans = scans.filter((s) => s.status === 'running' || s.status === 'pending').length
  const completedScans = scans.filter((s) => s.status === 'completed').length
  const recentScans = [...scans].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-400 text-sm">Caricamento dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/30 border border-red-700 text-red-400 rounded-xl px-6 py-4">
        <p className="font-medium">Errore nel caricamento</p>
        <p className="text-sm mt-1 opacity-80">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">Panoramica della sicurezza della tua infrastruttura</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={<Globe className="w-6 h-6 text-cyan-400" />}
          label="Target totali"
          value={targets.length}
          color="bg-cyan-500/10 border border-cyan-500/20"
        />
        <StatCard
          icon={<Activity className="w-6 h-6 text-purple-400" />}
          label="Scansioni attive"
          value={activeScans}
          color="bg-purple-500/10 border border-purple-500/20"
        />
        <StatCard
          icon={<AlertTriangle className="w-6 h-6 text-amber-400" />}
          label="Scansioni totali"
          value={scans.length}
          color="bg-amber-500/10 border border-amber-500/20"
        />
        <StatCard
          icon={<CheckCircle className="w-6 h-6 text-emerald-400" />}
          label="Scansioni completate"
          value={completedScans}
          color="bg-emerald-500/10 border border-emerald-500/20"
        />
      </div>

      {/* Recent scans */}
      <div className="card p-0">
        <div className="px-6 py-4 border-b border-[#1f2937] flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Scansioni recenti</h2>
          <button
            onClick={() => navigate('/scans')}
            className="text-sm text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
          >
            Vedi tutte <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {recentScans.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <Activity className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">Nessuna scansione ancora avviata</p>
            <button
              onClick={() => navigate('/scans')}
              className="btn-primary mt-4 text-sm"
            >
              Avvia la prima scansione
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#1f2937]">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Target</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Scope</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stato</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data</th>
                  <th className="px-6 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2937]">
                {recentScans.map((scan) => (
                  <tr
                    key={scan.id}
                    className="hover:bg-[#1f2937]/40 cursor-pointer transition-colors"
                    onClick={() => navigate(`/scans/${scan.id}`)}
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
                      <ChevronRight className="w-4 h-4 text-gray-600 ml-auto" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick tips */}
      {targets.length === 0 && (
        <div className="card border-cyan-500/30 bg-cyan-500/5">
          <div className="flex items-start gap-4">
            <div className="flex items-center justify-center w-10 h-10 bg-cyan-500/10 rounded-xl border border-cyan-500/30 flex-shrink-0">
              <Globe className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <h3 className="text-white font-semibold">Inizia aggiungendo un target</h3>
              <p className="text-gray-400 text-sm mt-1">
                Aggiungi il dominio della tua azienda per avviare la prima scansione di sicurezza.
              </p>
              <button
                onClick={() => navigate('/targets')}
                className="btn-primary mt-3 text-sm"
              >
                Aggiungi target
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

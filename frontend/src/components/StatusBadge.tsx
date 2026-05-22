interface StatusBadgeProps {
  status: string
}

const colors: Record<string, string> = {
  pending: 'bg-gray-800 text-gray-400',
  running: 'bg-blue-900/50 text-blue-400 animate-pulse',
  completed: 'bg-emerald-900/50 text-emerald-400',
  failed: 'bg-red-900/50 text-red-400',
  cancelled: 'bg-gray-800 text-gray-500',
}

const labels: Record<string, string> = {
  pending: 'In attesa',
  running: 'In corso',
  completed: 'Completato',
  failed: 'Fallito',
  cancelled: 'Annullato',
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colorClass = colors[status] ?? 'bg-gray-800 text-gray-400'
  const label = labels[status] ?? status
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${colorClass}`}>
      {label}
    </span>
  )
}

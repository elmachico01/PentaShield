interface SeverityBadgeProps {
  severity: string
}

const colors: Record<string, string> = {
  CRITICAL: 'bg-red-900/50 text-red-400 border border-red-700',
  HIGH: 'bg-orange-900/50 text-orange-400 border border-orange-700',
  MEDIUM: 'bg-amber-900/50 text-amber-400 border border-amber-700',
  LOW: 'bg-blue-900/50 text-blue-400 border border-blue-700',
  INFO: 'bg-gray-800 text-gray-400 border border-gray-600',
}

const labels: Record<string, string> = {
  CRITICAL: 'Critico',
  HIGH: 'Alto',
  MEDIUM: 'Medio',
  LOW: 'Basso',
  INFO: 'Info',
}

export default function SeverityBadge({ severity }: SeverityBadgeProps) {
  const colorClass = colors[severity] ?? 'bg-gray-800 text-gray-400 border border-gray-600'
  const label = labels[severity] ?? severity
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${colorClass}`}>
      {label}
    </span>
  )
}

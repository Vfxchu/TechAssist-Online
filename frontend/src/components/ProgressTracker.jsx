const STAGES = [
  { key: 'diagnosing',   label: 'Diagnosing' },
  { key: 'understanding', label: 'Understanding' },
  { key: 'suggesting',   label: 'Suggesting' },
  { key: 'resolving',    label: 'Resolving' },
  { key: 'closed',       label: 'Closed' },
]

function getStageIndex(ticket) {
  if (ticket.status === 'Resolved' || ticket.status === 'Closed') return 4
  if (ticket.status === 'Escalated') return 4
  const attempts = ticket.failed_attempts || 0
  if (attempts === 0 && ticket.category === 'Other') return 0
  if (attempts === 0) return 1
  if (attempts < 3) return 2
  return 3
}

export default function ProgressTracker({ ticket }) {
  const current = getStageIndex(ticket)

  return (
    <div className="flex items-center gap-0 w-full">
      {STAGES.map((stage, idx) => {
        const isComplete = idx < current
        const isActive = idx === current
        const isLast = idx === STAGES.length - 1

        return (
          <div key={stage.key} className="flex items-center flex-1 min-w-0">
            <div className="flex flex-col items-center flex-shrink-0">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                  isComplete
                    ? 'bg-indigo-500 text-white'
                    : isActive
                    ? 'bg-indigo-600 text-white ring-2 ring-indigo-400 ring-offset-1 ring-offset-slate-900'
                    : 'bg-slate-700 text-slate-500'
                }`}
              >
                {isComplete ? '✓' : idx + 1}
              </div>
              <span
                className={`text-xs mt-1 whitespace-nowrap ${
                  isActive ? 'text-indigo-400 font-medium' : isComplete ? 'text-slate-400' : 'text-slate-600'
                }`}
              >
                {stage.label}
              </span>
            </div>
            {!isLast && (
              <div
                className={`h-0.5 flex-1 mx-1 mb-4 transition-colors ${
                  idx < current ? 'bg-indigo-500' : 'bg-slate-700'
                }`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

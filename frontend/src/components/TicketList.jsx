import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Clock, ChevronRight } from 'lucide-react'
import { getTickets } from '../api/client.js'

const STATUS_DOT = {
  Open: 'bg-amber-400',
  'In Progress': 'bg-blue-400',
  'Pending User': 'bg-purple-400',
  Resolved: 'bg-emerald-400',
  Escalated: 'bg-red-400',
  Closed: 'bg-slate-500',
}

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function TicketList({ refreshKey }) {
  const [tickets, setTickets] = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    getTickets().then(setTickets).catch(console.error)
  }, [refreshKey])

  if (tickets.length === 0) {
    return (
      <p className="text-sm text-slate-500 text-center py-8">
        No tickets yet. Create one above.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {tickets.map(t => (
        <button
          key={t.id}
          onClick={() => navigate(`/tickets/${t.id}`)}
          className="w-full flex items-center gap-3 p-3 bg-slate-800 hover:bg-slate-700 rounded-xl text-left transition-colors group"
        >
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOT[t.status] || 'bg-slate-500'}`} />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-slate-200 truncate">{t.title}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-slate-500">{t.ticket_id}</span>
              <span className="text-xs text-slate-600">·</span>
              <Clock size={11} className="text-slate-600" />
              <span className="text-xs text-slate-500">{timeAgo(t.updated_at)}</span>
            </div>
          </div>
          <ChevronRight size={16} className="text-slate-600 group-hover:text-slate-400 flex-shrink-0" />
        </button>
      ))}
    </div>
  )
}

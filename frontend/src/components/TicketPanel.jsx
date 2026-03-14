import { Tag, Monitor, AlertTriangle, Clock, User } from 'lucide-react'

const STATUS_COLORS = {
  Open: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  'In Progress': 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  'Pending User': 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
  Resolved: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  Escalated: 'bg-red-500/20 text-red-400 border border-red-500/30',
  Closed: 'bg-slate-500/20 text-slate-400 border border-slate-500/30',
}

const SEVERITY_COLORS = {
  Low: 'text-slate-400',
  Medium: 'text-yellow-400',
  High: 'text-orange-400',
  Critical: 'text-red-400',
}

function Row({ icon: Icon, label, value }) {
  return (
    <div className="flex items-start gap-2 py-2 border-b border-slate-800 last:border-0">
      <Icon size={14} className="text-slate-500 mt-0.5 flex-shrink-0" />
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-sm text-slate-200">{value || '—'}</p>
      </div>
    </div>
  )
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString([], {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export default function TicketPanel({ ticket, onResolve, onEscalate }) {
  if (!ticket) return null

  return (
    <div className="w-72 flex-shrink-0 bg-slate-900 border-l border-slate-800 flex flex-col overflow-y-auto">
      <div className="p-4 border-b border-slate-800">
        <p className="text-xs text-slate-500 mb-1">{ticket.ticket_id}</p>
        <h2 className="text-sm font-semibold text-white leading-snug">{ticket.title}</h2>
        <span className={`inline-block mt-2 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[ticket.status] || STATUS_COLORS.Open}`}>
          {ticket.status}
        </span>
      </div>

      <div className="p-4 flex-1">
        <Row icon={Tag} label="Category" value={ticket.category} />
        <Row
          icon={AlertTriangle}
          label="Severity"
          value={
            <span className={SEVERITY_COLORS[ticket.severity] || ''}>
              {ticket.severity}
            </span>
          }
        />
        <Row icon={Monitor} label="Priority" value={ticket.priority} />
        <Row icon={User} label="User" value={ticket.user_id} />
        <Row icon={Clock} label="Created" value={fmtDate(ticket.created_at)} />
        <Row icon={Clock} label="Updated" value={fmtDate(ticket.updated_at)} />
        {ticket.resolved_at && (
          <Row icon={Clock} label="Resolved" value={fmtDate(ticket.resolved_at)} />
        )}
        {ticket.assigned_to && (
          <Row icon={User} label="Assigned To" value={ticket.assigned_to} />
        )}
        {ticket.failed_attempts > 0 && (
          <Row
            icon={AlertTriangle}
            label="Failed Attempts"
            value={<span className="text-orange-400">{ticket.failed_attempts}</span>}
          />
        )}
        {ticket.solution && (
          <div className="mt-3 p-3 bg-emerald-900/30 rounded-lg border border-emerald-800">
            <p className="text-xs text-emerald-400 font-medium mb-1">Solution</p>
            <p className="text-xs text-slate-300 leading-relaxed">{ticket.solution}</p>
          </div>
        )}
      </div>

      {ticket.status === 'Open' && (
        <div className="p-4 border-t border-slate-800 flex flex-col gap-2">
          <button
            onClick={onResolve}
            className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm rounded-lg transition-colors font-medium"
          >
            Mark Resolved
          </button>
          <button
            onClick={onEscalate}
            className="w-full py-2 bg-slate-700 hover:bg-red-900/50 hover:text-red-400 text-slate-300 text-sm rounded-lg transition-colors"
          >
            Escalate to Human
          </button>
        </div>
      )}
    </div>
  )
}

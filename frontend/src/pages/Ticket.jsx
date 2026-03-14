import { useState, useEffect } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, Bot, ThumbsUp, ThumbsDown } from 'lucide-react'
import { getTicket, sendMessage, resolveTicket, escalateTicket, submitSatisfaction } from '../api/client.js'
import Chat from '../components/Chat.jsx'
import TicketPanel from '../components/TicketPanel.jsx'
import ProgressTracker from '../components/ProgressTracker.jsx'

export default function Ticket() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()

  const [ticket, setTicket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [satisfaction, setSatisfaction] = useState(null)

  useEffect(() => {
    loadTicket()
  }, [id])

  const loadTicket = async () => {
    setLoading(true)
    setError('')
    try {
      const t = await getTicket(Number(id))
      setTicket(t)
      if (t.satisfaction) setSatisfaction(t.satisfaction)
    } catch {
      setError('Ticket not found.')
    } finally {
      setLoading(false)
    }
  }

  const handleTicketUpdate = (updatedTicket) => {
    if (updatedTicket) {
      setTicket(prev => ({ ...prev, ...updatedTicket }))
    }
  }

  const handleResolve = async () => {
    try {
      const updated = await resolveTicket(Number(id))
      setTicket(prev => ({ ...prev, ...updated, messages: prev.messages }))
    } catch { /* ignore */ }
  }

  const handleEscalate = async () => {
    if (!confirm('Escalate this ticket to a human IT agent?')) return
    try {
      const updated = await escalateTicket(Number(id))
      setTicket(prev => ({ ...prev, ...updated, messages: prev.messages }))
    } catch { /* ignore */ }
  }

  const handleSatisfaction = async (rating) => {
    setSatisfaction(rating)
    try {
      await submitSatisfaction(Number(id), rating)
    } catch { /* ignore */ }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !ticket) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4">
        <p className="text-slate-400">{error || 'Something went wrong.'}</p>
        <button onClick={() => navigate('/')} className="text-indigo-400 hover:text-indigo-300 text-sm">
          ← Back to Home
        </button>
      </div>
    )
  }

  const isResolved = ticket.status === 'Resolved' || ticket.status === 'Closed'

  return (
    <div className="h-screen bg-slate-950 text-slate-100 flex flex-col overflow-hidden">
      {/* Top bar */}
      <header className="flex-shrink-0 border-b border-slate-800 px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate('/')}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <ArrowLeft size={18} />
        </button>

        <div className="w-7 h-7 bg-indigo-900/50 rounded-lg flex items-center justify-center">
          <Bot size={15} className="text-indigo-400" />
        </div>

        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-white truncate">{ticket.title}</h1>
          <p className="text-xs text-slate-500">{ticket.ticket_id}</p>
        </div>

        {/* Progress tracker */}
        <div className="hidden md:block w-72 flex-shrink-0">
          <ProgressTracker ticket={ticket} />
        </div>
      </header>

      {/* Main area */}
      <div className="flex flex-1 min-h-0">
        {/* Chat */}
        <div className="flex flex-col flex-1 min-w-0 min-h-0">
          <Chat
            ticket={ticket}
            onTicketUpdate={handleTicketUpdate}
            firstMessage={location.state?.firstMessage}
          />
        </div>

        {/* Ticket panel */}
        <TicketPanel
          ticket={ticket}
          onResolve={handleResolve}
          onEscalate={handleEscalate}
        />
      </div>

      {/* Satisfaction prompt for resolved tickets */}
      {isResolved && satisfaction === null && (
        <div className="flex-shrink-0 border-t border-slate-800 bg-slate-900 px-6 py-4 flex items-center justify-center gap-4">
          <p className="text-sm text-slate-300">Did this solve your issue?</p>
          <button
            onClick={() => handleSatisfaction(1)}
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm rounded-lg transition-colors"
          >
            <ThumbsUp size={15} />
            Yes, resolved
          </button>
          <button
            onClick={() => handleSatisfaction(-1)}
            className="flex items-center gap-1.5 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm rounded-lg transition-colors"
          >
            <ThumbsDown size={15} />
            Not really
          </button>
        </div>
      )}

      {satisfaction !== null && (
        <div className="flex-shrink-0 border-t border-slate-800 bg-slate-900 px-6 py-3 text-center">
          <p className={`text-sm ${satisfaction === 1 ? 'text-emerald-400' : 'text-slate-400'}`}>
            {satisfaction === 1 ? '🎉 Thank you for your feedback!' : 'Thanks — we\'ll use this to improve.'}
          </p>
        </div>
      )}
    </div>
  )
}

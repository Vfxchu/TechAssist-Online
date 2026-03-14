import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bot, Send, LayoutDashboard } from 'lucide-react'
import { createTicket } from '../api/client.js'
import TicketList from '../components/TicketList.jsx'

export default function Home() {
  const [issue, setIssue] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [ticketRefreshKey, setTicketRefreshKey] = useState(0)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!issue.trim()) return
    setLoading(true)
    setError('')
    try {
      const ticket = await createTicket(issue.trim().slice(0, 255))
      setTicketRefreshKey(k => k + 1)
      navigate(`/tickets/${ticket.id}`, {
        state: { firstMessage: issue.trim() },
      })
    } catch {
      setError('Failed to create ticket. Is the backend running?')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Nav */}
      <header className="border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
            <Bot size={18} className="text-white" />
          </div>
          <span className="font-bold text-lg text-white">TechAssist</span>
          <span className="text-xs text-slate-500 ml-1">AI Helpdesk</span>
        </div>
        <button
          onClick={() => navigate('/admin')}
          className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors"
        >
          <LayoutDashboard size={15} />
          Admin
        </button>
      </header>

      <main className="flex-1 flex flex-col items-center px-4 pt-16 pb-12">
        {/* Hero */}
        <div className="text-center mb-10 max-w-xl">
          <div className="w-16 h-16 bg-indigo-900/50 border border-indigo-700 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <Bot size={32} className="text-indigo-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-3">
            AI-Powered IT Support
          </h1>
          <p className="text-slate-400 leading-relaxed">
            Describe your technical issue and Vishnu — your IT specialist — will diagnose
            it step by step and guide you to a resolution.
          </p>
        </div>

        {/* Issue form */}
        <form onSubmit={handleSubmit} className="w-full max-w-xl">
          <div className="bg-slate-900 rounded-2xl border border-slate-700 overflow-hidden shadow-xl">
            <textarea
              value={issue}
              onChange={e => setIssue(e.target.value)}
              placeholder="Describe your issue… e.g. 'My WiFi keeps disconnecting every hour on Windows 11'"
              rows={4}
              className="w-full bg-transparent text-slate-100 placeholder-slate-500 px-5 py-4 text-sm resize-none outline-none"
              onKeyDown={e => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e)
              }}
            />
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
              <span className="text-xs text-slate-500">⌘Enter to submit</span>
              <button
                type="submit"
                disabled={!issue.trim() || loading}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors font-medium"
              >
                {loading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Send size={15} />
                )}
                {loading ? 'Opening ticket…' : 'Start Support Chat'}
              </button>
            </div>
          </div>
          {error && <p className="text-red-400 text-sm mt-2 text-center">{error}</p>}
        </form>

        {/* Feature pills */}
        <div className="flex flex-wrap justify-center gap-3 mt-8">
          {[
            '🔍 Structured diagnosis',
            '📚 Live documentation fetch',
            '🔢 Tiered fix suggestions',
            '🎫 Persistent ticket tracking',
            '🤝 Human escalation',
          ].map(f => (
            <span key={f} className="px-3 py-1.5 bg-slate-800 rounded-full text-xs text-slate-400">
              {f}
            </span>
          ))}
        </div>

        {/* Recent tickets */}
        <div className="w-full max-w-xl mt-12">
          <h2 className="text-sm font-semibold text-slate-400 mb-4">Recent Tickets</h2>
          <TicketList refreshKey={ticketRefreshKey} />
        </div>
      </main>
    </div>
  )
}

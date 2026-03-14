import { useEffect, useState } from 'react'
import { getAnalyticsSummary, getCommonIssues } from '../api/client.js'
import { TicketCheck, AlertCircle, TrendingUp, Users, Clock, ThumbsUp } from 'lucide-react'

function StatCard({ icon: Icon, label, value, sub, color = 'indigo' }) {
  const colors = {
    indigo: 'bg-indigo-500/10 text-indigo-400',
    emerald: 'bg-emerald-500/10 text-emerald-400',
    amber: 'bg-amber-500/10 text-amber-400',
    red: 'bg-red-500/10 text-red-400',
    blue: 'bg-blue-500/10 text-blue-400',
    slate: 'bg-slate-700 text-slate-400',
  }
  return (
    <div className="bg-slate-800 rounded-xl p-5 flex items-start gap-4">
      <div className={`p-2.5 rounded-lg ${colors[color]}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value}</p>
        <p className="text-sm text-slate-300 font-medium">{label}</p>
        {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [issues, setIssues] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getAnalyticsSummary(), getCommonIssues()])
      .then(([s, i]) => { setSummary(s); setIssues(i) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!summary) return <p className="text-slate-500 text-center py-12">Failed to load analytics.</p>

  const resolutionPct = (summary.ai_resolution_rate * 100).toFixed(1)

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={TicketCheck} label="Total Tickets"    value={summary.total_tickets}  color="indigo" />
        <StatCard icon={AlertCircle} label="Open Tickets"     value={summary.open_tickets}   color="amber" />
        <StatCard icon={TrendingUp}  label="Resolved by AI"   value={`${resolutionPct}%`}    color="emerald" sub="AI resolution rate" />
        <StatCard icon={Users}       label="Escalated"         value={summary.escalated_tickets} color="red" />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard icon={Clock} label="Today" value={summary.today_tickets} color="blue" />
        <StatCard icon={Clock} label="This Week" value={summary.week_tickets} color="blue" />
        <StatCard icon={Clock} label="This Month" value={summary.month_tickets} color="blue" />
      </div>

      <div className="bg-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">Avg Failed Attempts Before Resolution</h3>
        <div className="flex items-end gap-2">
          <span className="text-3xl font-bold text-white">{summary.avg_failed_attempts}</span>
          <span className="text-slate-500 mb-1">per ticket</span>
        </div>
      </div>

      {issues.length > 0 && (
        <div className="bg-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Top 10 Issue Categories</h3>
          <div className="space-y-2">
            {issues.map((issue, i) => (
              <div key={issue.category} className="flex items-center gap-3">
                <span className="text-xs text-slate-500 w-5 text-right">{i + 1}.</span>
                <div className="flex-1">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm text-slate-200">{issue.category}</span>
                    <div className="flex gap-3 text-xs text-slate-400">
                      <span>{issue.count} tickets</span>
                      <span className="text-emerald-400">{(issue.resolution_rate * 100).toFixed(0)}% resolved</span>
                    </div>
                  </div>
                  <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 rounded-full"
                      style={{ width: `${issue.resolution_rate * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

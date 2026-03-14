import { useNavigate } from 'react-router-dom'
import { ArrowLeft, LayoutDashboard } from 'lucide-react'
import Dashboard from '../components/Dashboard.jsx'

export default function Admin() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => navigate('/')}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <LayoutDashboard size={18} className="text-indigo-400" />
        <h1 className="text-lg font-bold text-white">Analytics Dashboard</h1>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <Dashboard />
      </main>
    </div>
  )
}

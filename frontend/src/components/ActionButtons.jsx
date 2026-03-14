import { CheckCircle, XCircle, HelpCircle } from 'lucide-react'

export default function ActionButtons({ onFixed, onNotWorking, onMoreDetail, disabled }) {
  return (
    <div className="flex flex-wrap gap-2 mt-3 ml-11">
      <button
        onClick={onFixed}
        disabled={disabled}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded-lg transition-colors"
      >
        <CheckCircle size={15} />
        That fixed it
      </button>
      <button
        onClick={onNotWorking}
        disabled={disabled}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-slate-200 text-sm rounded-lg transition-colors"
      >
        <XCircle size={15} />
        Still not working
      </button>
      <button
        onClick={onMoreDetail}
        disabled={disabled}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-slate-200 text-sm rounded-lg transition-colors"
      >
        <HelpCircle size={15} />
        Show me more detail
      </button>
    </div>
  )
}

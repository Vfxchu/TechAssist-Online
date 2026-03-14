import { Bot, User } from 'lucide-react'

function renderContent(text) {
  const lines = text.split('\n')
  const elements = []
  let key = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    if (line.trim() === '') {
      elements.push(<div key={key++} className="h-2" />)
      continue
    }

    // Numbered list
    const numMatch = line.match(/^(\d+)\.\s+(.+)/)
    if (numMatch) {
      elements.push(
        <div key={key++} className="flex gap-2 my-0.5">
          <span className="text-indigo-400 font-semibold min-w-[1.2rem]">{numMatch[1]}.</span>
          <span>{parseInline(numMatch[2])}</span>
        </div>
      )
      continue
    }

    // Bullet list
    const bulletMatch = line.match(/^[-*•]\s+(.+)/)
    if (bulletMatch) {
      elements.push(
        <div key={key++} className="flex gap-2 my-0.5">
          <span className="text-slate-400 mt-1">•</span>
          <span>{parseInline(bulletMatch[1])}</span>
        </div>
      )
      continue
    }

    // Heading (##)
    const h2Match = line.match(/^##\s+(.+)/)
    if (h2Match) {
      elements.push(
        <p key={key++} className="font-semibold text-white mt-2">
          {parseInline(h2Match[1])}
        </p>
      )
      continue
    }

    // Regular line
    elements.push(<p key={key++} className="my-0.5">{parseInline(line)}</p>)
  }

  return elements
}

function parseInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|https?:\/\/\S+)/)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-semibold text-white">{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={i} className="bg-slate-900 text-emerald-400 px-1.5 py-0.5 rounded text-sm font-mono">
          {part.slice(1, -1)}
        </code>
      )
    }
    if (part.startsWith('http')) {
      return (
        <a key={i} href={part} target="_blank" rel="noopener noreferrer"
          className="text-indigo-400 underline underline-offset-2 hover:text-indigo-300 break-all">
          {part}
        </a>
      )
    }
    return part
  })
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function Message({ message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end gap-3 group">
        <div className="max-w-[72%]">
          <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed">
            {message.content}
            {message.screenshot_path && (
              <div className="mt-2">
                <img
                  src={message.screenshot_path}
                  alt="screenshot"
                  className="max-w-xs rounded-lg border border-indigo-500"
                />
              </div>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1 text-right">{formatTime(message.created_at)}</p>
        </div>
        <div className="w-8 h-8 rounded-full bg-indigo-700 flex items-center justify-center flex-shrink-0 mt-1">
          <User size={16} className="text-white" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3 group">
      <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0 mt-1">
        <Bot size={16} className="text-indigo-400" />
      </div>
      <div className="max-w-[78%]">
        <div className="bg-slate-800 text-slate-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed">
          {renderContent(message.content)}
        </div>
        <p className="text-xs text-slate-500 mt-1">{formatTime(message.created_at)}</p>
      </div>
    </div>
  )
}

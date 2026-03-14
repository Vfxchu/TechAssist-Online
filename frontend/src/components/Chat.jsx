import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, X } from 'lucide-react'
import Message from './Message.jsx'
import ActionButtons from './ActionButtons.jsx'
import ScreenshotUpload from './ScreenshotUpload.jsx'
import { sendMessage } from '../api/client.js'

export default function Chat({ ticket, onTicketUpdate, firstMessage }) {
  const [messages, setMessages]               = useState(ticket?.messages || [])
  const [input, setInput]                     = useState('')
  const [loading, setLoading]                 = useState(false)
  const [screenshotRequested, setScreenshotRequested] = useState(false)
  const [showUpload, setShowUpload]           = useState(false)
  const [pendingScreenshot, setPendingScreenshot] = useState(null)
  const [showActionButtons, setShowActionButtons] = useState(false)
  const [escalationBanner, setEscalationBanner] = useState(false)

  const bottomRef  = useRef(null)
  const textRef    = useRef(null)
  const isOpen     = ticket?.status === 'Open'

  useEffect(() => {
    setMessages(ticket?.messages || [])
    setShowActionButtons(false)
    setScreenshotRequested(false)
    setEscalationBanner(false)
  }, [ticket?.id])

  // Auto-send the first message if provided (from Home navigation)
  useEffect(() => {
    if (firstMessage && ticket?.messages?.length === 0) {
      send(firstMessage)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const lastAssistantMsg = [...messages].reverse().find(m => m.role === 'assistant')
  const showButtons = showActionButtons && isOpen && lastAssistantMsg

  const send = async (text) => {
    if (!text.trim() || loading || !isOpen) return
    setInput('')
    setShowActionButtons(false)
    setEscalationBanner(false)
    setLoading(true)

    // Capture screenshot path before clearing state (closure fix)
    const screenshotToSend = pendingScreenshot

    // Optimistic user message
    const optimistic = {
      id: Date.now(),
      ticket_id: ticket.id,
      role: 'user',
      content: text,
      screenshot_path: screenshotToSend,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, optimistic])
    setPendingScreenshot(null)
    setShowUpload(false)
    setScreenshotRequested(false)

    try {
      const result = await sendMessage(ticket.id, text, screenshotToSend)

      setMessages(prev => [
        ...prev.filter(m => m.id !== optimistic.id),
        result.user_message,
        result.assistant_message,
      ])

      if (result.screenshot_requested) setScreenshotRequested(true)
      if (result.escalation_recommended) setEscalationBanner(true)
      
      // Only show buttons if AI is suggesting a fix (Phase 3)
      // Identified by the confirmation phrase or the action_needed status
      const isSuggesting = result.assistant_message.content.includes("Did this fix the issue?")
      if (isSuggesting && result.action_needed !== 'resolved' && result.action_needed !== 'escalate') {
        setShowActionButtons(true)
      }

      if (onTicketUpdate) onTicketUpdate(result.ticket)
    } catch {
      setMessages(prev => prev.filter(m => m.id !== optimistic.id))
      alert('Failed to send message — please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  const handleScreenshotUploaded = (path) => {
    setPendingScreenshot(path)
    setShowUpload(false)
    setScreenshotRequested(false)
    textRef.current?.focus()
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Escalation banner */}
      {escalationBanner && isOpen && (
        <div className="mx-4 mt-3 p-3 bg-red-900/30 border border-red-700 rounded-xl flex items-center gap-3">
          <span className="text-red-400 text-sm">
            AI has reached the escalation threshold. Consider escalating to a human agent.
          </span>
        </div>
      )}

      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-14 h-14 rounded-full bg-indigo-900/50 flex items-center justify-center mb-4">
              <span className="text-2xl">🤖</span>
            </div>
            <p className="text-slate-400 text-sm">Vishnu is ready to help. Describe your issue above to begin.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={msg.id || i}>
            <Message message={msg} />
            {showButtons && i === messages.length - 1 && msg.role === 'assistant' && (
              <ActionButtons
                disabled={loading}
                onFixed={() => send("That fixed it")}
                onNotWorking={() => send("Still not working")}
                onMoreDetail={() => send("Show me more detail")}
              />
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
              <span className="text-xs">🤖</span>
            </div>
            <div className="bg-slate-800 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1 items-center h-5">
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className="w-2 h-2 bg-slate-500 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 150}ms` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Screenshot upload area */}
      {(screenshotRequested || showUpload) && isOpen && (
        <ScreenshotUpload
          ticketId={ticket.id}
          requested={screenshotRequested}
          onUploaded={handleScreenshotUploaded}
          onDismiss={() => { setShowUpload(false); setScreenshotRequested(false) }}
        />
      )}

      {/* Pending screenshot badge */}
      {pendingScreenshot && (
        <div className="mx-4 mb-2 flex items-center gap-3 p-2 bg-slate-800/50 rounded-lg border border-slate-700 w-fit">
          <div className="w-10 h-10 rounded overflow-hidden border border-slate-600 flex-shrink-0">
            <img src={pendingScreenshot} alt="preview" className="w-full h-full object-cover" />
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Screenshot Attached</span>
            <button
              onClick={() => setPendingScreenshot(null)}
              className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1"
            >
              <X size={10} />
              Remove
            </button>
          </div>
        </div>
      )}

      {/* Input bar */}
      {!isOpen ? (
        <div className="p-4 border-t border-slate-800 text-center">
          <span className={`text-sm px-3 py-1.5 rounded-full ${
            ticket.status === 'Resolved'
              ? 'bg-emerald-900/40 text-emerald-400'
              : 'bg-red-900/40 text-red-400'
          }`}>
            Ticket {ticket.status} — chat is closed
          </span>
        </div>
      ) : (
        <div className="p-4 border-t border-slate-800">
          <div className="flex gap-2 bg-slate-800 rounded-xl p-2">
            <button
              onClick={() => setShowUpload(v => !v)}
              className="p-2 text-slate-400 hover:text-slate-200 transition-colors flex-shrink-0"
              title="Attach screenshot"
            >
              <Paperclip size={18} />
            </button>
            <textarea
              ref={textRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe your issue or reply to Vishnu… (Enter to send)"
              rows={1}
              className="flex-1 bg-transparent text-slate-200 placeholder-slate-500 text-sm resize-none outline-none py-2 max-h-32"
              style={{ minHeight: '2rem' }}
              disabled={loading}
            />
            <button
              onClick={() => send(input)}
              disabled={!input.trim() || loading}
              className="p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex-shrink-0"
            >
              <Send size={16} />
            </button>
          </div>
          <p className="text-xs text-slate-600 mt-1.5 px-1">
            Shift+Enter for new line · Enter to send
          </p>
        </div>
      )}
    </div>
  )
}

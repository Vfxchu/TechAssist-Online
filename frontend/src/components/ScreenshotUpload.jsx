import { useState, useRef } from 'react'
import { Camera, Upload, X } from 'lucide-react'
import { uploadScreenshot } from '../api/client.js'

export default function ScreenshotUpload({ ticketId, onUploaded, onDismiss, requested = false }) {
  const [uploading, setUploading] = useState(false)
  const [preview, setPreview] = useState(null)
  const inputRef = useRef(null)

  const handleFile = async (file) => {
    if (!file || !file.type.startsWith('image/')) return
    const url = URL.createObjectURL(file)
    setPreview(url)
    setUploading(true)
    try {
      const result = await uploadScreenshot(ticketId, file)
      onUploaded(result.screenshot_path)
    } catch {
      alert('Upload failed — please try again.')
      setPreview(null)
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div
      className={`mx-4 mb-2 rounded-xl border-2 border-dashed p-4 transition-colors ${
        requested
          ? 'border-amber-500 bg-amber-950/30'
          : 'border-slate-600 bg-slate-800/50'
      }`}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
    >
      <div className="flex items-start gap-3">
        <Camera size={20} className={requested ? 'text-amber-400' : 'text-slate-400'} />
        <div className="flex-1 min-w-0">
          {requested && (
            <p className="text-amber-400 text-xs font-medium mb-1">
              Vishnu is requesting a screenshot to continue diagnosis
            </p>
          )}
          {preview ? (
            <div className="relative inline-block">
              <img src={preview} alt="preview" className="max-h-32 rounded-lg" />
              {uploading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-lg">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={() => inputRef.current?.click()}
              className="text-sm text-slate-300 hover:text-white underline"
            >
              Click to attach a screenshot, or drag and drop here
            </button>
          )}
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
          />
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="text-slate-500 hover:text-slate-300">
            <X size={16} />
          </button>
        )}
      </div>
    </div>
  )
}

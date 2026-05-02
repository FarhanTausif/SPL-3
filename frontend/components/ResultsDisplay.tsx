'use client'

import { useRunStore } from '@/stores/runStore'
import { CheckCircle, AlertCircle, XCircle, Copy, Download } from 'lucide-react'
import { useState } from 'react'

export function ResultsDisplay() {
  const currentRun = useRunStore((state) => state.currentRun)
  const evidence = useRunStore((state) => state.evidence)
  const [copied, setCopied] = useState(false)

  if (!currentRun) {
    return null
  }

  const handleCopyCode = () => {
    if (currentRun.generated_code) {
      navigator.clipboard.writeText(currentRun.generated_code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const getVerdictIcon = () => {
    if (currentRun.hallucination_detected) {
      return <AlertCircle className="w-8 h-8 text-warning" />
    }
    return <CheckCircle className="w-8 h-8 text-success" />
  }

  const getVerdictColor = () => {
    if (currentRun.hallucination_detected) {
      return 'bg-yellow-50 border-yellow-200'
    }
    return 'bg-green-50 border-green-200'
  }

  return (
    <div className="space-y-6">
      {/* Verdict Card */}
      <div className={`glass p-6 border-2 ${getVerdictColor()}`}>
        <div className="flex items-start gap-4">
          {getVerdictIcon()}
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-900">
              {currentRun.hallucination_detected ? 'Hallucination Detected' : 'Code Verified'}
            </h2>
            <p className="text-gray-600 mt-2">
              {currentRun.verdict || (currentRun.hallucination_detected ? 'This code contains potential hallucinations.' : 'This code has been verified and appears correct.')}
            </p>
            <div className="mt-4 flex items-center gap-4">
              <div>
                <p className="text-sm text-gray-600">Confidence Score</p>
                <p className="text-2xl font-bold">
                  {(currentRun.confidence ? currentRun.confidence * 100 : 0).toFixed(1)}%
                </p>
              </div>
              <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    currentRun.hallucination_detected ? 'bg-warning' : 'bg-success'
                  }`}
                  style={{
                    width: `${(currentRun.confidence || 0) * 100}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Generated Code */}
      {currentRun.generated_code && (
        <div className="glass p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Generated Code</h3>
            <button
              onClick={handleCopyCode}
              className="flex items-center gap-2 px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-smooth"
            >
              <Copy className="w-4 h-4" />
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm max-h-96 overflow-y-auto">
            <code>{currentRun.generated_code}</code>
          </pre>
        </div>
      )}

      {/* Evidence Summary */}
      {evidence.length > 0 && (
        <div className="glass p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Verification Evidence</h3>
          <div className="space-y-3">
            {evidence.slice(0, 5).map((ev, idx) => (
              <div key={idx} className="p-3 bg-white/50 rounded-lg">
                <div className="flex items-start gap-3">
                  <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded font-mono">
                    {ev.evidence_kind}
                  </span>
                  <div className="flex-1 text-sm">
                    <p className="text-gray-700">{ev.finding}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(ev.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            {evidence.length > 5 && (
              <p className="text-sm text-gray-600 text-center py-2">
                +{evidence.length - 5} more pieces of evidence
              </p>
            )}
          </div>
        </div>
      )}

      {/* Timestamps */}
      <div className="glass p-4 text-sm text-gray-600">
        <p>Verification completed at {new Date(currentRun.updated_at).toLocaleString()}</p>
      </div>
    </div>
  )
}

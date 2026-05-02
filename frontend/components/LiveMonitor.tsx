'use client'

import { useRunStatus, useRunEvidence } from '@/hooks/useRunStatus'
import { useRunStore } from '@/stores/runStore'
import { CheckCircle, AlertCircle, Loader, XCircle } from 'lucide-react'

interface LiveMonitorProps {
  runId: string
}

export function LiveMonitor({ runId }: LiveMonitorProps) {
  const currentRun = useRunStore((state) => state.currentRun)
  const isLoading = useRunStore((state) => state.isLoading)
  const error = useRunStore((state) => state.error)

  // Use polling hooks
  useRunStatus(runId, true)
  useRunEvidence(runId)

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-6 h-6 text-green-600" />
      case 'failed':
        return <XCircle className="w-6 h-6 text-red-600" />
      case 'started':
      case 'queued':
        return <Loader className="w-6 h-6 text-blue-600 animate-spin" />
      default:
        return <AlertCircle className="w-6 h-6 text-gray-600" />
    }
  }

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 badge-success'
      case 'failed':
        return 'bg-red-100 text-red-800 badge-error'
      case 'started':
      case 'queued':
        return 'bg-blue-100 text-blue-800 badge-info'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (!currentRun) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <Loader className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-3" />
          <p className="text-gray-600">Loading verification run...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Status Header */}
      <div className="glass p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {getStatusIcon(currentRun.status)}
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                Verification {currentRun.status === 'completed' ? 'Complete' : 'In Progress'}
              </h2>
              <p className="text-gray-600 mt-1">Run ID: {currentRun.run_id}</p>
            </div>
          </div>
          <span className={`badge ${getStatusBadgeColor(currentRun.status)}`}>
            {currentRun.status.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Progress Section */}
      {(currentRun.status === 'queued' || currentRun.status === 'started') && (
        <div className="glass p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Verification Pipeline</h3>
          <div className="space-y-3">
            <VerificationStage name="Initialization" status="done" />
            <VerificationStage name="Clarification Agent" status={currentRun.status === 'queued' ? 'pending' : 'running'} />
            <VerificationStage name="Code Generation" status={currentRun.status === 'queued' ? 'pending' : 'running'} />
            <VerificationStage name="Parallel Verification (6 agents)" status={currentRun.status === 'queued' ? 'pending' : 'running'} />
            <VerificationStage name="Policy Decision" status="pending" />
          </div>
        </div>
      )}

      {/* Metrics Section */}
      {currentRun.status === 'completed' && (
        <div className="glass p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Hallucination Analysis</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-white/50 rounded-lg">
              <p className="text-sm text-gray-600">Hallucination Detected</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {currentRun.hallucination_detected ? 'Yes' : 'No'}
              </p>
            </div>
            <div className="p-4 bg-white/50 rounded-lg">
              <p className="text-sm text-gray-600">Confidence</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {(currentRun.confidence ? currentRun.confidence * 100 : 0).toFixed(0)}%
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="flex items-start p-4 bg-red-50 border border-red-200 rounded-lg glass">
          <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
          <div className="text-sm text-red-800">{error}</div>
        </div>
      )}

      {/* Timestamps */}
      <div className="glass p-4 text-sm text-gray-600">
        <p>Created: {new Date(currentRun.created_at).toLocaleString()}</p>
        <p>Updated: {new Date(currentRun.updated_at).toLocaleString()}</p>
      </div>
    </div>
  )
}

function VerificationStage({
  name,
  status,
}: {
  name: string
  status: 'done' | 'running' | 'pending'
}) {
  const getStatusColor = (s: string) => {
    switch (s) {
      case 'done':
        return 'text-green-600'
      case 'running':
        return 'text-blue-600'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusIcon = (s: string) => {
    switch (s) {
      case 'done':
        return '✓'
      case 'running':
        return '⟳'
      default:
        return '○'
    }
  }

  return (
    <div className="flex items-center gap-3">
      <span className={`font-bold text-lg ${getStatusColor(status)}`}>
        {getStatusIcon(status)}
      </span>
      <span className={`flex-1 ${status === 'running' ? 'font-semibold text-blue-900' : 'text-gray-700'}`}>
        {name}
      </span>
      {status === 'running' && <Loader className="w-4 h-4 text-blue-600 animate-spin" />}
    </div>
  )
}

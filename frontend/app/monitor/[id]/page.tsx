'use client'

import { useParams, useRouter } from 'next/navigation'
import { LiveMonitor } from '@/components/LiveMonitor'
import { ResultsDisplay } from '@/components/ResultsDisplay'
import { useRunStore } from '@/stores/runStore'
import { ArrowLeft } from 'lucide-react'

export default function MonitorPage() {
  const params = useParams()
  const router = useRouter()
  const runId = params.id as string
  const currentRun = useRunStore((state) => state.currentRun)

  const isComplete = currentRun && (currentRun.status === 'completed' || currentRun.status === 'failed')

  return (
    <main className="min-h-screen py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Navigation */}
        <button
          onClick={() => router.push('/')}
          className="flex items-center gap-2 text-primary hover:text-blue-700 mb-8 transition-smooth"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </button>

        {/* Content */}
        <div className="space-y-8">
          {/* Title */}
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {isComplete ? 'Verification Results' : 'Live Verification'}
            </h1>
            <p className="text-gray-600 mt-2">Run ID: {runId}</p>
          </div>

          {/* Main Content */}
          {isComplete ? <ResultsDisplay /> : <LiveMonitor runId={runId} />}
        </div>
      </div>
    </main>
  )
}

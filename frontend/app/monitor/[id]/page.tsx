'use client'

import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { useRunStore } from '@/stores/runStore'
import { useRunStatus } from '@/hooks/useRunStatus'
import { WorkflowDAG, EvidencePanel, MetricsPanel } from '@/components/workflow'
import { ResultsDisplay } from '@/components/ResultsDisplay'
import { ArrowLeft, Copy, CheckCircle2 } from 'lucide-react'
import { motion } from 'framer-motion'

export default function MonitorPage() {
  const params = useParams()
  const router = useRouter()
  const runId = params.id as string
  const { data: runStatus } = useRunStatus(runId)
  const currentRun = useRunStore((state) => state.currentRun)
  const [copiedId, setCopiedId] = useState(false)
  const [elapsedTime, setElapsedTime] = useState(0)

  const isComplete = currentRun && (currentRun.status === 'completed' || currentRun.status === 'failed')

  // Update elapsed time
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedTime((prev) => prev + 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const handleCopyId = () => {
    navigator.clipboard.writeText(runId)
    setCopiedId(true)
    setTimeout(() => setCopiedId(false), 2000)
  }

  // Build agents from current run status
  const agents = [
    {
      name: 'Clarification',
      role: 'Agent',
      status: (currentRun?.status === 'queued' ? 'idle' : 'complete') as 'idle' | 'running' | 'complete' | 'error',
      progress: 100,
      duration: 100,
      stage: 'Clarification',
    },
    {
      name: 'Generation',
      role: 'Code Generator',
      status: (currentRun?.status === 'queued' ? 'idle' : currentRun?.status === 'completed' ? 'complete' : 'running') as any,
      progress: currentRun?.status === 'completed' ? 100 : 50,
      duration: currentRun?.status === 'completed' ? 500 : undefined,
      stage: 'Generation',
    },
    {
      name: 'Claim Extraction',
      role: 'Analyzer',
      status: (currentRun?.status === 'completed' ? 'complete' : 'idle') as any,
      progress: currentRun?.status === 'completed' ? 100 : 0,
      stage: 'Verification',
    },
    {
      name: 'Static Analysis',
      role: 'Analyzer',
      status: (currentRun?.status === 'completed' ? 'complete' : 'idle') as any,
      progress: currentRun?.status === 'completed' ? 100 : 0,
      stage: 'Verification',
    },
    {
      name: 'Sandbox',
      role: 'Executor',
      status: (currentRun?.status === 'completed' ? 'complete' : 'idle') as any,
      progress: currentRun?.status === 'completed' ? 100 : 0,
      duration: currentRun?.status === 'completed' ? 50 : undefined,
      stage: 'Verification',
    },
    {
      name: 'Judge',
      role: 'Verifier',
      status: (currentRun?.status === 'completed' ? 'complete' : 'idle') as any,
      progress: currentRun?.status === 'completed' ? 100 : 0,
      stage: 'Verification',
    },
  ]

  const evidence = (currentRun as any)?.evidence || []

  const metrics = {
    hallucination_risk_score: currentRun?.confidence ? 1 - currentRun.confidence : 0.3,
    confidence: currentRun?.confidence || 0.7,
    verification_progress: {
      claims_verified: 9,
      claims_total: 9,
      static_passed: true,
      sandbox_passed: true,
      judge_score: currentRun?.confidence || 0.8,
      cove_verified_percent: 100,
    },
    timing: {
      generation_ms: 500,
      claims_ms: 100,
      static_ms: 50,
      sandbox_ms: 10,
      judge_ms: 300,
      cove_ms: 50,
      policy_ms: 5,
    },
    alerts: [],
  }

  const policyDecision = (currentRun?.verdict as any) || 'accept'

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 py-6 px-4" id="main-content">
      {/* Skip Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:block absolute top-4 left-4 bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium z-50"
      >
        Skip to main content
      </a>

      {/* Header */}
      <motion.div
        className="max-w-7xl mx-auto mb-6"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {/* Navigation */}
        <button
          onClick={() => router.push('/')}
          aria-label="Back to home page"
          className="flex items-center gap-2 text-blue-600 hover:text-blue-800 mb-4 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded px-2 py-1"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </button>

        {/* Title Section */}
        <div className="flex items-start justify-between mb-4 gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-slate-900">
              {isComplete ? '✅ Verification Complete' : '⏳ Verification In Progress'}
            </h1>
            <p className="text-slate-600 mt-2 text-sm sm:text-base">
              Status: <span className="font-semibold text-slate-900">{currentRun?.status || 'queued'}</span>
            </p>
          </div>

          {/* Info Panel - Desktop */}
          <motion.div
            className="hidden lg:block bg-white rounded-lg border border-slate-200 p-4 min-w-fit"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <div className="space-y-2 text-sm">
              <div>
                <p className="text-slate-600">Run ID</p>
                <button
                  onClick={handleCopyId}
                  aria-label={`Copy run ID: ${runId}`}
                  className="flex items-center gap-2 font-mono text-xs bg-slate-100 px-2 py-1 rounded hover:bg-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {runId.slice(0, 8)}...
                  {copiedId ? <CheckCircle2 className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <div>
                <p className="text-slate-600">Elapsed</p>
                <p className="font-semibold">{Math.floor(elapsedTime / 60)}m {elapsedTime % 60}s</p>
              </div>
              <div>
                <p className="text-slate-600">Risk Score</p>
                <p className="font-semibold">{(metrics.hallucination_risk_score * 100).toFixed(1)}%</p>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Info Panel - Mobile */}
        <motion.div
          className="lg:hidden bg-white rounded-lg border border-slate-200 p-3 grid grid-cols-3 gap-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <div>
            <p className="text-xs text-slate-600">Run ID</p>
            <button
              onClick={handleCopyId}
              aria-label={`Copy run ID: ${runId}`}
              className="flex items-center gap-1 font-mono text-xs bg-slate-100 px-2 py-1 rounded hover:bg-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 mt-1"
            >
              {runId.slice(0, 4)}...
              {copiedId ? <CheckCircle2 className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3" />}
            </button>
          </div>
          <div>
            <p className="text-xs text-slate-600">Elapsed</p>
            <p className="font-semibold text-xs mt-1">{Math.floor(elapsedTime / 60)}m {elapsedTime % 60}s</p>
          </div>
          <div>
            <p className="text-xs text-slate-600">Risk</p>
            <p className="font-semibold text-xs mt-1">{(metrics.hallucination_risk_score * 100).toFixed(1)}%</p>
          </div>
        </motion.div>
      </motion.div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto">
        {isComplete ? (
          <ResultsDisplay />
        ) : (
          <motion.div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 auto-rows-max lg:auto-rows-fr"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, staggerChildren: 0.1 }}
          >
            {/* Left: Workflow DAG */}
            <motion.div
              className="md:col-span-2 lg:col-span-2 bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden"
              style={{ minHeight: '400px', height: 'auto', maxHeight: '600px' }}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
            >
              <WorkflowDAG
                agents={agents}
                policyDecision={policyDecision}
                isRepairLoopActive={policyDecision === 'repair' && !isComplete}
              />
            </motion.div>

            {/* Right: Metrics Panel */}
            <motion.div
              className="md:col-span-2 lg:col-span-1 bg-white rounded-lg border border-slate-200 shadow-sm"
              style={{ minHeight: '400px', height: 'auto', maxHeight: '600px' }}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
            >
              <MetricsPanel metrics={metrics} policyDecision={policyDecision} />
            </motion.div>

            {/* Bottom: Evidence Panel */}
            <motion.div
              className="col-span-1 md:col-span-2 lg:col-span-3 bg-white rounded-lg border border-slate-200 shadow-sm"
              style={{ minHeight: '300px', height: 'auto', maxHeight: '500px' }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.1 }}
            >
              <EvidencePanel
                evidence={evidence.map((e: any) => ({
                  kind: e.evidence_kind || e.kind || 'policy_decision',
                  summary: e.finding || e.summary || 'Result',
                  status: e.severity === 'error' ? 'error' : e.severity === 'warning' ? 'warning' : 'success',
                  payload: e,
                  timestamp: e.timestamp,
                }))}
                loading={false}
              />
            </motion.div>
          </motion.div>
        )}
      </div>
    </main>
  )
}

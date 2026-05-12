'use client'

import { useMemo, useState } from 'react'
import type React from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, CheckCircle2, Copy, Radio, RefreshCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { useRunStore } from '@/stores/runStore'
import { useHealth, useRunEvidence, useRunEvents, useRunStatus } from '@/hooks/useRunStatus'
import { useRunUpdates } from '@/hooks/useRunUpdates'
import { buildOrchestrationViewModel } from '@/lib/orchestration'
import { OrchestrationFlow } from '@/components/orchestration/OrchestrationFlow'
import { StageInspector } from '@/components/orchestration/StageInspector'
import { EvidenceTimeline } from '@/components/orchestration/EvidenceTimeline'
import { RunMetricsPanel } from '@/components/orchestration/RunMetricsPanel'
import { CodeResultPanel } from '@/components/orchestration/CodeResultPanel'
import { StatusBadge } from '@/components/orchestration/StatusBadge'

export default function MonitorPage() {
  const params = useParams()
  const router = useRouter()
  const runId = params.id as string
  const [copiedId, setCopiedId] = useState(false)
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null)

  const currentRun = useRunStore((state) => state.currentRun)
  const evidence = useRunStore((state) => state.evidence)
  const events = useRunStore((state) => state.events)

  const runQuery = useRunStatus(runId)
  useRunEvidence(runId)
  useRunEvents(runId)
  const healthQuery = useHealth()
  const { isWSConnected, isPolling } = useRunUpdates(runId)

  const viewModel = useMemo(
    () => buildOrchestrationViewModel({
      run: currentRun,
      evidence,
      events,
      health: healthQuery.data,
    }),
    [currentRun, evidence, events, healthQuery.data]
  )

  const selectedStage = viewModel.stages.find((stage) => stage.id === (selectedStageId || viewModel.activeStageId))
  const terminal = currentRun?.status === 'completed' || currentRun?.status === 'failed' || currentRun?.status === 'needs_clarification'

  const handleCopyId = () => {
    navigator.clipboard.writeText(runId)
    setCopiedId(true)
    setTimeout(() => setCopiedId(false), 1600)
  }

  return (
    <main className="min-h-screen bg-background px-4 py-6 text-foreground">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
        <header className="rounded-lg border bg-card p-4 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <Button type="button" variant="ghost" size="sm" onClick={() => router.push('/')} className="mb-3 px-0">
                <ArrowLeft className="h-4 w-4" />
                New prompt
              </Button>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-2xl font-semibold tracking-normal">CrewAI Orchestration Run</h1>
                <StatusBadge status={currentRun?.status || 'queued'} />
                <Badge variant={isWSConnected ? 'success' : 'warning'}>
                  <Radio className="mr-1 h-3 w-3" />
                  {isWSConnected ? 'live stream' : isPolling ? 'polling fallback' : 'connecting'}
                </Badge>
              </div>
              <p className="mt-2 max-w-4xl text-sm text-muted-foreground">
                {currentRun?.normalized_request.prompt || 'Loading run prompt and orchestration state.'}
              </p>
            </div>

            <div className="grid min-w-0 grid-cols-2 gap-3 text-sm md:grid-cols-4 lg:min-w-[620px]">
              <RunFact label="Run ID" value={runId.slice(0, 8)} action={(
                <Button type="button" variant="ghost" size="icon" onClick={handleCopyId} aria-label="Copy run ID">
                  {copiedId ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
                </Button>
              )} />
              <RunFact label="Mode" value={currentRun?.normalized_request.run_mode || 'loading'} />
              <RunFact label="Language" value={currentRun?.normalized_request.language || 'loading'} />
              <RunFact label="Risk" value={`${viewModel.riskPercent}%`} />
            </div>
          </div>

          <Separator className="my-4" />

          <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-4">
            <RunFact label="CrewAI" value={healthQuery.data?.orchestration.crewai_enabled ? 'enabled' : 'not enabled'} />
            <RunFact label="Worker" value={String(healthQuery.data?.orchestration.worker_readiness?.state || 'unknown')} />
            <RunFact label="Providers" value={viewModel.providerSummary} />
            <RunFact label="Policy" value={viewModel.policyLabel} />
          </div>
        </header>

        {runQuery.isError && (
          <Card className="border-destructive">
            <CardContent className="flex items-center justify-between gap-3 p-4">
              <p className="text-sm text-destructive">Unable to load the run. Check the backend and retry.</p>
              <Button type="button" variant="outline" size="sm" onClick={() => runQuery.refetch()}>
                <RefreshCcw className="h-4 w-4" />
                Retry
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <section className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Execution Flow</CardTitle>
                <CardDescription>
                  Prompt-to-result pipeline with parallel verification branches and conditional repair loop.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <OrchestrationFlow
                  stages={viewModel.stages}
                  selectedStageId={selectedStage?.id || viewModel.activeStageId}
                  onSelectStage={setSelectedStageId}
                />
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <RunMetricsPanel run={currentRun} viewModel={viewModel} />
              <Card>
                <CardHeader>
                  <CardTitle>Evidence & Event Timeline</CardTitle>
                  <CardDescription>
                    Backend records shown in arrival order. No frontend-simulated evidence is inserted.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <EvidenceTimeline evidence={evidence} events={events} />
                </CardContent>
              </Card>
            </div>

            {terminal && <CodeResultPanel runResponse={currentRun} />}
          </section>

          <motion.aside
            className="min-h-[520px]"
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35 }}
          >
            <StageInspector stage={selectedStage} />
          </motion.aside>
        </div>
      </div>
    </main>
  )
}

function RunFact({
  label,
  value,
  action,
}: {
  label: string
  value: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-2 rounded-md border bg-background px-3 py-2">
      <div className="min-w-0">
        <p className="text-xs uppercase text-muted-foreground">{label}</p>
        <p className="mt-0.5 truncate font-medium capitalize">{value}</p>
      </div>
      {action}
    </div>
  )
}

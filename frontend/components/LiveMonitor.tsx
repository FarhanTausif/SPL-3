'use client'

import { useMemo } from 'react'
import { useRunEvidence, useRunEvents, useRunStatus } from '@/hooks/useRunStatus'
import { useRunStore } from '@/stores/runStore'
import { buildOrchestrationViewModel } from '@/lib/orchestration'
import { OrchestrationFlow } from '@/components/orchestration/OrchestrationFlow'

interface LiveMonitorProps {
  runId: string
}

export function LiveMonitor({ runId }: LiveMonitorProps) {
  const currentRun = useRunStore((state) => state.currentRun)
  const evidence = useRunStore((state) => state.evidence)
  const events = useRunStore((state) => state.events)

  useRunStatus(runId, true)
  useRunEvidence(runId)
  useRunEvents(runId)

  const viewModel = useMemo(
    () => buildOrchestrationViewModel({ run: currentRun, evidence, events }),
    [currentRun, evidence, events]
  )

  return (
    <OrchestrationFlow
      stages={viewModel.stages}
      selectedStageId={viewModel.activeStageId}
      onSelectStage={() => undefined}
    />
  )
}

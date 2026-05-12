'use client'

import { CodeResultPanel } from '@/components/orchestration/CodeResultPanel'
import { RunMetricsPanel } from '@/components/orchestration/RunMetricsPanel'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useRunStore } from '@/stores/runStore'
import { buildOrchestrationViewModel } from '@/lib/orchestration'

export function ResultsDisplay() {
  const currentRun = useRunStore((state) => state.currentRun)
  const evidence = useRunStore((state) => state.evidence)
  const events = useRunStore((state) => state.events)

  if (!currentRun) return null

  const viewModel = buildOrchestrationViewModel({ run: currentRun, evidence, events })

  return (
    <div className="space-y-6">
      <RunMetricsPanel run={currentRun} viewModel={viewModel} />
      <CodeResultPanel runResponse={currentRun} />
      <Card>
        <CardHeader>
          <CardTitle>Policy Reasons</CardTitle>
          <CardDescription>Backend policy explanation for the final decision.</CardDescription>
        </CardHeader>
        <CardContent>
          {currentRun.policy_decision?.reasons?.length ? (
            <ul className="space-y-2 text-sm">
              {currentRun.policy_decision.reasons.map((reason) => (
                <li key={reason} className="rounded-md border bg-background p-3">{reason}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No policy reasons reported.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { metricRows, OrchestrationViewModel } from '@/lib/orchestration'
import { RunDetail } from '@/lib/api'

export function RunMetricsPanel({
  run,
  viewModel,
}: {
  run: RunDetail | null
  viewModel: OrchestrationViewModel
}) {
  const rows = metricRows(run?.fused_metrics)
  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk & Policy</CardTitle>
        <CardDescription>Fused hallucination metrics and final policy state.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Hallucination risk</span>
            <span className="font-semibold">{viewModel.riskPercent}%</span>
          </div>
          <Progress className="mt-2" value={viewModel.riskPercent} />
        </div>
        <div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Policy confidence</span>
            <span className="font-semibold">{viewModel.confidencePercent}%</span>
          </div>
          <Progress className="mt-2" value={viewModel.confidencePercent} />
        </div>
        <Separator />
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Decision</span>
            <span className="font-semibold capitalize">{viewModel.policyLabel}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Providers</span>
            <span className="max-w-[55%] truncate font-semibold">{viewModel.providerSummary}</span>
          </div>
        </div>
        {rows.length > 0 && (
          <>
            <Separator />
            <div className="space-y-3">
              {rows.map(([label, value]) => (
                <div key={label}>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="font-medium">{Math.round(value * 100)}%</span>
                  </div>
                  <Progress className="mt-1 h-1.5" value={Math.round(value * 100)} />
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

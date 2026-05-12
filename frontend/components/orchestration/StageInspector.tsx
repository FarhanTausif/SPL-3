'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { PipelineStage } from '@/lib/orchestration'
import { StatusBadge } from '@/components/orchestration/StatusBadge'

export function StageInspector({ stage }: { stage?: PipelineStage }) {
  if (!stage) return null
  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>{stage.label}</CardTitle>
            <CardDescription className="mt-1">{stage.role}</CardDescription>
          </div>
          <StatusBadge status={stage.status} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-xs uppercase text-muted-foreground">Provider</p>
            <p className="mt-1 break-words font-medium">{stage.provider || 'Pending'}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-muted-foreground">{stage.model ? 'Model' : 'Tool used'}</p>
            <p className="mt-1 break-words font-medium">{stage.model || stage.toolUsed || 'Not reported'}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-muted-foreground">Duration</p>
            <p className="mt-1 font-medium">{stage.durationMs ? `${stage.durationMs.toFixed(0)} ms` : 'Not measured'}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-muted-foreground">Evidence</p>
            <p className="mt-1 font-medium">{stage.evidence.length}</p>
          </div>
        </div>
        <Separator />
        <div>
          <p className="text-xs uppercase text-muted-foreground">Stage summary</p>
          <p className="mt-2 text-sm leading-6">{stage.summary}</p>
        </div>
        <Separator />
        <div>
          <p className="text-xs uppercase text-muted-foreground">Raw details</p>
          <ScrollArea className="mt-2 max-h-72 rounded-md border bg-muted/40 p-3">
            <pre className="whitespace-pre-wrap break-words text-xs leading-5">
              {JSON.stringify(stage.details, null, 2)}
            </pre>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  )
}

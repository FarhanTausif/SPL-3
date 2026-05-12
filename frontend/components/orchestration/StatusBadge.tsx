'use client'

import { Badge } from '@/components/ui/badge'
import { PipelineStatus } from '@/lib/orchestration'

export function StatusBadge({ status }: { status: PipelineStatus | string }) {
  const normalized = status.toLowerCase()
  if (normalized === 'complete' || normalized === 'completed') {
    return <Badge variant="success">Complete</Badge>
  }
  if (normalized === 'running' || normalized === 'queued') {
    return <Badge>Running</Badge>
  }
  if (normalized === 'warning' || normalized === 'needs_clarification') {
    return <Badge variant="warning">Review</Badge>
  }
  if (normalized === 'error' || normalized === 'failed' || normalized === 'reject') {
    return <Badge variant="destructive">Failed</Badge>
  }
  return <Badge variant="muted">Idle</Badge>
}

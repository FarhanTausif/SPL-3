'use client'

import { memo, useMemo } from 'react'
import ReactFlow, { Background, Edge, Handle, Node, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import { motion } from 'framer-motion'
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Circle,
  Code2,
  FileQuestion,
  GitBranch,
  Hammer,
  PackageCheck,
  ShieldCheck,
  Terminal,
} from 'lucide-react'
import { PipelineStage, PipelineStatus } from '@/lib/orchestration'
import { cn } from '@/lib/utils'
import { StatusBadge } from '@/components/orchestration/StatusBadge'

interface OrchestrationFlowProps {
  stages: PipelineStage[]
  selectedStageId: string
  onSelectStage: (stageId: string) => void
}

const positions: Record<string, { x: number; y: number }> = {
  prompt: { x: 0, y: 140 },
  clarification: { x: 220, y: 140 },
  generation: { x: 440, y: 140 },
  claim_extraction: { x: 690, y: 0 },
  static_analysis: { x: 690, y: 110 },
  sandbox: { x: 690, y: 220 },
  judge: { x: 930, y: 55 },
  cove: { x: 930, y: 185 },
  panel: { x: 1170, y: 55 },
  fusion: { x: 1170, y: 185 },
  policy: { x: 1400, y: 140 },
  repair: { x: 1620, y: 245 },
  result: { x: 1620, y: 45 },
}

const iconMap = {
  prompt: FileQuestion,
  clarification: Bot,
  generation: Code2,
  claim_extraction: GitBranch,
  static_analysis: ShieldCheck,
  sandbox: Terminal,
  judge: Bot,
  cove: PackageCheck,
  panel: ShieldCheck,
  fusion: GitBranch,
  policy: AlertTriangle,
  repair: Hammer,
  result: CheckCircle2,
}

function statusClasses(status: PipelineStatus, selected: boolean) {
  return cn(
    'w-[190px] rounded-lg border bg-card p-3 text-card-foreground shadow-sm transition-colors',
    status === 'running' && 'border-primary shadow-md ring-2 ring-primary/20',
    status === 'complete' && 'border-emerald-300 dark:border-emerald-800',
    status === 'warning' && 'border-amber-300 dark:border-amber-800',
    status === 'error' && 'border-destructive',
    status === 'idle' && 'opacity-70',
    selected && 'ring-2 ring-primary'
  )
}

function StageNode({ data }: { data: { stage: PipelineStage; selected: boolean; onSelect: () => void } }) {
  const Icon = iconMap[data.stage.id as keyof typeof iconMap] || Circle
  return (
    <button
      type="button"
      onClick={data.onSelect}
      className={statusClasses(data.stage.status, data.selected)}
      aria-label={`${data.stage.label} ${data.stage.status}`}
    >
      <Handle type="target" position={Position.Left} className="!bg-border" />
      <Handle type="source" position={Position.Right} className="!bg-border" />
      <div className="flex items-start gap-3 text-left">
        <span className="mt-0.5 rounded-md border bg-background p-1.5">
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate text-sm font-semibold">{data.stage.label}</p>
          </div>
          <p className="mt-1 truncate text-xs text-muted-foreground">{data.stage.role}</p>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        <StatusBadge status={data.stage.status} />
        {(data.stage.provider || data.stage.toolUsed) && (
          <span className="truncate text-xs text-muted-foreground">{data.stage.provider || data.stage.toolUsed}</span>
        )}
      </div>
    </button>
  )
}

const nodeTypes = { stage: StageNode }

export const OrchestrationFlow = memo(function OrchestrationFlow({
  stages,
  selectedStageId,
  onSelectStage,
}: OrchestrationFlowProps) {
  const nodes = useMemo<Node[]>(() => stages.map((stage) => ({
    id: stage.id,
    type: 'stage',
    position: positions[stage.id] || { x: 0, y: 0 },
    data: {
      stage,
      selected: selectedStageId === stage.id,
      onSelect: () => onSelectStage(stage.id),
    },
    draggable: false,
  })), [onSelectStage, selectedStageId, stages])

  const edges = useMemo<Edge[]>(() => [
    ['prompt', 'clarification'],
    ['clarification', 'generation'],
    ['generation', 'claim_extraction'],
    ['generation', 'static_analysis'],
    ['generation', 'sandbox'],
    ['claim_extraction', 'judge'],
    ['static_analysis', 'judge'],
    ['sandbox', 'cove'],
    ['judge', 'panel'],
    ['cove', 'panel'],
    ['panel', 'fusion'],
    ['fusion', 'policy'],
    ['policy', 'result'],
    ['policy', 'repair'],
    ['repair', 'generation'],
  ].map(([source, target]) => ({
    id: `${source}-${target}`,
    source,
    target,
    animated: stages.find((stage) => stage.id === source)?.status === 'running',
    style: { strokeWidth: 2 },
  })), [stages])

  return (
    <motion.div
      className="h-[520px] overflow-hidden rounded-lg border bg-background"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.45}
        maxZoom={1.2}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
      >
        <Background color="hsl(var(--muted-foreground))" gap={24} />
      </ReactFlow>
    </motion.div>
  )
})

import {
  EventRecord,
  EvidenceRecord,
  FusedHallucinationMetrics,
  HealthResponse,
  PolicyDecision,
  RepairResult,
  RunDetail,
  StageStatus,
} from '@/lib/api'

export type PipelineStatus = 'idle' | 'running' | 'complete' | 'warning' | 'error'

export interface PipelineStage {
  id: string
  label: string
  role: string
  group: 'input' | 'generation' | 'verification' | 'decision' | 'mitigation' | 'result'
  status: PipelineStatus
  provider?: string
  model?: string
  toolUsed?: string
  summary: string
  durationMs?: number
  evidence: EvidenceRecord[]
  details: Record<string, unknown>
}

export interface OrchestrationViewModel {
  stages: PipelineStage[]
  activeStageId: string
  terminal: boolean
  repairActive: boolean
  policyLabel: string
  riskPercent: number
  confidencePercent: number
  providerSummary: string
}

const STAGE_DEFINITIONS: Array<Omit<PipelineStage, 'status' | 'summary' | 'evidence' | 'details'>> = [
  { id: 'prompt', label: 'Prompt Intake', role: 'User request', group: 'input' },
  { id: 'clarification', label: 'Clarification', role: 'Clarifier agent', group: 'generation' },
  { id: 'generation', label: 'Generation', role: 'Coder agent', group: 'generation' },
  { id: 'claim_extraction', label: 'Claim Extraction', role: 'Claim extractor', group: 'verification' },
  { id: 'static_analysis', label: 'Static Analysis', role: 'Static verifier', group: 'verification' },
  { id: 'sandbox', label: 'Sandbox Execution', role: 'Runtime verifier', group: 'verification' },
  { id: 'judge', label: 'Judge Verification', role: 'LLM judge', group: 'verification' },
  { id: 'cove', label: 'CoVE Verification', role: 'Question verifier', group: 'verification' },
  { id: 'panel', label: 'Panel Consensus', role: 'Verifier panel', group: 'decision' },
  { id: 'fusion', label: 'Metric Fusion', role: 'Risk aggregator', group: 'decision' },
  { id: 'policy', label: 'Policy Decision', role: 'Policy coordinator', group: 'decision' },
  { id: 'repair', label: 'Mitigation Repair', role: 'Repair agent', group: 'mitigation' },
  { id: 'result', label: 'Final Result', role: 'Return payload', group: 'result' },
]

const evidenceKindToStage: Record<string, string> = {
  clarification: 'clarification',
  claim_extraction: 'claim_extraction',
  static_analysis: 'static_analysis',
  sandbox: 'sandbox',
  judge: 'judge',
  cove: 'cove',
  panel: 'panel',
  fusion: 'fusion',
  policy: 'policy',
  repair: 'repair',
  provider_invocation: 'generation',
  routing: 'generation',
  orchestration: 'generation',
}

const stageAliases: Record<string, string> = {
  lifecycle: 'prompt',
  extract_claims: 'claim_extraction',
  static_analysis: 'static_analysis',
  sandbox_verify: 'sandbox',
  tooling: 'claim_extraction',
  panel_verification: 'panel',
  policy_decide: 'policy',
}

export function buildOrchestrationViewModel({
  run,
  evidence,
  events,
  health,
}: {
  run: RunDetail | null
  evidence: EvidenceRecord[]
  events: EventRecord[]
  health?: HealthResponse | null
}): OrchestrationViewModel {
  const evidenceByStage = groupEvidenceByStage(evidence)
  const stageSummaryById = groupStageSummary(run?.stage_summary || [])
  const terminal = run?.status === 'completed' || run?.status === 'failed' || run?.status === 'needs_clarification'
  const repairActive = isRepairActive(run, evidence)

  const stages = STAGE_DEFINITIONS.map((definition) => {
    const stageEvidence = evidenceByStage[definition.id] || []
    const stageSummary = stageSummaryById[definition.id]
    const status = deriveStageStatus(definition.id, run, stageSummary, stageEvidence, events, terminal, repairActive)
    const owner = deriveOwner(definition.id, run, stageEvidence, evidence)
    return {
      ...definition,
      status,
      provider: owner.provider,
      model: owner.model,
      toolUsed: owner.toolUsed,
      summary: deriveSummary(definition.id, run, stageSummary, stageEvidence, health),
      durationMs: deriveDuration(stageSummary, stageEvidence),
      evidence: stageEvidence,
      details: {
        ...(stageSummary?.details || {}),
        ...(stageEvidence[stageEvidence.length - 1]?.payload || {}),
      },
    }
  })

  const activeStage = stages.find((stage) => stage.status === 'running')
    || [...stages].reverse().find((stage) => stage.status === 'complete' || stage.status === 'warning' || stage.status === 'error')
    || stages[0]

  const riskPercent = Math.round(((run?.fused_metrics?.overall_hallucination_score ?? policyRisk(run?.policy_decision)) || 0) * 100)
  const confidencePercent = Math.round(((run?.policy_decision?.score ?? (run ? 1 - riskPercent / 100 : 0)) || 0) * 100)

  return {
    stages,
    activeStageId: activeStage.id,
    terminal,
    repairActive,
    policyLabel: policyLabel(run?.policy_decision),
    riskPercent,
    confidencePercent,
    providerSummary: providerSummary(run, evidence, health),
  }
}

export function policyLabel(policy?: PolicyDecision | null): string {
  if (!policy) return 'Pending'
  return policy.state.replace(/_/g, ' ')
}

export function formatPercent(value?: number | null): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0%'
  return `${Math.round(value * 100)}%`
}

export function metricRows(metrics?: FusedHallucinationMetrics | null) {
  if (!metrics) return []
  return [
    ['Requirement alignment', metrics.requirement_alignment_score],
    ['Dependency plausibility', metrics.dependency_plausibility_score],
    ['API symbol validity', metrics.api_symbol_validity_score],
    ['Unsupported assumptions', 1 - metrics.unsupported_assumption_score],
    ['Execution validity', metrics.execution_validity_score],
    ['Tool-supported claims', metrics.tool_supported_claim_ratio],
  ] as const
}

function groupEvidenceByStage(evidence: EvidenceRecord[]): Record<string, EvidenceRecord[]> {
  return evidence.reduce<Record<string, EvidenceRecord[]>>((groups, record) => {
    const stage = evidenceKindToStage[record.kind] || stageAliases[String(record.payload.stage || '')] || record.kind
    groups[stage] = [...(groups[stage] || []), record]
    return groups
  }, {})
}

function groupStageSummary(stages: StageStatus[]): Record<string, StageStatus> {
  return stages.reduce<Record<string, StageStatus>>((groups, stage) => {
    const id = stageAliases[stage.stage] || stage.stage
    groups[id] = stage
    return groups
  }, {})
}

function deriveStageStatus(
  id: string,
  run: RunDetail | null,
  summary: StageStatus | undefined,
  stageEvidence: EvidenceRecord[],
  events: EventRecord[],
  terminal: boolean,
  repairActive: boolean
): PipelineStatus {
  if (!run) return id === 'prompt' ? 'running' : 'idle'
  if (run.status === 'failed') {
    const failed = summary?.status === 'failed' || events.some((event) => normalizeStageId(event.stage) === id && event.status === 'failed')
    if (failed || id === 'result') return 'error'
  }
  if (id === 'prompt') return run.status === 'queued' ? 'running' : 'complete'
  if (id === 'result') return terminal ? (run.status === 'failed' ? 'error' : 'complete') : 'idle'
  if (id === 'repair' && !repairActive) return 'idle'
  if (summary?.status === 'running') return 'running'
  if (summary?.status === 'needs_clarification') return 'warning'
  if (summary?.status === 'failed') return 'error'
  if (summary?.status === 'completed' || stageEvidence.length > 0) {
    if (id === 'policy' && run.policy_decision?.state === 'reject') return 'error'
    if (id === 'policy' && run.policy_decision?.state === 'warn_and_return_partial') return 'warning'
    return 'complete'
  }
  if (run.status === 'running') {
    const recentStage = normalizeStageId(events[events.length - 1]?.stage || '')
    if (recentStage === id) return 'running'
  }
  return 'idle'
}

function deriveOwner(
  id: string,
  run: RunDetail | null,
  stageEvidence: EvidenceRecord[],
  allEvidence: EvidenceRecord[]
): { provider?: string; model?: string; toolUsed?: string } {
  if (id === 'generation' && run) {
    const providerEvidence = allEvidence.find((item) => item.kind === 'provider_invocation')
    const invocations = Array.isArray(providerEvidence?.payload.invocations) ? providerEvidence?.payload.invocations as Record<string, unknown>[] : []
    const generation = invocations.find((item) => item.stage === 'generation' || item.role === 'coder')
    return {
      provider: String(generation?.provider_name || run.normalized_request.provider || ''),
      model: String(generation?.model || ''),
    }
  }
  const toolUsed = toolForStage(id, stageEvidence)
  const payload = stageEvidence[stageEvidence.length - 1]?.payload || {}
  const provider = payload.provider || payload.provider_name || payload.repair_provider
  const model = payload.model
  if (id === 'clarification' && run?.clarification_result?.metadata && typeof run.clarification_result.metadata === 'object') {
    const invocation = (run.clarification_result.metadata as Record<string, unknown>).provider_invocation as Record<string, unknown> | undefined
    return {
      provider: String(invocation?.provider_name || provider || ''),
      model: String(invocation?.model || model || ''),
    }
  }
  return {
    provider: provider ? String(provider) : undefined,
    model: model ? String(model) : undefined,
    toolUsed,
  }
}

function toolForStage(id: string, evidence: EvidenceRecord[]): string | undefined {
  if (id === 'claim_extraction') return 'claim_extractor'
  if (id === 'static_analysis') return 'static_analyzer'
  if (id === 'sandbox') return 'sandbox_compile_runner'
  const payload = evidence[evidence.length - 1]?.payload || {}
  if (Array.isArray(payload.invocations)) {
    const names = payload.invocations
      .map((item) => typeof item === 'object' && item ? String((item as Record<string, unknown>).tool_name || '') : '')
      .filter(Boolean)
    if (names.length > 0) return names.join(', ')
  }
  return undefined
}

function deriveSummary(
  id: string,
  run: RunDetail | null,
  summary: StageStatus | undefined,
  evidence: EvidenceRecord[],
  health?: HealthResponse | null
): string {
  if (!run && id === 'prompt') return 'Waiting for a prompt to create a verification run.'
  if (id === 'prompt') return run?.normalized_request.prompt || 'Prompt submitted.'
  if (id === 'generation') return `Target: ${run?.normalized_request.language || 'unknown'} via ${run?.normalized_request.provider || 'auto'}`
  if (id === 'policy') return run?.policy_decision?.reasons?.[0] || policyLabel(run?.policy_decision)
  if (id === 'fusion') return run?.fused_metrics ? `Overall hallucination risk ${formatPercent(run.fused_metrics.overall_hallucination_score)}` : 'Awaiting fused risk metrics.'
  if (id === 'repair') return repairSummary(run?.repair_result)
  if (id === 'result') return run?.status ? `Run ${run.status.replace(/_/g, ' ')}` : 'Awaiting result.'
  if (summary?.details && Object.keys(summary.details).length > 0) return compactJsonSummary(summary.details)
  if (evidence.length > 0) return compactJsonSummary(evidence[evidence.length - 1].payload)
  if (id === 'clarification' && health) {
    return `CrewAI ${health.orchestration.crewai_enabled ? 'enabled' : 'available check'}; worker ${String(health.orchestration.worker_readiness.state || 'unknown')}.`
  }
  return 'Pending upstream completion.'
}

function deriveDuration(summary?: StageStatus, evidence: EvidenceRecord[] = []): number | undefined {
  const payload = evidence[evidence.length - 1]?.payload || {}
  if (typeof payload.duration_ms === 'number') return payload.duration_ms
  if (Array.isArray(payload.invocations)) {
    const total = payload.invocations.reduce((sum, item) => {
      if (typeof item !== 'object' || item === null) return sum
      const duration = (item as Record<string, unknown>).duration_ms
      return sum + (typeof duration === 'number' ? duration : 0)
    }, 0)
    if (total > 0) return total
  }
  const invocation = payload.provider_invocation
  if (typeof invocation === 'object' && invocation !== null) {
    const latency = (invocation as Record<string, unknown>).latency_ms
    if (typeof latency === 'number') return latency
  }
  if (summary?.started_at && summary.finished_at) {
    const duration = Math.max(0, new Date(summary.finished_at).getTime() - new Date(summary.started_at).getTime())
    return duration > 0 ? duration : undefined
  }
  return undefined
}

function repairSummary(repair?: RepairResult | null): string {
  if (!repair || repair.outcome === 'skipped') return 'Repair branch inactive unless policy requests mitigation.'
  const latest = repair.attempts[repair.attempts.length - 1]
  return latest?.summary || `Repair ${repair.outcome}`
}

function compactJsonSummary(value: Record<string, unknown>): string {
  const keys = Object.keys(value).filter((key) => !['claims', 'findings', 'entries', 'invocations'].includes(key)).slice(0, 3)
  if (keys.length === 0) return 'Evidence captured for this stage.'
  return keys.map((key) => `${key}: ${String(value[key])}`).join(' · ')
}

function isRepairActive(run: RunDetail | null, evidence: EvidenceRecord[]): boolean {
  return Boolean(
    run?.policy_decision?.state === 'repair_and_retry'
      || evidence.some((item) => item.kind === 'repair')
  )
}

function policyRisk(policy?: PolicyDecision | null): number {
  if (!policy) return 0
  if (policy.state === 'reject') return 1
  if (policy.state === 'repair_and_retry') return 0.75
  if (policy.state === 'warn_and_return_partial' || policy.state === 'clarify') return 0.5
  return Math.max(0, 1 - policy.score)
}

function providerSummary(run: RunDetail | null, evidence: EvidenceRecord[], health?: HealthResponse | null): string {
  const providers = new Set<string>()
  if (run?.normalized_request.provider) providers.add(run.normalized_request.provider)
  evidence.forEach((item) => {
    const provider = item.payload.provider || item.payload.provider_name || item.payload.repair_provider
    if (provider) providers.add(String(provider))
  })
  if (providers.size > 0) return Array.from(providers).join(', ')
  const healthProviders = health ? Object.entries(health.providers).filter(([, ready]) => ready).map(([name]) => name) : []
  return healthProviders.join(', ') || 'No provider selected yet'
}

function normalizeStageId(stage: string): string {
  return stageAliases[stage] || stage
}

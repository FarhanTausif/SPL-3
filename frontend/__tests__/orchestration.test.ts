import { describe, expect, it } from 'vitest'
import { buildOrchestrationViewModel, metricRows, policyLabel } from '@/lib/orchestration'
import { EvidenceRecord, RunDetail } from '@/lib/api'

const baseRun: RunDetail = {
  run_id: 'run-1',
  created_at: '2026-05-05T00:00:00Z',
  status: 'completed',
  normalized_request: {
    prompt: 'Write Python code.',
    language: 'python',
    risk_level: 'medium',
    latency_budget_seconds: 15,
    provider: 'fake',
    run_mode: 'basic',
    acceptance_criteria: [],
  },
  policy_decision: {
    state: 'accept',
    reasons: ['All checks passed.'],
    hard_fail: false,
    score: 0.91,
    metrics: {},
  },
  fused_metrics: {
    requirement_alignment_score: 0.9,
    dependency_plausibility_score: 0.9,
    api_symbol_validity_score: 0.9,
    unsupported_assumption_score: 0.1,
    execution_validity_score: 1,
    judge_disagreement_score: 0,
    tool_supported_claim_ratio: 1,
    overall_hallucination_score: 0.08,
    metadata: {},
  },
  stage_summary: [
    { stage: 'generation', status: 'completed', details: { provider: 'fake' } },
    { stage: 'policy', status: 'completed', details: { policy_state: 'accept' } },
  ],
  evidence_summary: {},
}

describe('orchestration view model', () => {
  it('derives stage state from backend evidence and stage summary', () => {
    const evidence: EvidenceRecord[] = [
      {
        id: 'ev-1',
        kind: 'judge',
        payload: {
          provider: 'fake',
          model: 'fake-judge',
          duration_ms: 120,
          verdict: 'pass',
        },
      },
    ]

    const view = buildOrchestrationViewModel({ run: baseRun, evidence, events: [] })
    const judge = view.stages.find((stage) => stage.id === 'judge')
    const repair = view.stages.find((stage) => stage.id === 'repair')

    expect(judge?.status).toBe('complete')
    expect(judge?.provider).toBe('fake')
    expect(judge?.model).toBe('fake-judge')
    expect(judge?.durationMs).toBe(120)
    expect(repair?.status).toBe('idle')
    expect(view.riskPercent).toBe(8)
  })

  it('formats policy and metric rows without legacy confidence fields', () => {
    expect(policyLabel(baseRun.policy_decision)).toBe('accept')
    expect(metricRows(baseRun.fused_metrics)).toHaveLength(6)
  })
})

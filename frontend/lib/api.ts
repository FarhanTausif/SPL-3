import axios, { AxiosError } from 'axios'

const CONFIGURED_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function getApiBaseUrl(): string {
  if (typeof window === 'undefined') return CONFIGURED_API_BASE_URL
  try {
    const configured = new URL(CONFIGURED_API_BASE_URL)
    if (configured.hostname === 'localhost' || configured.hostname === '127.0.0.1') {
      configured.hostname = window.location.hostname === 'localhost' ? 'localhost' : '127.0.0.1'
      return configured.toString().replace(/\/$/, '')
    }
  } catch {
    return CONFIGURED_API_BASE_URL
  }
  return CONFIGURED_API_BASE_URL
}

export const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export type RiskLevel = 'low' | 'medium' | 'high'
export type RunMode = 'basic' | 'advanced'
export type RunStatus = 'queued' | 'running' | 'needs_clarification' | 'completed' | 'failed'
export type PolicyState = 'accept' | 'warn_and_return_partial' | 'reject' | 'repair_and_retry' | 'clarify'

export interface ToolPolicy {
  max_calls_per_role?: number
  timeout_seconds?: number
  allow_repo_context?: boolean
  allow_web_lookup?: boolean
  allowed_domains?: string[]
}

export interface CreateRunRequest {
  prompt: string
  language_hint?: string
  risk_level?: RiskLevel
  latency_budget_seconds?: number
  provider?: string | null
  run_mode?: RunMode
  target_runtime?: string | null
  framework_hint?: string | null
  acceptance_criteria?: string[]
  tool_policy?: ToolPolicy | null
}

export interface NormalizedRequest {
  prompt: string
  language: string
  risk_level: RiskLevel
  latency_budget_seconds: number
  provider: string
  run_mode: RunMode
  target_runtime?: string | null
  framework_hint?: string | null
  acceptance_criteria: string[]
  tool_policy?: ToolPolicy | null
}

export interface StageStatus {
  stage: string
  status: string
  started_at?: string | null
  finished_at?: string | null
  details: Record<string, unknown>
}

export interface CoderOutput {
  provider: string
  model: string
  language: string
  code: string
  assumptions: string[]
  dependencies: string[]
  files_touched: string[]
  execution_notes: string[]
  metadata: Record<string, unknown>
}

export interface PolicyDecision {
  state: PolicyState
  reasons: string[]
  hard_fail: boolean
  score: number
  metrics: Record<string, unknown>
}

export interface FusedHallucinationMetrics {
  requirement_alignment_score: number
  dependency_plausibility_score: number
  api_symbol_validity_score: number
  unsupported_assumption_score: number
  execution_validity_score: number
  judge_disagreement_score: number
  tool_supported_claim_ratio: number
  overall_hallucination_score: number
  metadata: Record<string, unknown>
}

export interface RepairAttempt {
  attempt_number: number
  trigger: string
  provider: string
  model: string
  duration_ms: number
  input_code: string
  output_code?: string | null
  summary: string
  metadata: Record<string, unknown>
}

export interface RepairResult {
  outcome: 'attempted' | 'succeeded' | 'failed' | 'skipped'
  attempts: RepairAttempt[]
  final_attempt_number: number
  metrics: Record<string, unknown>
}

export interface RunResponse {
  run_id: string
  normalized_request: NormalizedRequest
  status: RunStatus
  stage_summary: StageStatus[]
  clarification_result?: Record<string, unknown> | null
  fused_metrics?: FusedHallucinationMetrics | null
  coder_output?: CoderOutput | null
  extracted_claims?: Record<string, unknown>[]
  static_findings?: Record<string, unknown>[]
  sandbox_result?: Record<string, unknown> | null
  judge_result?: Record<string, unknown> | null
  cove_result?: Record<string, unknown> | null
  repair_result?: RepairResult | null
  policy_decision?: PolicyDecision | null
  evidence_ids?: string[]
}

export interface RunDetail {
  run_id: string
  created_at: string
  normalized_request: NormalizedRequest
  status: RunStatus
  policy_decision?: PolicyDecision | null
  clarification_result?: Record<string, unknown> | null
  fused_metrics?: FusedHallucinationMetrics | null
  coder_output?: CoderOutput | null
  repair_result?: RepairResult | null
  stage_summary: StageStatus[]
  evidence_summary: Record<string, number>
}

export interface EvidenceRecord {
  id?: string | null
  run_id?: string | null
  kind: string
  payload: Record<string, unknown>
  created_at?: string | null
}

export interface EventRecord {
  sequence: number
  event_type: string
  stage: string
  status: string
  message: string
  created_at?: string | null
  payload: Record<string, unknown>
}

export interface HealthResponse {
  status: string
  version: string
  providers: Record<string, boolean>
  orchestration: {
    configured_mode: string
    crewai_available: boolean
    crewai_enabled: boolean
    advanced_run_mode: string
    worker_id: string
    worker_freshness: Record<string, unknown>
    queue_backlog: Record<string, unknown>
    worker_readiness: Record<string, unknown>
    provider_role_readiness: Record<string, unknown>
    routing_policy_version: string
    prompt_policy_version: string
    provider_health_details: Record<string, Record<string, unknown>>
    live_provider_readiness: Record<string, unknown>
  }
}

export interface RunSnapshot {
  run: RunDetail
  evidence: EvidenceRecord[]
  events: EventRecord[]
  health?: HealthResponse
}

export const runApi = {
  createRun: async (request: CreateRunRequest): Promise<RunResponse> => {
    try {
      const response = await apiClient.post<RunResponse>('/v1/runs', request)
      return response.data
    } catch (error) {
      throw handleApiError(error)
    }
  },

  getRunStatus: async (runId: string): Promise<RunDetail> => {
    try {
      const response = await apiClient.get<RunDetail>(`/v1/runs/${runId}`)
      return response.data
    } catch (error) {
      throw handleApiError(error)
    }
  },

  getRunEvidence: async (runId: string): Promise<EvidenceRecord[]> => {
    try {
      const response = await apiClient.get<EvidenceRecord[]>(`/v1/runs/${runId}/evidence`)
      return response.data || []
    } catch (error) {
      throw handleApiError(error)
    }
  },

  getRunEvents: async (runId: string): Promise<EventRecord[]> => {
    try {
      const response = await apiClient.get<EventRecord[]>(`/v1/runs/${runId}/events`)
      return response.data || []
    } catch (error) {
      throw handleApiError(error)
    }
  },

  getHealth: async (): Promise<HealthResponse> => {
    try {
      const response = await apiClient.get<HealthResponse>('/health')
      return response.data
    } catch (error) {
      throw handleApiError(error)
    }
  },
}

interface ApiErrorResponse {
  detail?: string | { msg: string }[]
  message?: string
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: ApiErrorResponse
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function handleApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorResponse>
    const status = axiosError.response?.status || 500
    const data = axiosError.response?.data
    let message = 'An error occurred'

    if (data?.detail) {
      message = typeof data.detail === 'string' ? data.detail : data.detail.map((e) => e.msg).join(', ')
    } else if (data?.message) {
      message = data.message
    } else if (axiosError.code === 'ECONNABORTED') {
      message = `Backend request timed out at ${getApiBaseUrl()}`
    } else if (axiosError.message) {
      message = `${axiosError.message} (${getApiBaseUrl()})`
    }

    return new ApiError(status, message, data)
  }

  return new ApiError(500, 'Unknown error occurred', { message: String(error) })
}

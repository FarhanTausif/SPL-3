import axios, { AxiosError } from 'axios'

// API client for backend communication
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface CreateRunRequest {
  prompt: string
  language: string
  risk_level?: string
  max_retries?: number
}

export interface RunResponse {
  run_id: string
  status: string
  created_at: string
  updated_at: string
  user_prompt?: string
  generated_code?: string
  hallucination_detected?: boolean
  confidence?: number
  verdict?: string
}

export interface EvidenceRecord {
  id: string
  run_id: string
  evidence_kind: string
  finding: string
  severity?: string
  timestamp: string
}

export interface EventRecord {
  id: string
  run_id: string
  event_type: string
  details: Record<string, unknown>
  timestamp: string
}

export interface HealthResponse {
  status: string
  providers: Record<string, string>
  worker_count: number
  queue_depth: number
}

// API Endpoints
export const runApi = {
  // Create a new verification run
  createRun: async (request: CreateRunRequest): Promise<RunResponse> => {
    try {
      const response = await apiClient.post<RunResponse>('/v1/runs', request)
      return response.data
    } catch (error) {
      throw handleApiError(error)
    }
  },

  // Get run status by ID
  getRunStatus: async (runId: string): Promise<RunResponse> => {
    try {
      const response = await apiClient.get<RunResponse>(`/v1/runs/${runId}`)
      return response.data
    } catch (error) {
      throw handleApiError(error)
    }
  },

  // Get run evidence
  getRunEvidence: async (runId: string): Promise<EvidenceRecord[]> => {
    try {
      const response = await apiClient.get<EvidenceRecord[]>(
        `/v1/runs/${runId}/evidence`
      )
      return response.data || []
    } catch (error) {
      throw handleApiError(error)
    }
  },

  // Get run events
  getRunEvents: async (runId: string): Promise<EventRecord[]> => {
    try {
      const response = await apiClient.get<EventRecord[]>(
        `/v1/runs/${runId}/events`
      )
      return response.data || []
    } catch (error) {
      throw handleApiError(error)
    }
  },

  // Check health status
  getHealth: async (): Promise<HealthResponse> => {
    try {
      const response = await apiClient.get<HealthResponse>('/health')
      return response.data
    } catch (error) {
      throw handleApiError(error)
    }
  },
}

// Error handling
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
      if (typeof data.detail === 'string') {
        message = data.detail
      } else if (Array.isArray(data.detail)) {
        message = data.detail.map((e) => e.msg).join(', ')
      }
    } else if (data?.message) {
      message = data.message
    } else if (axiosError.message) {
      message = axiosError.message
    }

    return new ApiError(status, message, data)
  }

  return new ApiError(500, 'Unknown error occurred', {
    message: String(error),
  })
}

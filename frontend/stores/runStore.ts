import { create } from 'zustand'
import { RunResponse, EvidenceRecord, EventRecord } from '@/lib/api'

export interface RunStore {
  // Current run
  runId: string | null
  currentRun: RunResponse | null
  evidence: EvidenceRecord[]
  events: EventRecord[]

  // UI State
  isLoading: boolean
  error: string | null
  pollActive: boolean

  // Actions
  setRunId: (id: string) => void
  setCurrentRun: (run: RunResponse) => void
  setEvidence: (evidence: EvidenceRecord[]) => void
  setEvents: (events: EventRecord[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setPollActive: (active: boolean) => void
  reset: () => void
}

export const useRunStore = create<RunStore>((set) => ({
  runId: null,
  currentRun: null,
  evidence: [],
  events: [],
  isLoading: false,
  error: null,
  pollActive: false,

  setRunId: (id) => set({ runId: id }),
  setCurrentRun: (run) => set({ currentRun: run }),
  setEvidence: (evidence) => set({ evidence }),
  setEvents: (events) => set({ events }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setPollActive: (active) => set({ pollActive: active }),
  reset: () => set({
    runId: null,
    currentRun: null,
    evidence: [],
    events: [],
    isLoading: false,
    error: null,
    pollActive: false,
  }),
}))

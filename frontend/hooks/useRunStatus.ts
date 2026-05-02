import { useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { runApi } from '@/lib/api'
import { useRunStore } from '@/stores/runStore'

// Hook for polling run status
export function useRunStatus(runId: string | null, enabled = true) {
  const setCurrentRun = useRunStore((state) => state.setCurrentRun)
  const setError = useRunStore((state) => state.setError)
  const setPollActive = useRunStore((state) => state.setPollActive)

  const query = useQuery({
    queryKey: ['run', runId],
    queryFn: () => {
      if (!runId) throw new Error('No run ID provided')
      return runApi.getRunStatus(runId)
    },
    enabled: !!runId && enabled,
    refetchInterval: 2000, // Poll every 2 seconds
    refetchIntervalInBackground: true,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  })

  // Update store when run data changes
  useEffect(() => {
    if (query.data) {
      setCurrentRun(query.data)
      setPollActive(query.data.status === 'queued' || query.data.status === 'started')
    }
  }, [query.data, setCurrentRun, setPollActive])

  // Handle errors
  useEffect(() => {
    if (query.error) {
      const errorMessage =
        query.error instanceof Error ? query.error.message : 'Failed to fetch run status'
      setError(errorMessage)
    }
  }, [query.error, setError])

  return query
}

// Hook for fetching evidence
export function useRunEvidence(runId: string | null) {
  const setEvidence = useRunStore((state) => state.setEvidence)

  const query = useQuery({
    queryKey: ['evidence', runId],
    queryFn: () => {
      if (!runId) throw new Error('No run ID provided')
      return runApi.getRunEvidence(runId)
    },
    enabled: !!runId,
    retry: 3,
  })

  // Update store when evidence changes
  useEffect(() => {
    if (query.data) {
      setEvidence(query.data)
    }
  }, [query.data, setEvidence])

  return query
}

// Hook for fetching events
export function useRunEvents(runId: string | null) {
  const setEvents = useRunStore((state) => state.setEvents)

  const query = useQuery({
    queryKey: ['events', runId],
    queryFn: () => {
      if (!runId) throw new Error('No run ID provided')
      return runApi.getRunEvents(runId)
    },
    enabled: !!runId,
    retry: 3,
  })

  // Update store when events change
  useEffect(() => {
    if (query.data) {
      setEvents(query.data)
    }
  }, [query.data, setEvents])

  return query
}

// Hook for checking health
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => runApi.getHealth(),
    refetchInterval: 30000, // Check every 30 seconds
    retry: true,
  })
}

// Hook to stop polling when run is complete
export function useStopPollingWhenComplete(runId: string | null) {
  const queryClient = useQueryClient()
  const currentRun = useRunStore((state) => state.currentRun)

  useEffect(() => {
    if (runId && currentRun && (currentRun.status === 'completed' || currentRun.status === 'failed')) {
      // Stop polling by disabling the query
      queryClient.setQueryData(['run', runId], currentRun, {
        updatedAt: Date.now(),
      })
    }
  }, [runId, currentRun, queryClient])
}

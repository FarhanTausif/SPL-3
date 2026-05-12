/**
 * Real-time Update Hooks
 * Custom React hooks for WebSocket-based run and agent updates
 * with automatic fallback to polling if WebSocket unavailable
 */

'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { getWebSocketClient, WSMessage, RunUpdateData, AgentUpdateData, EvidenceCollectedData } from '@/lib/websocket';
import { useQuery } from '@tanstack/react-query';
import { apiClient, EventRecord, EvidenceRecord, RunDetail, RunSnapshot, StageStatus } from '@/lib/api';
import { useRunStore } from '@/stores/runStore';

/**
 * Hook for real-time run updates via WebSocket or polling fallback
 */
export function useRunUpdates(
  runId: string,
  onStatusChange?: (status: string) => void,
  onAgentUpdate?: (agentName: string, status: string) => void
) {
  const wsClient = getWebSocketClient();
  const unsubscribeRef = useRef<(() => void)[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const setCurrentRun = useRunStore((state) => state.setCurrentRun);
  const setEvidence = useRunStore((state) => state.setEvidence);
  const setEvents = useRunStore((state) => state.setEvents);

  // Fallback polling query
  const { data: pollData, isFetching } = useQuery({
    queryKey: ['run', runId, 'status'],
    queryFn: () => apiClient.get(`/v1/runs/${runId}`).then(res => res.data),
    refetchInterval: wsConnected ? undefined : 2000, // Only poll if WS not connected
    enabled: !!runId,
    staleTime: wsConnected ? Infinity : 1000,
  });

  useEffect(() => {
    if (!pollData || wsConnected) return;
    setCurrentRun(pollData as RunDetail);
  }, [pollData, setCurrentRun, wsConnected]);

  useEffect(() => {
    if (!runId) return;

    // Try WebSocket first
    wsClient
      .connect(runId)
      .then(() => {
        setWsConnected(true);
        console.log('[useRunUpdates] WebSocket connected');

        const unsubSnapshot = wsClient.on('run.snapshot', (msg: WSMessage<RunSnapshot>) => {
          if (msg.data.run) setCurrentRun(msg.data.run);
          setEvidence(msg.data.evidence || []);
          setEvents(msg.data.events || []);
          if (msg.data.run?.status && onStatusChange) onStatusChange(msg.data.run.status);
        });

        // Subscribe to run updates
        const unsubRun = wsClient.on('run.updated', (msg: WSMessage<RunUpdateData>) => {
          if (msg.data.status && onStatusChange) {
            onStatusChange(msg.data.status);
          }
        });

        const unsubStage = wsClient.on('stage.updated', (msg: WSMessage<{ run: RunDetail; stage: StageStatus }>) => {
          if (msg.data.run) setCurrentRun(msg.data.run);
        });

        const unsubEvidence = wsClient.on('evidence.collected', (msg: WSMessage<{ evidence: EvidenceRecord[]; events: EventRecord[] }>) => {
          setEvidence(msg.data.evidence || []);
          setEvents(msg.data.events || []);
        });

        // Subscribe to run completion
        const unsubComplete = wsClient.on('run.completed', (msg: WSMessage<RunSnapshot>) => {
          if (msg.data.run) setCurrentRun(msg.data.run);
          setEvidence(msg.data.evidence || []);
          setEvents(msg.data.events || []);
          if (onStatusChange) {
            onStatusChange('completed');
          }
          wsClient.disconnect();
          setWsConnected(false);
        });

        const unsubFailed = wsClient.on('run.failed', (msg: WSMessage<RunSnapshot>) => {
          if (msg.data.run) setCurrentRun(msg.data.run);
          setEvidence(msg.data.evidence || []);
          setEvents(msg.data.events || []);
          if (onStatusChange) onStatusChange('failed');
          wsClient.disconnect();
          setWsConnected(false);
        });

        // Subscribe to agent updates
        const unsubAgent = wsClient.on('agent.updated', (msg: WSMessage<AgentUpdateData>) => {
          if (msg.data.agentName && msg.data.status && onAgentUpdate) {
            onAgentUpdate(msg.data.agentName, msg.data.status);
          }
        });

        unsubscribeRef.current = [unsubSnapshot, unsubRun, unsubStage, unsubEvidence, unsubComplete, unsubFailed, unsubAgent];
      })
      .catch((error) => {
        console.warn('[useRunUpdates] WebSocket connection failed, using polling:', error);
        setWsConnected(false);
        // Polling will handle updates
      });

    return () => {
      unsubscribeRef.current.forEach((unsub) => unsub?.());
      wsClient.disconnect();
      setWsConnected(false);
    };
  }, [runId, onStatusChange, onAgentUpdate, wsClient]);

  return {
    isWSConnected: wsConnected,
    isPolling: !wsConnected,
    isFetching,
  };
}

/**
 * Hook for real-time agent execution stream
 */
export function useAgentStream(
  runId: string,
  agentName: string,
  onUpdate?: (data: AgentUpdateData) => void,
  onComplete?: (data: AgentUpdateData) => void
) {
  const wsClient = getWebSocketClient();
  const unsubscribeRef = useRef<(() => void)[]>([]);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    if (!runId || !agentName) return;

    wsClient
      .connect(runId)
      .then(() => {
        setWsConnected(true);

        // Subscribe to this specific agent's updates
        const unsubUpdate = wsClient.on('agent.updated', (msg: WSMessage<AgentUpdateData>) => {
          if (msg.data.agentName === agentName && onUpdate) {
            onUpdate(msg.data);
          }
        });

        // Subscribe to agent completion
        const unsubComplete = wsClient.on('agent.completed', (msg: WSMessage<AgentUpdateData>) => {
          if (msg.data.agentName === agentName && onComplete) {
            onComplete(msg.data);
          }
        });

        unsubscribeRef.current = [unsubUpdate, unsubComplete];
      })
      .catch((error) => {
        console.warn('[useAgentStream] WebSocket failed:', error);
        setWsConnected(false);
      });

    return () => {
      unsubscribeRef.current.forEach((unsub) => unsub?.());
    };
  }, [runId, agentName, onUpdate, onComplete, wsClient]);

  return { isWSConnected: wsConnected };
}

/**
 * Hook for real-time evidence collection stream
 */
export function useEvidenceStream(runId: string, onEvidenceCollected?: (data: EvidenceCollectedData) => void) {
  const wsClient = getWebSocketClient();
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    if (!runId) return;

    wsClient
      .connect(runId)
      .then(() => {
        setWsConnected(true);

        unsubscribeRef.current = wsClient.on('evidence.collected', (msg: WSMessage<EvidenceCollectedData>) => {
          if (onEvidenceCollected) {
            onEvidenceCollected(msg.data);
          }
        });
      })
      .catch((error) => {
        console.warn('[useEvidenceStream] WebSocket failed:', error);
        setWsConnected(false);
      });

    return () => {
      unsubscribeRef.current?.();
    };
  }, [runId, onEvidenceCollected, wsClient]);

  return { isWSConnected: wsConnected };
}

/**
 * Hook for listening to multiple message types at once
 */
export function useWSListener(
  runId: string,
  listeners: Record<string, (msg: WSMessage) => void>,
  enabled = true
) {
  const wsClient = getWebSocketClient();
  const unsubscribeRef = useRef<(() => void)[]>([]);

  useEffect(() => {
    if (!runId || !enabled) return;

    wsClient
      .connect(runId)
      .then(() => {
        const unsubs = Object.entries(listeners).map(([type, handler]) =>
          wsClient.on(type as any, handler)
        );
        unsubscribeRef.current = unsubs;
      })
      .catch((error) => {
        console.warn('[useWSListener] WebSocket failed:', error);
      });

    return () => {
      unsubscribeRef.current.forEach((unsub) => unsub?.());
    };
  }, [runId, enabled, listeners, wsClient]);
}

/**
 * WebSocket Client Infrastructure
 * Handles real-time connections for run updates and agent streaming
 * With automatic reconnection, fallback to polling, and error recovery
 */

export type WSMessageType =
  | 'run.snapshot'
  | 'run.started'
  | 'run.updated'
  | 'run.completed'
  | 'run.failed'
  | 'stage.updated'
  | 'agent.started'
  | 'agent.updated'
  | 'agent.completed'
  | 'evidence.collected'
  | 'error'
  | 'ping';

export interface WSMessage<T = any> {
  type: WSMessageType;
  runId: string;
  timestamp: number;
  data: T;
}

export interface RunUpdateData {
  status: 'queued' | 'running' | 'needs_clarification' | 'completed' | 'failed';
  stage?: string;
  progress?: number;
  elapsedSeconds?: number;
}

export interface AgentUpdateData {
  agentName: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  output?: string;
  error?: string;
  durationMs?: number;
}

export interface EvidenceCollectedData {
  evidenceKind: string;
  count: number;
  timestamp: number;
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private runId: string | null = null;
  private messageHandlers: Map<WSMessageType, Set<(msg: WSMessage) => void>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageQueue: WSMessage[] = [];
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private isManualClose = false;

  constructor(url: string) {
    this.url = url;
  }

  /**
   * Connect to WebSocket server for a specific run
   */
  connect(runId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.isConnecting) {
        reject(new Error('Connection already in progress'));
        return;
      }

      this.isConnecting = true;
      this.runId = runId;
      this.isManualClose = false;

      try {
        const wsUrl = `${this.url}/v1/runs/${runId}/stream`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log(`[WS] Connected to ${runId}`);
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.reconnectDelay = 1000;

          // Start heartbeat
          this.startHeartbeat();

          // Flush message queue
          this.flushQueue();

          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const msg: WSMessage = JSON.parse(event.data);
            this.handleMessage(msg);
          } catch (error) {
            console.error('[WS] Failed to parse message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('[WS] Connection error:', error);
          this.isConnecting = false;
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('[WS] Connection closed');
          this.isConnecting = false;
          this.stopHeartbeat();

          if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };
      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.isManualClose = true;
    this.stopHeartbeat();
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close(1000, 'Client disconnect');
    }
    this.ws = null;
    this.runId = null;
  }

  /**
   * Subscribe to specific message type
   */
  on(type: WSMessageType, handler: (msg: WSMessage) => void): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set());
    }
    this.messageHandlers.get(type)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(type);
      if (handlers) {
        handlers.delete(handler);
      }
    };
  }

  /**
   * Send message to server
   */
  send(type: string, data: any): void {
    const msg = { type, timestamp: Date.now(), data };

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    } else {
      // Queue message if not connected
      this.messageQueue.push(msg as WSMessage);
    }
  }

  /**
   * Get connection status
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  // Private methods

  private handleMessage(msg: WSMessage): void {
    const handlers = this.messageHandlers.get(msg.type);
    if (handlers) {
      handlers.forEach((handler) => handler(msg));
    }

    // Always handle ping
    if (msg.type === 'ping') {
      this.send('pong', { timestamp: Date.now() });
    }
  }

  private flushQueue(): void {
    while (this.messageQueue.length > 0) {
      const msg = this.messageQueue.shift();
      if (msg && this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(msg));
      }
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected()) {
        this.send('ping', { timestamp: Date.now() });
      }
    }, 30000); // Heartbeat every 30s
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    console.log(
      `[WS] Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );

    setTimeout(() => {
      if (this.runId && !this.isManualClose) {
        this.connect(this.runId).catch((error) => {
          console.error('[WS] Reconnection failed:', error);
          // Next attempt will schedule again if under max attempts
        });
      }
    }, this.reconnectDelay);

    // Exponential backoff: increase delay up to 30s
    this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 30000);
  }
}

// Singleton instance
let wsClient: WebSocketClient | null = null;

export function getWebSocketClient(): WebSocketClient {
  if (!wsClient) {
    const configuredBaseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    let baseUrl = configuredBaseUrl;
    if (typeof window !== 'undefined') {
      try {
        const parsed = new URL(configuredBaseUrl);
        if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') {
          parsed.hostname = window.location.hostname === 'localhost' ? 'localhost' : '127.0.0.1';
          baseUrl = parsed.toString().replace(/\/$/, '');
        }
      } catch {
        baseUrl = configuredBaseUrl;
      }
    }
    // Convert http/https to ws/wss
    const wsUrl = baseUrl.replace(/^http/, 'ws');
    wsClient = new WebSocketClient(wsUrl);
  }
  return wsClient;
}

export function resetWebSocketClient(): void {
  if (wsClient) {
    wsClient.disconnect();
  }
  wsClient = null;
}

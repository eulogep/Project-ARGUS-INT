// ==============================================================================
// ARGUS-INT — Resilient WebSocket Hook
// Exponential backoff + heartbeat + panic event listener
// ==============================================================================

'use client';

import { useEffect, useRef, useCallback, useState } from 'react';

interface UseWebSocketOptions {
  url: string;
  onMessage: (data: unknown) => void;
  onStatusChange?: (status: 'connecting' | 'open' | 'closed' | 'error') => void;
  heartbeatIntervalMs?: number;
  maxReconnectDelayMs?: number;
  enabled?: boolean;
}

export function useWebSocket({
  url,
  onMessage,
  onStatusChange,
  heartbeatIntervalMs = 30000,
  maxReconnectDelayMs = 30000,
  enabled = true,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const heartbeatTimer = useRef<NodeJS.Timeout | undefined>(undefined);
  const reconnectTimer = useRef<NodeJS.Timeout | undefined>(undefined);
  const [status, setStatus] = useState<'connecting' | 'open' | 'closed' | 'error'>('closed');

  const updateStatus = useCallback(
    (s: typeof status) => {
      setStatus(s);
      onStatusChange?.(s);
    },
    [onStatusChange]
  );

  const disconnect = useCallback(() => {
    clearInterval(heartbeatTimer.current);
    clearTimeout(reconnectTimer.current);
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    updateStatus('closed');
  }, [updateStatus]);

  const connect = useCallback(() => {
    if (!enabled) return;
    disconnect();
    updateStatus('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttempt.current = 0;
        updateStatus('open');

        // Start heartbeat
        heartbeatTimer.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, heartbeatIntervalMs);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong') return; // Heartbeat response
          onMessage(data);
        } catch {
          onMessage(event.data);
        }
      };

      ws.onerror = () => updateStatus('error');

      ws.onclose = () => {
        clearInterval(heartbeatTimer.current);
        updateStatus('closed');

        // Exponential backoff reconnect
        const delay = Math.min(
          1000 * Math.pow(2, reconnectAttempt.current),
          maxReconnectDelayMs
        );
        reconnectAttempt.current++;

        reconnectTimer.current = setTimeout(connect, delay);
      };
    } catch {
      updateStatus('error');
    }
  }, [url, enabled, onMessage, disconnect, updateStatus, heartbeatIntervalMs, maxReconnectDelayMs]);

  useEffect(() => {
    if (enabled) connect();

    // Listen for panic event to immediately close
    const handlePanic = () => disconnect();
    window.addEventListener('argus:panic', handlePanic);

    return () => {
      disconnect();
      window.removeEventListener('argus:panic', handlePanic);
    };
  }, [enabled, connect, disconnect]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { status, send, disconnect, reconnect: connect };
}

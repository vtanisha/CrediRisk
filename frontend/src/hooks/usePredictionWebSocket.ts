import { useEffect, useRef, useState, useCallback } from 'react';
import { api, ShapValue } from '../api/client';

export interface PredictionState {
  probability: number | null;
  delta: number | null;
  shapValues: ShapValue[];
  confidenceLower: number | null;
  confidenceUpper: number | null;
  isConnected: boolean;
}

const INITIAL_STATE: PredictionState = {
  probability: null,
  delta: null,
  shapValues: [],
  confidenceLower: null,
  confidenceUpper: null,
  isConnected: false,
};

export function usePredictionWebSocket(customerId: number | null) {
  const [state, setState] = useState<PredictionState>(INITIAL_STATE);
  const wsRef = useRef<WebSocket | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (customerId === null || isNaN(customerId)) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const url = api.getWsUrl(customerId);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      retryCountRef.current = 0;
      setState(s => ({ ...s, isConnected: true }));
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data);
        if (data.error) return;
        setState(s => ({
          ...s,
          probability: Math.round(data.new_default_probability * 100),
          delta: data.delta ?? null,
          shapValues: data.mock_shap_values ?? s.shapValues,
          confidenceLower: data.confidence_lower != null ? Math.round(data.confidence_lower * 100) : null,
          confidenceUpper: data.confidence_upper != null ? Math.round(data.confidence_upper * 100) : null,
        }));
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setState(s => ({ ...s, isConnected: false }));
      // Exponential backoff reconnect (max 30s)
      const delay = Math.min(1000 * 2 ** retryCountRef.current, 30_000);
      retryCountRef.current += 1;
      reconnectRef.current = setTimeout(() => {
        if (mountedRef.current) connect();
      }, delay);
    };

    ws.onerror = () => ws.close();
  }, [customerId]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendFeatures = useCallback((income: number, loanAmount: number) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ income, loan_amount: loanAmount }));
      }
    }, 300);
  }, []);

  return { ...state, sendFeatures };
}

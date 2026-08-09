import { useCallback, useEffect, useRef, useState } from "react";

const RECONNECT_DELAY_MS = 1500;

export default function useCockpitSocket() {
  const [state, setState] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const closedByUs = useRef(false);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${window.location.host}/ws`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "state") setState(msg.state);
      } catch (err) {
        console.error("useCockpitSocket: could not parse message", err);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (!closedByUs.current) {
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    closedByUs.current = false;
    connect();
    return () => {
      closedByUs.current = true;
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { state, connected };
}

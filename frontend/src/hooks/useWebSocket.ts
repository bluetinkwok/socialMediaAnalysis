import { useEffect, useRef, useState } from 'react';

interface UseWebSocketOptions {
  reconnectInterval?: number;
  reconnectAttempts?: number;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onMessage?: (event: MessageEvent) => void;
  onError?: (event: Event) => void;
}

interface UseWebSocketReturn {
  lastMessage: MessageEvent | null;
  readyState: number;
  sendMessage: (data: string | ArrayBufferLike | Blob | ArrayBufferView) => void;
}

/**
 * React hook for WebSocket connections
 * @param url WebSocket URL to connect to (set to null to not connect)
 * @param options Configuration options
 * @returns WebSocket state and methods
 */
export const useWebSocket = (
  url: string | null,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn => {
  const {
    reconnectInterval = 5000,
    reconnectAttempts = 10,
    onOpen,
    onClose,
    onMessage,
    onError,
  } = options;

  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const [readyState, setReadyState] = useState<number>(WebSocket.CONNECTING);
  
  const reconnectCount = useRef(0);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Function to create a new WebSocket connection
  const connect = () => {
    if (!url) return;
    
    // Close existing connection if any
    if (ws.current) {
      ws.current.close();
    }

    // Create new WebSocket connection
    const websocket = new WebSocket(url);
    
    // Set up event handlers
    websocket.onopen = (event) => {
      console.log('WebSocket connected:', url);
      setReadyState(WebSocket.OPEN);
      reconnectCount.current = 0;
      if (onOpen) onOpen(event);
    };

    websocket.onclose = (event) => {
      console.log('WebSocket closed:', url);
      setReadyState(WebSocket.CLOSED);
      
      // Attempt to reconnect if not closed cleanly
      if (!event.wasClean && reconnectCount.current < reconnectAttempts) {
        console.log(`Attempting to reconnect (${reconnectCount.current + 1}/${reconnectAttempts})...`);
        reconnectCount.current += 1;
        
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
        }
        
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      }
      
      if (onClose) onClose(event);
    };

    websocket.onmessage = (event) => {
      setLastMessage(event);
      if (onMessage) onMessage(event);
    };

    websocket.onerror = (event) => {
      console.error('WebSocket error:', event);
      if (onError) onError(event);
    };

    // Store WebSocket reference
    ws.current = websocket;
  };

  // Function to send a message through the WebSocket
  const sendMessage = (data: string | ArrayBufferLike | Blob | ArrayBufferView) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(data);
    } else {
      console.error('WebSocket is not connected');
    }
  };

  // Connect on mount or when URL changes
  useEffect(() => {
    if (url) {
      connect();
    }
    
    // Clean up on unmount or URL change
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
    };
  }, [url]);

  return {
    lastMessage,
    readyState,
    sendMessage,
  };
}; 
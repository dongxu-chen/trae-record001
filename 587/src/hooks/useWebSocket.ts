import { useEffect, useRef, useCallback } from 'react';
import { WSMessage, User, Annotation } from '../../shared/types';
import { OTOperation, createOperation } from '../../shared/ot';
import { useStore } from '../store/useStore';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const pendingOperations = useRef<OTOperation[]>([]);
  
  const {
    sessionId,
    currentUser,
    version,
    setIsConnected,
    setAnnotations,
    setUsers,
    addAnnotation,
    updateAnnotation,
    deleteAnnotation,
    setChartData,
    setChartType,
    setVersion,
    setPermissions,
  } = useStore();

  const connect = useCallback((sessId: string, user: User, permissions: 'read' | 'write' = 'write') => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      setIsConnected(true);
      sendMessage('user_join', { sessionId: sessId, user, permissions });
      
      pendingOperations.current.forEach(op => {
        sendMessage('operation', { sessionId: sessId, operation: op });
      });
      pendingOperations.current = [];
    };

    wsRef.current.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };
  }, [setIsConnected]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const handleMessage = useCallback((message: WSMessage) => {
    const { type, payload } = message;

    switch (type) {
      case 'session_state':
        setAnnotations(payload.annotations || []);
        setUsers(payload.users || []);
        if (payload.chartData) setChartData(payload.chartData);
        if (payload.chartType) setChartType(payload.chartType);
        if (payload.version !== undefined) setVersion(payload.version);
        if (payload.permissions) setPermissions(payload.permissions);
        break;
      case 'user_join':
        setUsers(payload.users || []);
        break;
      case 'user_leave':
        setUsers(payload.users || []);
        break;
      case 'operation':
        handleIncomingOperation(payload.operation);
        break;
      case 'error':
        console.error('Server error:', payload.message);
        alert(payload.message);
        break;
    }
  }, [setAnnotations, setUsers, setChartData, setChartType, setVersion, setPermissions]);

  const handleIncomingOperation = useCallback((operation: OTOperation) => {
    const currentVersion = useStore.getState().version;
    
    if (operation.version > currentVersion) {
      setVersion(operation.version);
    }

    switch (operation.type) {
      case 'add':
        const newAnnotation: Annotation = {
          id: operation.annotationId,
          ...operation.payload,
          version: operation.version,
          createdAt: operation.timestamp,
          updatedAt: operation.timestamp,
        };
        addAnnotation(newAnnotation);
        break;
      case 'update':
        const existing = useStore.getState().annotations.find(a => a.id === operation.annotationId);
        if (existing) {
          const updated: Annotation = {
            ...existing,
            ...operation.payload,
            version: operation.version,
            updatedAt: operation.timestamp,
          };
          updateAnnotation(updated);
        }
        break;
      case 'delete':
        deleteAnnotation(operation.annotationId);
        break;
    }
  }, [addAnnotation, updateAnnotation, deleteAnnotation, setVersion]);

  const sendMessage = useCallback((type: string, payload: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && currentUser) {
      wsRef.current.send(
        JSON.stringify({
          type,
          payload,
          userId: currentUser.id,
          timestamp: Date.now(),
        })
      );
      return true;
    }
    return false;
  }, [currentUser]);

  const sendCursorUpdate = useCallback((cursor: { x: number; y: number }) => {
    if (sessionId) {
      sendMessage('cursor_update', { sessionId, cursor });
    }
  }, [sessionId, sendMessage]);

  const sendOTOperation = useCallback((operation: OTOperation) => {
    if (sessionId) {
      const sent = sendMessage('operation', { sessionId, operation });
      if (!sent) {
        pendingOperations.current.push(operation);
      }
    }
  }, [sessionId, sendMessage]);

  const sendAnnotationAdd = useCallback((annotation: Omit<Annotation, 'id' | 'createdAt' | 'updatedAt' | 'version'>) => {
    if (sessionId && currentUser) {
      const { annotations, version: currentVersion } = useStore.getState();
      const tempId = `temp_${Date.now()}`;
      
      const operation = createOperation(
        'add',
        tempId,
        annotation,
        currentUser.id,
        currentVersion
      );
      
      const optimisticAnnotation: Annotation = {
        id: tempId,
        ...annotation,
        version: currentVersion + 1,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      
      addAnnotation(optimisticAnnotation);
      setVersion(currentVersion + 1);
      sendOTOperation(operation);
    }
  }, [sessionId, currentUser, addAnnotation, setVersion, sendOTOperation]);

  const sendAnnotationUpdate = useCallback((annotationId: string, updates: Partial<Annotation>) => {
    if (sessionId && currentUser) {
      const { annotations, version: currentVersion } = useStore.getState();
      const existing = annotations.find(a => a.id === annotationId);
      
      if (existing) {
        const operation = createOperation(
          'update',
          annotationId,
          updates,
          currentUser.id,
          currentVersion
        );
        
        const optimisticUpdate: Annotation = {
          ...existing,
          ...updates,
          version: currentVersion + 1,
          updatedAt: Date.now(),
        };
        updateAnnotation(optimisticUpdate);
        setVersion(currentVersion + 1);
        sendOTOperation(operation);
      }
    }
  }, [sessionId, currentUser, updateAnnotation, setVersion, sendOTOperation]);

  const sendAnnotationDelete = useCallback((annotationId: string) => {
    if (sessionId && currentUser) {
      const { version: currentVersion } = useStore.getState();
      
      const operation = createOperation(
        'delete',
        annotationId,
        {},
        currentUser.id,
        currentVersion
      );
      
      deleteAnnotation(annotationId);
      setVersion(currentVersion + 1);
      sendOTOperation(operation);
    }
  }, [sessionId, currentUser, deleteAnnotation, setVersion, sendOTOperation]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connect,
    disconnect,
    sendCursorUpdate,
    sendAnnotationAdd,
    sendAnnotationUpdate,
    sendAnnotationDelete,
    isConnected: useStore.getState().isConnected,
  };
}

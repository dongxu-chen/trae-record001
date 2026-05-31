import { WebSocketServer, WebSocket } from 'ws';
import { Server } from 'http';
import { WSMessage, User, Annotation } from '../../shared/types';
import { OTOperation } from '../../shared/ot';
import { store } from '../store/memoryStore';

interface ExtendedWebSocket extends WebSocket {
  sessionId?: string;
  userId?: string;
  permissions?: 'read' | 'write';
}

interface SessionClients {
  [sessionId: string]: Map<string, ExtendedWebSocket>;
}

class ChartAnnotationWSServer {
  private wss: WebSocketServer;
  private sessionClients: SessionClients = {};

  constructor(server: Server) {
    this.wss = new WebSocketServer({ server, path: '/ws' });
    this.setupHandlers();
  }

  private setupHandlers(): void {
    this.wss.on('connection', (ws: ExtendedWebSocket) => {
      console.log('New WebSocket connection');

      ws.on('message', (data: string) => {
        try {
          const message: WSMessage = JSON.parse(data);
          this.handleMessage(ws, message);
        } catch (error) {
          console.error('Failed to parse message:', error);
        }
      });

      ws.on('close', () => {
        this.handleDisconnect(ws);
      });

      ws.on('error', (error) => {
        console.error('WebSocket error:', error);
      });
    });
  }

  private handleMessage(ws: ExtendedWebSocket, message: WSMessage): void {
    const { type, payload, userId } = message;

    switch (type) {
      case 'user_join':
        this.handleUserJoin(ws, payload, userId);
        break;
      case 'cursor_update':
        this.handleCursorUpdate(payload, userId);
        break;
      case 'operation':
        this.handleOperation(ws, payload, userId);
        break;
    }
  }

  private handleUserJoin(
    ws: ExtendedWebSocket,
    payload: { sessionId: string; user: User; permissions?: 'read' | 'write' },
    userId: string
  ): void {
    const { sessionId, user, permissions = 'write' } = payload;
    
    ws.sessionId = sessionId;
    ws.userId = userId;
    ws.permissions = permissions;

    if (!this.sessionClients[sessionId]) {
      this.sessionClients[sessionId] = new Map();
    }
    this.sessionClients[sessionId].set(userId, ws);

    store.addUser(sessionId, user);

    const session = store.getSession(sessionId);
    const version = store.getVersion(sessionId);
    
    this.broadcastToSession(sessionId, {
      type: 'user_join',
      payload: { user, users: session?.users || [] },
      userId,
      timestamp: Date.now(),
    });

    ws.send(JSON.stringify({
      type: 'session_state',
      payload: {
        annotations: session?.annotations || [],
        users: session?.users || [],
        chartData: session?.chartData,
        chartType: session?.chartType,
        version,
        permissions,
      },
      userId: 'server',
      timestamp: Date.now(),
    }));
  }

  private handleCursorUpdate(payload: { sessionId: string; cursor: { x: number; y: number } }, userId: string): void {
    const { sessionId, cursor } = payload;
    
    store.updateUserCursor(sessionId, userId, cursor);

    this.broadcastToSession(sessionId, {
      type: 'cursor_update',
      payload: { userId, cursor },
      userId,
      timestamp: Date.now(),
    }, userId);
  }

  private handleOperation(
    ws: ExtendedWebSocket,
    payload: { sessionId: string; operation: OTOperation },
    userId: string
  ): void {
    if (ws.permissions === 'read') {
      ws.send(JSON.stringify({
        type: 'error',
        payload: { message: 'Read-only access: cannot modify annotations' },
        userId: 'server',
        timestamp: Date.now(),
      }));
      return;
    }

    const { sessionId, operation } = payload;
    
    const result = store.applyOTOperation(sessionId, operation);
    
    if (result.success && result.operation) {
      this.broadcastToSession(sessionId, {
        type: 'operation',
        payload: { operation: result.operation },
        userId,
        timestamp: Date.now(),
      });
    }
  }

  private handleDisconnect(ws: ExtendedWebSocket): void {
    const { sessionId, userId } = ws;
    
    if (sessionId && userId) {
      store.removeUser(sessionId, userId);
      
      if (this.sessionClients[sessionId]) {
        this.sessionClients[sessionId].delete(userId);
        
        if (this.sessionClients[sessionId].size === 0) {
          delete this.sessionClients[sessionId];
        } else {
          const session = store.getSession(sessionId);
          this.broadcastToSession(sessionId, {
            type: 'user_leave',
            payload: { userId, users: session?.users || [] },
            userId,
            timestamp: Date.now(),
          });
        }
      }
    }
    
    console.log('Client disconnected');
  }

  private broadcastToSession(sessionId: string, message: WSMessage, excludeUserId?: string): void {
    const clients = this.sessionClients[sessionId];
    if (!clients) return;

    const messageStr = JSON.stringify(message);
    
    clients.forEach((client, clientId) => {
      if (clientId !== excludeUserId && client.readyState === WebSocket.OPEN) {
        client.send(messageStr);
      }
    });
  }

  public close(): void {
    this.wss.close();
  }
}

export default ChartAnnotationWSServer;

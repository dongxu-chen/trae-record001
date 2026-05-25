import { WebSocketServer, WebSocket } from 'ws';
import type { Server as HTTPServer } from 'http';

interface ClientMap {
  [userId: string]: WebSocket[];
}

class WebSocketService {
  private wss: WebSocketServer | null = null;
  private clients: ClientMap = {};

  init(server: HTTPServer) {
    this.wss = new WebSocketServer({ server, path: '/ws' });

    this.wss.on('connection', (ws: WebSocket, req) => {
      const url = new URL(req.url || '/', 'http://localhost');
      const userId = url.searchParams.get('userId');

      if (!userId) {
        ws.close(4001, '未授权');
        return;
      }

      if (!this.clients[userId]) {
        this.clients[userId] = [];
      }
      this.clients[userId].push(ws);

      ws.on('close', () => {
        this.removeClient(userId, ws);
      });

      ws.on('error', () => {
        this.removeClient(userId, ws);
      });

      ws.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());
          if (message.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
          }
        } catch (err) {
          console.error('WebSocket消息解析错误:', err);
        }
      });

      ws.send(JSON.stringify({
        type: 'connected',
        message: 'WebSocket连接成功',
        timestamp: Date.now()
      }));
    });

    console.log('🔌 WebSocket 服务器已启动');
  }

  private removeClient(userId: string, ws: WebSocket) {
    if (this.clients[userId]) {
      this.clients[userId] = this.clients[userId].filter(client => client !== ws);
      if (this.clients[userId].length === 0) {
        delete this.clients[userId];
      }
    }
  }

  sendToUser(userId: string, data: any) {
    const clients = this.clients[userId];
    if (clients && clients.length > 0) {
      const message = JSON.stringify({
        ...data,
        timestamp: Date.now()
      });
      
      clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
          client.send(message);
        }
      });
    }
  }

  broadcast(data: any) {
    const message = JSON.stringify({
      ...data,
      timestamp: Date.now()
    });

    Object.values(this.clients).forEach(clients => {
      clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
          client.send(message);
        }
      });
    });
  }

  notifyDynamicCodeUpdate(userId: string, codeData: any) {
    this.sendToUser(userId, {
      type: 'dynamic_code_updated',
      action: 'update',
      data: codeData
    });
  }

  notifyDynamicCodeCreated(userId: string, codeData: any) {
    this.sendToUser(userId, {
      type: 'dynamic_code_created',
      action: 'create',
      data: codeData
    });
  }

  notifyDynamicCodeDeleted(userId: string, codeId: string) {
    this.sendToUser(userId, {
      type: 'dynamic_code_deleted',
      action: 'delete',
      data: { id: codeId }
    });
  }

  notifyScanUpdate(userId: string, codeId: string, scanCount: number) {
    this.sendToUser(userId, {
      type: 'scan_updated',
      action: 'scan',
      data: { id: codeId, scanCount }
    });
  }

  getConnectedUsers(): number {
    return Object.keys(this.clients).length;
  }

  getConnectionsCount(): number {
    return Object.values(this.clients).reduce((sum, clients) => sum + clients.length, 0);
  }
}

export const wsService = new WebSocketService();
export default wsService;

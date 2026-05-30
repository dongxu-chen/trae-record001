import { createServer } from 'http';
import { WebSocketServer, WebSocket } from 'ws';

const PORT = 3001;

const server = createServer();

const wss = new WebSocketServer({ server });

interface WSMessage {
  type: 'push_subtitle' | 'sync_state' | 'client_join' | 'client_leave' | 'heartbeat' | 'subtitle_update' | 'scroll_sync';
  payload?: any;
  clientId?: string;
  timestamp?: number;
}

const clients = new Map<string, WebSocket>();

function broadcast(message: WSMessage, excludeId?: string) {
  const data = JSON.stringify({ ...message, timestamp: Date.now() });
  clients.forEach((client, id) => {
    if (id !== excludeId && client.readyState === WebSocket.OPEN) {
      client.send(data);
    }
  });
}

wss.on('connection', (ws) => {
  const clientId = Math.random().toString(36).substr(2, 9);
  clients.set(clientId, ws);

  console.log(`[WS] Client connected: ${clientId} (total: ${clients.size})`);

  ws.send(JSON.stringify({
    type: 'client_join',
    clientId,
    timestamp: Date.now()
  }));

  broadcast({
    type: 'client_join',
    payload: { clientId, totalClients: clients.size },
    clientId
  });

  ws.on('message', (raw) => {
    try {
      const message: WSMessage = JSON.parse(raw.toString());

      switch (message.type) {
        case 'push_subtitle':
          broadcast({
            type: 'subtitle_update',
            payload: message.payload,
            clientId
          });
          console.log(`[WS] Subtitle push from ${clientId}:`, message.payload?.lines?.map((l: any) => l.text).join(' | '));
          break;

        case 'sync_state':
          broadcast({
            type: 'scroll_sync',
            payload: message.payload,
            clientId
          });
          break;

        case 'heartbeat':
          ws.send(JSON.stringify({ type: 'heartbeat', timestamp: Date.now() }));
          break;
      }
    } catch (e) {
      console.error('[WS] Invalid message:', e);
    }
  });

  ws.on('close', () => {
    clients.delete(clientId);
    console.log(`[WS] Client disconnected: ${clientId} (total: ${clients.size})`);
    broadcast({
      type: 'client_leave',
      payload: { clientId, totalClients: clients.size },
      clientId
    });
  });
});

server.listen(PORT, () => {
  console.log(`[WS] WebSocket server running on ws://localhost:${PORT}`);
  console.log(`[WS] Connect from client using: ws://localhost:${PORT}`);
});

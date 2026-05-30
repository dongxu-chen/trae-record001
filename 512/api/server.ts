import http from 'http';
import { WebSocketServer, WebSocket } from 'ws';
import app from './app.js';
import { ensureConnection, seedInitialRules, saveMetricData, getAllRules } from './services/redis.js';
import { evaluateMetric } from './services/alert-service.js';
import { generateMetricData } from './services/data-simulator.js';
import { getRelatedMetrics } from './services/alert-correlation.js';
import type { WebSocketMessage, MetricData } from './types.js';

const PORT = Number(process.env.PORT) || 3003;

const server = http.createServer(app);

const wss = new WebSocketServer({ noServer: true });

const clients = new Set<WebSocket>();

server.on('upgrade', (request, socket, head) => {
  wss.handleUpgrade(request, socket, head, (ws) => {
    wss.emit('connection', ws, request);
  });
});

function broadcast(message: WebSocketMessage): void {
  const data = JSON.stringify(message);
  for (const client of clients) {
    if (client.readyState === WebSocket.OPEN) {
      try {
        client.send(data);
      } catch {
        clients.delete(client);
      }
    }
  }
}

wss.on('connection', (ws: WebSocket) => {
  clients.add(ws);

  ws.on('message', (raw: Buffer) => {
    try {
      const message = JSON.parse(raw.toString()) as WebSocketMessage;
      if (message.type === 'config_update') {
        broadcast({ type: 'config_update', payload: message.payload });
      }
    } catch {
    }
  });

  ws.on('close', () => {
    clients.delete(ws);
  });

  ws.on('error', () => {
    clients.delete(ws);
  });

  ws.send(JSON.stringify({ type: 'config_update', payload: { connected: true } }));
});

async function startDataSimulation(): Promise<void> {
  await ensureConnection();
  await seedInitialRules();
  await getAllRules();

  setInterval(async () => {
    try {
      const metrics: MetricData[] = generateMetricData();

      for (const metric of metrics) {
        await saveMetricData(metric);
      }

      broadcast({ type: 'data', payload: metrics });

      for (const metric of metrics) {
        const alerts = await evaluateMetric(metric.metric, metric.value);
        for (const alert of alerts) {
          const relatedMetrics = getRelatedMetrics(alert.metric);
          const alertWithCorrelation = {
            ...alert,
            correlatedMetrics: relatedMetrics,
          };
          broadcast({ type: 'alert', payload: alertWithCorrelation });
        }
      }
    } catch (error) {
      console.error('Simulation tick error:', error);
    }
  }, 2000);
}

function start(port: number, maxAttempts = 10) {
  let started = false;
  const srv = server.listen(port, () => {
    if (!started) {
      started = true;
      console.log(`Server ready on port ${port}`);
      startDataSimulation();
    }
  });

  srv.once('error', (err: any) => {
    if (err.code === 'EADDRINUSE' && maxAttempts > 0 && !started) {
      console.log(`Port ${port} in use, trying ${port + 1}...`);
      srv.removeAllListeners();
      srv.close();
      setTimeout(() => start(port + 1, maxAttempts - 1), 200);
    } else if (!started) {
      console.error('Failed to start server:', err);
      process.exit(1);
    }
  });
}

start(PORT);

process.on('SIGTERM', () => {
  for (const client of clients) {
    client.close();
  }
  wss.close();
  server.close(() => {
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  for (const client of clients) {
    client.close();
  }
  wss.close();
  server.close(() => {
    process.exit(0);
  });
});

export default server;

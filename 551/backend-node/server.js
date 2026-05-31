const WebSocket = require('ws');
const express = require('express');
const http = require('http');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = process.env.PORT || 3001;
const PYTHON_WS_URL = 'ws://localhost:8765';

let pythonClient = null;
const frontendClients = new Set();

function connectToPython() {
  console.log('Connecting to Python speech recognition service...');
  
  const ws = new WebSocket(PYTHON_WS_URL);
  
  ws.on('open', () => {
    console.log('Connected to Python speech recognition service');
    pythonClient = ws;
    
    ws.send(JSON.stringify({ action: 'get_config' }));
  });
  
  ws.on('message', (data) => {
    const message = data.toString();
    console.log('Received from Python:', message.substring(0, 100));
    
    frontendClients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    });
  });
  
  ws.on('error', (error) => {
    console.error('Python WebSocket error:', error.message);
  });
  
  ws.on('close', () => {
    console.log('Disconnected from Python service, retrying in 3 seconds...');
    pythonClient = null;
    setTimeout(connectToPython, 3000);
  });
}

wss.on('connection', (ws, req) => {
  const ip = req.socket.remoteAddress;
  console.log(`New frontend client connected: ${ip}`);
  frontendClients.add(ws);
  
  if (pythonClient && pythonClient.readyState === WebSocket.OPEN) {
    pythonClient.send(JSON.stringify({ action: 'get_config' }));
  }
  
  ws.on('message', (data) => {
    const message = data.toString();
    console.log('Received from frontend:', message);
    
    if (pythonClient && pythonClient.readyState === WebSocket.OPEN) {
      pythonClient.send(message);
    } else {
      ws.send(JSON.stringify({
        type: 'error',
        message: 'Speech recognition service not available'
      }));
    }
  });
  
  ws.on('close', () => {
    console.log(`Frontend client disconnected: ${ip}`);
    frontendClients.delete(ws);
  });
  
  ws.on('error', (error) => {
    console.error('Frontend WebSocket error:', error);
    frontendClients.delete(ws);
  });
});

app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    pythonConnected: pythonClient && pythonClient.readyState === WebSocket.OPEN,
    frontendClients: frontendClients.size
  });
});

app.get('/api/config', (req, res) => {
  if (pythonClient && pythonClient.readyState === WebSocket.OPEN) {
    res.json({ status: 'connected' });
  } else {
    res.json({ status: 'disconnected' });
  }
});

server.listen(PORT, () => {
  console.log(`Node.js server running on port ${PORT}`);
  console.log(`WebSocket server: ws://localhost:${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/api/health`);
  connectToPython();
});

process.on('SIGINT', () => {
  console.log('\nShutting down server...');
  if (pythonClient) {
    pythonClient.close();
  }
  wss.close(() => {
    server.close(() => {
      console.log('Server shutdown complete');
      process.exit(0);
    });
  });
});

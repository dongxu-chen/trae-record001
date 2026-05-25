import { createServer } from 'http';
import app from './app.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { wsService } from './websocket/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dataDir = path.join(__dirname, '../../data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const PORT = process.env.PORT || 3001;

const server = createServer(app);

wsService.init(server);

server.listen(PORT, () => {
  console.log(`🚀 服务器运行在端口 ${PORT}`);
  console.log(`📊 API 地址: http://localhost:${PORT}/api`);
  console.log(`🔌 WebSocket: ws://localhost:${PORT}/ws`);
});

const http = require('http');
const fs = require('fs');
const path = require('path');

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.wav': 'audio/wav',
  '.mp3': 'audio/mpeg',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.eot': 'font/eot',
  '.otf': 'font/otf'
};

const server = http.createServer((req, res) => {
  let filePath = '.' + req.url;
  
  if (filePath === './') {
    filePath = './index.html';
  }

  const extname = String(path.extname(filePath)).toLowerCase();
  const contentType = MIME_TYPES[extname] || 'application/octet-stream';

  fs.readFile(filePath, (error, content) => {
    if (error) {
      if (error.code === 'ENOENT') {
        res.writeHead(404, { 'Content-Type': 'text/html' });
        res.end('<h1>404 Not Found</h1>', 'utf-8');
      } else {
        res.writeHead(500);
        res.end('Server Error: ' + error.code + ' ..\n');
      }
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

function findAvailablePort(startPort, callback) {
  const attemptListen = (port) => {
    server.once('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        attemptListen(port + 1);
      } else {
        callback(err, null);
      }
    });
    
    server.once('listening', () => {
      callback(null, port);
    });
    
    server.listen(port);
  };
  
  attemptListen(startPort);
}

const START_PORT = 8000;

findAvailablePort(START_PORT, (err, port) => {
  if (err) {
    console.error('无法启动服务器:', err);
    process.exit(1);
  }
  
  console.log('WebVR 拳击训练应用服务器已启动');
  console.log('本地访问: http://localhost:' + port + '/');
  console.log('请在支持WebXR的浏览器中打开此地址');
  console.log('推荐使用Chrome、Firefox或Edge浏览器');
});

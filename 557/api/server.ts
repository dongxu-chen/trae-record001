/**
 * local server entry file, for local development
 */
import app from './app.js';

console.log('[Server] Starting...');
console.log('[Server] App loaded:', typeof app);

/**
 * start server with port
 */
const PORT = process.env.PORT || 3001;

const server = app.listen(PORT, () => {
  console.log(`[Server] Ready on port ${PORT}`);
  console.log(`[Server] Health check: http://localhost:${PORT}/api/health`);
  console.log(`[Server] Validate API: POST http://localhost:${PORT}/api/function/validate`);
  console.log(`[Server] Derivative API: POST http://localhost:${PORT}/api/function/derivative`);
  console.log(`[Server] Evaluate API: POST http://localhost:${PORT}/api/function/evaluate`);
  console.log(`[Server] Export API: POST http://localhost:${PORT}/api/export/png`);
});

server.on('error', (err) => {
  console.error('[Server] Error:', err);
  process.exit(1);
});

/**
 * close server
 */
process.on('SIGTERM', () => {
  console.log('[Server] SIGTERM signal received');
  server.close(() => {
    console.log('[Server] Closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('[Server] SIGINT signal received');
  server.close(() => {
    console.log('[Server] Closed');
    process.exit(0);
  });
});

process.on('uncaughtException', (err) => {
  console.error('[Server] Uncaught exception:', err);
  process.exit(1);
});

export default app;
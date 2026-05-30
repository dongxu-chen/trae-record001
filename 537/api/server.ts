/**
 * local server entry file, for local development
 */
import app from './app.js';

/**
 * start server with port
 */
function startServer(port: number): void {
  const server = app.listen(port, () => {
    console.log(`Server ready on port ${port}`);
  }).on('error', (err: any) => {
    if (err.code === 'EADDRINUSE') {
      console.log(`Port ${port} in use, trying ${port + 1}...`);
      startServer(port + 1);
    } else {
      console.error('Server error:', err);
      process.exit(1);
    }
  });

  process.on('SIGTERM', () => {
    console.log('SIGTERM signal received');
    server.close(() => {
      console.log('Server closed');
      process.exit(0);
    });
  });

  process.on('SIGINT', () => {
    console.log('SIGINT signal received');
    server.close(() => {
      console.log('Server closed');
      process.exit(0);
    });
  });
}

const PORT = parseInt(process.env.PORT || '3005', 10);
startServer(PORT);

export default app;
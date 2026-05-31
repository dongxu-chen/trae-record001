/**
 * local server entry file, for local development
 */
import app from './app.js';

const PORT = 3001;

const server = app.listen(PORT, () => {
  console.log(`=================================`);
  console.log(`Server is running`);
  console.log(`Port: ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`API Base URL: http://localhost:${PORT}/api`);
  console.log(`Health Check: http://localhost:${PORT}/api/health`);
  console.log(`=================================`);
});

process.on('SIGTERM', () => {
  console.log('SIGTERM signal received, shutting down gracefully');
  server.close(() => {
    console.log('Server closed successfully');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT signal received, shutting down gracefully');
  server.close(() => {
    console.log('Server closed successfully');
    process.exit(0);
  });
});

export default app;
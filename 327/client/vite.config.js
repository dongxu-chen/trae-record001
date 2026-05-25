import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      events: 'events',
      stream: 'stream-browserify',
      util: 'util',
      buffer: 'buffer',
      process: 'process/browser'
    }
  },
  optimizeDeps: {
    esbuildOptions: {
      define: {
        global: 'globalThis',
        process: JSON.stringify({ env: {} })
      }
    }
  },
  server: {
    port: 5173,
    https: false,
    proxy: {
      '/socket.io': {
        target: 'http://localhost:3001',
        ws: true,
        changeOrigin: true
      }
    }
  },
  build: {
    commonjsOptions: {
      transformMixedEsModules: true
    }
  }
});

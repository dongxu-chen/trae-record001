import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 3001,
    open: true
  },
  build: {
    lib: {
      entry: 'src/sdk/index.js',
      name: 'DashboardSDK',
      formats: ['es', 'umd'],
      fileName: (format) => `dashboard-sdk.${format}.js`
    },
    rollupOptions: {
      external: [],
      output: {
        globals: {},
        assetFileNames: 'dashboard-sdk.[ext]'
      }
    }
  }
});

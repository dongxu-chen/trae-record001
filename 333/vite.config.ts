import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    electron([
      {
        entry: 'electron/main/index.ts',
        onstart(options) {
          options.startup()
        },
        vite: {
          build: {
            sourcemap: true,
            outDir: 'dist-electron/main',
            rollupOptions: {
              external: ['electron', 'electron-store', 'ws', 'simple-peer', 'better-sqlite3', '@journeyapps/sqlcipher', 'bcryptjs', 'pbkdf2', 'uuid']
            }
          }
        }
      },
      {
        entry: 'electron/preload/index.ts',
        vite: {
          build: {
            sourcemap: true,
            outDir: 'dist-electron/preload'
          }
        }
      }
    ]),
    renderer()
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@shared': path.resolve(__dirname, 'shared')
    }
  },
  server: {
    port: 33445,
    strictPort: true
  }
})

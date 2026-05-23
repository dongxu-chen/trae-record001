import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import monacoEditorPlugin from 'vite-plugin-monaco-editor'

export default defineConfig({
  plugins: [
    vue(),
    monacoEditorPlugin({
      languageWorkers: ['editorWorkerService', 'typescript', 'json', 'html', 'css'],
      customWorkers: [
        {
          label: 'python',
          entry: 'monaco-editor/esm/vs/basic-languages/python/python.js'
        }
      ]
    })
  ],
  server: {
    port: 3000
  },
  optimizeDeps: {
    include: ['monaco-editor']
  }
})

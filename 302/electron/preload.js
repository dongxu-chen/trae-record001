import { ipcRenderer } from 'electron'

window.electronAPI = {
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),
  onNavigate: (callback) => {
    ipcRenderer.on('navigate', (event, path) => callback(path))
  },
  onNewTranslation: (callback) => {
    ipcRenderer.on('new-translation', callback)
  },
  onImportDocument: (callback) => {
    ipcRenderer.on('import-document', callback)
  },
}

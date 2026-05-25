/// <reference types="vite/client" />

interface Window {
  electronAPI?: {
    getAppVersion: () => Promise<string>
    getPlatform: () => Promise<string>
    onNavigate: (callback: (path: string) => void) => void
    onNewTranslation: (callback: () => void) => void
    onImportDocument: (callback: () => void) => void
  }
}

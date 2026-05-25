/// <reference types="vite/client" />

interface Window {
  electronAPI: import('../electron/preload').ElectronAPI
}

declare module '*.svg' {
  const content: string
  export default content
}

declare module '*.png' {
  const content: string
  export default content
}

declare module '*.jpg' {
  const content: string
  export default content
}

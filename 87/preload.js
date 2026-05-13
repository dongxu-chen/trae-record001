const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  redis: {
    connect: (config) => ipcRenderer.invoke('redis:connect', config),
    disconnect: (connectionId) => ipcRenderer.invoke('redis:disconnect', connectionId),
    keys: (connectionId, pattern) => ipcRenderer.invoke('redis:keys', { connectionId, pattern }),
    scanBatch: (connectionId, cursor, pattern, count) =>
      ipcRenderer.invoke('redis:scanBatch', { connectionId, cursor, pattern, count }),
    type: (connectionId, key) => ipcRenderer.invoke('redis:type', { connectionId, key }),
    get: (connectionId, key) => ipcRenderer.invoke('redis:get', { connectionId, key }),
    hgetall: (connectionId, key) => ipcRenderer.invoke('redis:hgetall', { connectionId, key }),
    lrange: (connectionId, key) => ipcRenderer.invoke('redis:lrange', { connectionId, key }),
    smembers: (connectionId, key) => ipcRenderer.invoke('redis:smembers', { connectionId, key }),
    zrange: (connectionId, key) => ipcRenderer.invoke('redis:zrange', { connectionId, key }),
    del: (connectionId, key) => ipcRenderer.invoke('redis:del', { connectionId, key }),
    execute: (connectionId, command, args) =>
      ipcRenderer.invoke('redis:execute', { connectionId, command, args }),
    slowlog: (connectionId, limit) =>
      ipcRenderer.invoke('redis:slowlog', { connectionId, limit }),
    slowlogLen: (connectionId) =>
      ipcRenderer.invoke('redis:slowlogLen', { connectionId }),
    slowlogReset: (connectionId) =>
      ipcRenderer.invoke('redis:slowlogReset', { connectionId }),
    export: (connectionId, pattern) =>
      ipcRenderer.invoke('redis:export', { connectionId, pattern }),
    import: (connectionId, data) =>
      ipcRenderer.invoke('redis:import', { connectionId, data }),
    configGet: (connectionId, parameter) =>
      ipcRenderer.invoke('redis:configGet', { connectionId, parameter })
  }
})

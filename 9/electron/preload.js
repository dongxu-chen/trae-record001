const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getSnippets: () => ipcRenderer.invoke('snippets:get'),
  saveSnippets: (snippets) => ipcRenderer.invoke('snippets:save', snippets),
  onSnippetsChanged: (callback) => {
    ipcRenderer.on('snippets:changed', (event, snippets) => callback(snippets));
    return () => ipcRenderer.removeListener('snippets:changed', callback);
  },

  getSettings: () => ipcRenderer.invoke('settings:get'),
  saveSettings: (settings) => ipcRenderer.invoke('settings:save', settings),

  uploadToGist: () => ipcRenderer.invoke('sync:upload'),
  downloadFromGist: () => ipcRenderer.invoke('sync:download'),

  onSyncStatus: (callback) => {
    ipcRenderer.on('sync:status', (event, status) => callback(status));
    return () => ipcRenderer.removeListener('sync:status', callback);
  },

  onOpenGistSettings: (callback) => {
    ipcRenderer.on('settings:open-gist', () => callback());
    return () => ipcRenderer.removeListener('settings:open-gist', callback);
  }
});

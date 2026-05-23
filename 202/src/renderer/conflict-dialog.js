const { ipcRenderer } = require('electron');
const fs = require('fs');
const path = require('path');

let conflictData = null;

const elements = {
  conflictFilePath: document.getElementById('conflictFilePath'),
  localCard: document.getElementById('localCard'),
  cloudCard: document.getElementById('cloudCard'),
  localTime: document.getElementById('localTime'),
  cloudTime: document.getElementById('cloudTime'),
  localSize: document.getElementById('localSize'),
  cloudSize: document.getElementById('cloudSize'),
  localChecksum: document.getElementById('localChecksum'),
  cloudChecksum: document.getElementById('cloudChecksum'),
  localPreview: document.getElementById('localPreview'),
  cloudPreview: document.getElementById('cloudPreview'),
  diffSection: document.getElementById('diffSection'),
  diffContent: document.getElementById('diffContent'),
  keepLocalBtn: document.getElementById('keepLocalBtn'),
  keepCloudBtn: document.getElementById('keepCloudBtn'),
  keepBothBtn: document.getElementById('keepBothBtn'),
  cancelBtn: document.getElementById('cancelBtn')
};

function init() {
  conflictData = window.conflictData;
  
  if (!conflictData) {
    conflictData = {
      id: 'demo-conflict-1',
      filePath: 'documents/report.docx',
      localFullPath: 'C:/Sync/documents/report.docx',
      localMtime: Date.now() - 3600000,
      cloudMtime: Date.now() - 7200000,
      localSize: 102400,
      cloudSize: 98304,
      localChecksum: 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2',
      cloudChecksum: 'c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4',
      type: 'both-modified'
    };
  }
  
  displayConflictData();
  bindEvents();
}

function displayConflictData() {
  elements.conflictFilePath.textContent = conflictData.filePath;
  elements.localTime.textContent = formatTime(conflictData.localMtime);
  elements.cloudTime.textContent = formatTime(conflictData.cloudMtime);
  elements.localSize.textContent = formatSize(conflictData.localSize);
  elements.cloudSize.textContent = formatSize(conflictData.cloudSize);
  elements.localChecksum.textContent = conflictData.localChecksum.substring(0, 16) + '...';
  elements.cloudChecksum.textContent = conflictData.cloudChecksum.substring(0, 16) + '...';
  
  generateFilePreview(conflictData.localFullPath, 'local');
}

function generateFilePreview(filePath, type) {
  if (!filePath) return;
  
  const previewElement = type === 'local' ? elements.localPreview : elements.cloudPreview;
  const ext = path.extname(filePath).toLowerCase();
  
  const imageExts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'];
  const textExts = ['.txt', '.md', '.json', '.js', '.html', '.css', '.py', '.java', '.c', '.cpp', '.h'];
  
  if (imageExts.includes(ext)) {
    previewElement.innerHTML = `<img src="file://${filePath}" style="max-width: 100%; max-height: 160px; object-fit: contain;">`;
  } else if (textExts.includes(ext)) {
    try {
      const content = fs.readFileSync(filePath, 'utf8').substring(0, 500);
      previewElement.innerHTML = `
        <pre style="font-size: 10px; text-align: left; padding: 8px; overflow: hidden; white-space: pre-wrap; word-break: break-all; color: #374151;">
${escapeHtml(content)}${content.length >= 500 ? '...' : ''}
        </pre>
      `;
    } catch (error) {
      console.error('Failed to read file:', error);
    }
  }
}

function bindEvents() {
  elements.localCard.addEventListener('click', () => selectVersion('local'));
  elements.cloudCard.addEventListener('click', () => selectVersion('cloud'));
  
  elements.keepLocalBtn.addEventListener('click', () => resolveConflict('keep-local'));
  elements.keepCloudBtn.addEventListener('click', () => resolveConflict('keep-cloud'));
  elements.keepBothBtn.addEventListener('click', () => resolveConflict('keep-both'));
  elements.cancelBtn.addEventListener('click', () => resolveConflict('cancel'));
}

function selectVersion(version) {
  elements.localCard.classList.toggle('selected', version === 'local');
  elements.cloudCard.classList.toggle('selected', version === 'cloud');
}

async function resolveConflict(resolution) {
  try {
    if (resolution !== 'cancel') {
      await ipcRenderer.invoke('resolve-conflict', conflictData.id, resolution);
    }
    
    ipcRenderer.send('conflict-resolved', {
      conflictId: conflictData.id,
      resolution
    });
    
    window.close();
  } catch (error) {
    console.error('Failed to resolve conflict:', error);
    alert('解决冲突失败: ' + error.message);
  }
}

function formatSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleDateString('zh-CN') + ' ' + 
         date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

ipcRenderer.on('set-conflict-data', (event, data) => {
  conflictData = data;
  displayConflictData();
});

init();

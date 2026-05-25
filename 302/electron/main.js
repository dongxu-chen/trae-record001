import { app, BrowserWindow, Menu, ipcMain } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

let mainWindow = null

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      webSecurity: true,
    },
    icon: path.join(__dirname, '../assets/icon.png'),
    title: '多语言翻译工具',
  })

  const startUrl = process.env.ELECTRON_START_URL || 
    `file://${path.join(__dirname, '../dist/index.html')}`

  mainWindow.loadURL(startUrl)

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function createMenu() {
  const template = [
    {
      label: '文件',
      submenu: [
        {
          label: '新建翻译',
          accelerator: 'Ctrl+N',
          click: () => {
            mainWindow?.webContents.send('new-translation')
          },
        },
        { type: 'separator' },
        {
          label: '导入文档',
          accelerator: 'Ctrl+O',
          click: () => {
            mainWindow?.webContents.send('import-document')
          },
        },
        { type: 'separator' },
        {
          label: '退出',
          accelerator: 'Ctrl+Q',
          click: () => app.quit(),
        },
      ],
    },
    {
      label: '编辑',
      submenu: [
        { role: 'undo', label: '撤销' },
        { role: 'redo', label: '重做' },
        { type: 'separator' },
        { role: 'cut', label: '剪切' },
        { role: 'copy', label: '复制' },
        { role: 'paste', label: '粘贴' },
        { role: 'selectAll', label: '全选' },
      ],
    },
    {
      label: '查看',
      submenu: [
        { role: 'reload', label: '刷新' },
        { role: 'forceReload', label: '强制刷新' },
        { role: 'toggleDevTools', label: '开发者工具' },
        { type: 'separator' },
        { role: 'resetZoom', label: '重置缩放' },
        { role: 'zoomIn', label: '放大' },
        { role: 'zoomOut', label: '缩小' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: '全屏' },
      ],
    },
    {
      label: '工具',
      submenu: [
        {
          label: '文本翻译',
          accelerator: 'Ctrl+1',
          click: () => {
            mainWindow?.webContents.send('navigate', '/')
          },
        },
        {
          label: '文档翻译',
          accelerator: 'Ctrl+2',
          click: () => {
            mainWindow?.webContents.send('navigate', '/document')
          },
        },
        {
          label: '术语库',
          accelerator: 'Ctrl+3',
          click: () => {
            mainWindow?.webContents.send('navigate', '/terms')
          },
        },
        {
          label: '翻译记忆',
          accelerator: 'Ctrl+4',
          click: () => {
            mainWindow?.webContents.send('navigate', '/memory')
          },
        },
        {
          label: '网页翻译',
          accelerator: 'Ctrl+5',
          click: () => {
            mainWindow?.webContents.send('navigate', '/plugin')
          },
        },
        { type: 'separator' },
        {
          label: '设置',
          accelerator: 'Ctrl+,',
          click: () => {
            mainWindow?.webContents.send('navigate', '/settings')
          },
        },
      ],
    },
    {
      label: '帮助',
      submenu: [
        {
          label: '关于',
          click: () => {
            mainWindow?.webContents.send('navigate', '/settings')
          },
        },
      ],
    },
  ]

  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
}

app.whenReady().then(() => {
  createWindow()
  createMenu()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

ipcMain.handle('get-app-version', () => {
  return app.getVersion()
})

ipcMain.handle('get-platform', () => {
  return process.platform
})

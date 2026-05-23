import { useState } from 'react'
import { importPlaylist, exportPlaylist, parseNeteasePlaylist, parseQQMusicPlaylist } from '../utils/playlistManager'

export default function PlaylistManager({ playlist, onImport, onExport }) {
  const [showModal, setShowModal] = useState(false)
  const [activeTab, setActiveTab] = useState('import')
  const [importStatus, setImportStatus] = useState(null)
  const [playlistUrl, setPlaylistUrl] = useState('')
  const [parsedPlaylist, setParsedPlaylist] = useState(null)
  const [playlistName, setPlaylistName] = useState('我的歌单')

  const handleFileImport = async (e) => {
    const files = Array.from(e.target.files)
    if (files.length === 0) return

    setImportStatus('loading')
    
    try {
      const results = []
      for (const file of files) {
        const data = await importPlaylist(file)
        results.push(data)
      }
      
      setImportStatus('success')
      setTimeout(() => setImportStatus(null), 2000)
      
      if (onImport) {
        onImport(results)
      }
    } catch (err) {
      setImportStatus('error')
      setTimeout(() => setImportStatus(null), 2000)
    }
    
    e.target.value = ''
  }

  const handleUrlImport = async () => {
    if (!playlistUrl.trim()) return
    
    setImportStatus('loading')
    
    try {
      const response = await fetch(playlistUrl, {
        mode: 'no-cors',
        credentials: 'omit'
      })
      
      setImportStatus('error')
      setTimeout(() => setImportStatus(null), 3000)
    } catch (err) {
      setImportStatus('error')
      setTimeout(() => setImportStatus(null), 3000)
    }
  }

  const handleHtmlImport = (e) => {
    const file = e.target.files[0]
    if (!file) return

    setImportStatus('loading')
    
    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const html = event.target.result
        let data = parseNeteasePlaylist(html)
        
        if (data.songs.length === 0) {
          data = parseQQMusicPlaylist(html)
        }
        
        if (data.songs.length > 0) {
          setParsedPlaylist(data)
          setPlaylistName(data.name)
          setImportStatus('success')
        } else {
          setImportStatus('error')
        }
      } catch (err) {
        setImportStatus('error')
      }
      setTimeout(() => setImportStatus(null), 2000)
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const handleExport = () => {
    exportPlaylist(playlist, playlistName)
  }

  return (
    <>
      <button className="manager-btn" onClick={() => setShowModal(true)}>
        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
          <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
        </svg>
        歌单管理
      </button>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>歌单管理</h3>
              <button className="close-btn" onClick={() => setShowModal(false)}>
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
              </button>
            </div>

            <div className="modal-tabs">
              <button 
                className={`tab-btn ${activeTab === 'import' ? 'active' : ''}`}
                onClick={() => setActiveTab('import')}
              >
                导入歌单
              </button>
              <button 
                className={`tab-btn ${activeTab === 'export' ? 'active' : ''}`}
                onClick={() => setActiveTab('export')}
              >
                导出歌单
              </button>
            </div>

            <div className="modal-body">
              {activeTab === 'import' ? (
                <div className="import-section">
                  <div className="import-option">
                    <h4>📄 从JSON文件导入</h4>
                    <p className="hint">支持本播放器导出的歌单文件</p>
                    <label className="upload-label">
                      选择文件
                      <input
                        type="file"
                        accept=".json"
                        multiple
                        onChange={handleFileImport}
                      />
                    </label>
                  </div>

                  <div className="import-option">
                    <h4>🎵 从网易云/QQ音乐导入</h4>
                    <p className="hint">1. 打开歌单页面，按Ctrl+S保存网页<br/>2. 选择保存的HTML文件</p>
                    <label className="upload-label">
                      选择HTML文件
                      <input
                        type="file"
                        accept=".html,.htm"
                        onChange={handleHtmlImport}
                      />
                    </label>
                  </div>

                  {parsedPlaylist && (
                    <div className="parsed-result">
                      <h5>✅ 已解析: {parsedPlaylist.name}</h5>
                      <p>共 {parsedPlaylist.songs.length} 首歌曲</p>
                      <small>注意：需要手动上传对应音乐文件</small>
                    </div>
                  )}

                  {importStatus && (
                    <div className={`import-status ${importStatus}`}>
                      {importStatus === 'loading' ? '处理中...' : 
                       importStatus === 'success' ? '✓ 成功!' : '✗ 失败'}
                    </div>
                  )}
                </div>
              ) : (
                <div className="export-section">
                  <div className="export-option">
                    <h4>💾 导出当前歌单</h4>
                    <p className="hint">当前歌单共 {playlist.length} 首歌曲</p>
                    <div className="export-input">
                      <label>歌单名称:</label>
                      <input
                        type="text"
                        value={playlistName}
                        onChange={(e) => setPlaylistName(e.target.value)}
                        placeholder="输入歌单名称"
                      />
                    </div>
                    <button 
                      className="export-btn"
                      onClick={handleExport}
                      disabled={playlist.length === 0}
                    >
                      导出歌单
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

import { formatTime } from '../utils/audioUtils'

export default function Playlist({ 
  playlist, 
  currentIndex, 
  onSelectSong, 
  onDeleteSong,
  onUpload 
}) {
  return (
    <div className="playlist-panel">
      <label className="upload-btn">
        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
          <path d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z"/>
        </svg>
        上传音乐
        <input
          type="file"
          accept="audio/*,.lrc"
          multiple
          onChange={onUpload}
        />
      </label>

      <div className="playlist-title">
        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
          <path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/>
        </svg>
        播放列表
        <span>({playlist.length} 首)</span>
      </div>

      {playlist.length === 0 ? (
        <div className="empty-playlist">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
          </svg>
          <p>播放列表为空</p>
          <p style={{ fontSize: '0.8rem', marginTop: '10px' }}>
            点击上方按钮上传音乐文件
          </p>
        </div>
      ) : (
        playlist.map((song, index) => (
          <div
            key={song.id}
            className={`playlist-item ${index === currentIndex ? 'active' : ''}`}
            onClick={() => onSelectSong(index)}
          >
            <span className="index">{String(index + 1).padStart(2, '0')}</span>
            <div className="info">
              <div className="name">{song.name}</div>
              <div className="duration">{formatTime(song.duration)}</div>
            </div>
            <button
              className="delete-btn"
              onClick={(e) => {
                e.stopPropagation()
                onDeleteSong(index)
              }}
            >
              ✕
            </button>
          </div>
        ))
      )}
    </div>
  )
}

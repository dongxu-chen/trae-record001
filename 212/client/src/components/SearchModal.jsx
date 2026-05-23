import { useState, useEffect } from 'react';

function SearchModal({ room, onClose, onSearch }) {
  const [keyword, setKeyword] = useState('');
  const [sender, setSender] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const handleSearch = async () => {
    if (!keyword && !sender && !startTime && !endTime) return;
    
    setLoading(true);
    setSearched(true);
    
    const params = {};
    if (keyword) params.keyword = keyword;
    if (sender) params.sender = sender;
    if (startTime) params.startTime = new Date(startTime).getTime();
    if (endTime) params.endTime = new Date(endTime).getTime() + 86400000;

    const data = await onSearch(params);
    setResults(data);
    setLoading(false);
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN');
  };

  const renderMessageContent = (msg) => {
    if (msg.type === 'voice') {
      return `[语音消息] ${Math.floor(msg.duration / 60)}:${(msg.duration % 60).toString().padStart(2, '0')}`;
    }
    return msg.content;
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal search-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>搜索消息 - {room.name}</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        
        <div className="search-form">
          <div className="search-row">
            <div className="search-field">
              <label>关键字</label>
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="输入关键字..."
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
          </div>
          
          <div className="search-row">
            <div className="search-field">
              <label>发送人</label>
              <input
                type="text"
                value={sender}
                onChange={(e) => setSender(e.target.value)}
                placeholder="输入用户名..."
              />
            </div>
          </div>
          
          <div className="search-row">
            <div className="search-field">
              <label>开始时间</label>
              <input
                type="date"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
              />
            </div>
            <div className="search-field">
              <label>结束时间</label>
              <input
                type="date"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
              />
            </div>
          </div>
          
          <button className="search-submit-btn" onClick={handleSearch} disabled={loading}>
            {loading ? '搜索中...' : '搜索'}
          </button>
        </div>
        
        <div className="search-results">
          {searched && (
            <>
              {loading ? (
                <div className="search-loading">搜索中...</div>
              ) : results.length > 0 ? (
                <>
                  <div className="results-count">找到 {results.length} 条消息</div>
                  <div className="results-list">
                    {results.map((msg) => (
                      <div key={msg.id} className="result-item">
                        <div className="result-header">
                          <span className="result-sender">{msg.username}</span>
                          <span className="result-time">{formatTime(msg.timestamp)}</span>
                        </div>
                        <div className="result-content">{renderMessageContent(msg)}</div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="no-results">没有找到匹配的消息</div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default SearchModal;
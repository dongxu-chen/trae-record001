import { useState } from 'react';

export function Sidebar({
  pageThumbnails,
  currentPage,
  onPageSelect,
  onUpload,
  onSearch,
  searchResults,
  currentSearchIndex,
  onNextSearch,
  onPrevSearch,
  onDeletePage,
  onMovePage,
  hasPDF
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [draggedIndex, setDraggedIndex] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      onUpload(file);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    onSearch(searchQuery);
  };

  const handleDragStart = (index) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedIndex !== index) {
      onMovePage(draggedIndex, index);
      setDraggedIndex(index);
    }
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  return (
    <div className="sidebar">
      <div className="sidebar-section">
        <h3>上传PDF</h3>
        <label className="upload-area">
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <div className="upload-icon">📄</div>
          <p>点击或拖拽上传PDF文件</p>
        </label>
      </div>

      {hasPDF && (
        <>
          <div className="sidebar-section">
            <h3>内容搜索</h3>
            <form onSubmit={handleSearch} className="search-box">
              <input
                type="text"
                placeholder="搜索关键词..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <button type="submit" className="btn btn-primary">
                🔍
              </button>
            </form>
            {searchResults.length > 0 && (
              <>
                <div className="search-info">
                  找到 {searchResults.length} 个匹配结果
                </div>
                <div className="search-nav">
                  <button 
                    onClick={onPrevSearch}
                    disabled={currentSearchIndex <= 0}
                  >
                    ◀ 上一个
                  </button>
                  <button 
                    onClick={onNextSearch}
                    disabled={currentSearchIndex >= searchResults.length - 1}
                  >
                    下一个 ▶
                  </button>
                </div>
              </>
            )}
          </div>

          <div className="sidebar-section" style={{ paddingBottom: 0, borderBottom: 'none' }}>
            <h3>页面管理 ({pageThumbnails.length})</h3>
          </div>
          
          <div className="page-thumbnails">
            {pageThumbnails.map((thumbnail, index) => (
              <div
                key={index}
                className={`page-thumbnail ${currentPage === index + 1 ? 'active' : ''}`}
                onClick={() => onPageSelect(index + 1)}
                draggable
                onDragStart={() => handleDragStart(index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragEnd={handleDragEnd}
              >
                {thumbnail ? (
                  <img 
                    src={thumbnail} 
                    alt={`Page ${index + 1}`}
                    style={{ width: '100%', borderRadius: '2px' }}
                  />
                ) : (
                  <div 
                    style={{ 
                      width: '100%', 
                      height: '150px', 
                      background: '#eee',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '2px',
                      color: '#999'
                    }}
                  >
                    空白页
                  </div>
                )}
                <div className="page-number">第 {index + 1} 页</div>
                <div className="page-actions">
                  {index > 0 && (
                    <button
                      className="btn btn-secondary"
                      onClick={(e) => {
                        e.stopPropagation();
                        onMovePage(index, index - 1);
                      }}
                    >
                      ↑
                    </button>
                  )}
                  {index < pageThumbnails.length - 1 && (
                    <button
                      className="btn btn-secondary"
                      onClick={(e) => {
                        e.stopPropagation();
                        onMovePage(index, index + 1);
                      }}
                    >
                      ↓
                    </button>
                  )}
                  {pageThumbnails.length > 1 && (
                    <button
                      className="btn btn-secondary"
                      style={{ background: '#e74c3c', color: 'white', border: 'none' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeletePage(index + 1);
                      }}
                    >
                      🗑️
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

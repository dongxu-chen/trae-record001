import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Search, Scissors, Loader2, Save, RotateCcw } from 'lucide-react';
import axios from 'axios';
import Timeline from '../components/Timeline';

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
}

function Edit() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [note, setNote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selection, setSelection] = useState(null);
  const [isTrimming, setIsTrimming] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    loadNote();
  }, [id]);

  const loadNote = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/notes/${id}`);
      const noteData = response.data;
      setNote(noteData);

      if (noteData.duration > 0) {
        setSelection({ start: 0, end: noteData.duration });
      } else if (noteData.transcriptionData?.duration > 0) {
        setSelection({ start: 0, end: noteData.transcriptionData.duration });
      }
    } catch (err) {
      setError('加载笔记失败: ' + (err.response?.data?.error || err.message));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = useCallback(async () => {
    if (!searchKeyword.trim() || !id) {
      setSearchResults([]);
      return;
    }

    try {
      setIsSearching(true);
      const response = await axios.get(`/api/notes/${id}/search`, {
        params: { keyword: searchKeyword },
      });
      setSearchResults(response.data.segments || []);
    } catch (err) {
      console.error('搜索失败:', err);
    } finally {
      setIsSearching(false);
    }
  }, [searchKeyword, id]);

  useEffect(() => {
    const debounce = setTimeout(handleSearch, 300);
    return () => clearTimeout(debounce);
  }, [handleSearch]);

  const handleSegmentClick = (segment) => {
    if (selection && note?.duration) {
      setSelection({
        start: Math.max(0, segment.start - 0.5),
        end: Math.min(note.duration || (note.transcriptionData?.duration || 0), segment.end + 0.5),
      });
    }
    setCurrentTime(segment.start);
  };

  const handleSeek = (time) => {
    setCurrentTime(time);
    setIsPlaying(false);
  };

  const handlePlayPause = (playing) => {
    setIsPlaying(playing);
  };

  const handleTrim = async () => {
    if (!selection || !note) return;

    const duration = note.duration || note.transcriptionData?.duration || 0;
    if (selection.start >= selection.end) {
      setError('选区无效，请选择有效的时间范围');
      return;
    }

    if (selection.start <= 0 && selection.end >= duration) {
      setError('请选择需要裁剪的区域（不是全部）');
      return;
    }

    try {
      setIsTrimming(true);
      setError('');

      const response = await axios.post(`/api/notes/${id}/trim`, {
        startTime: selection.start,
        endTime: selection.end,
      });

      navigate(`/edit/${response.data._id}`);
    } catch (err) {
      setError('裁剪失败: ' + (err.response?.data?.error || err.message));
      console.error(err);
    } finally {
      setIsTrimming(false);
    }
  };

  const resetSelection = () => {
    if (note) {
      const duration = note.duration || note.transcriptionData?.duration || 0;
      setSelection({ start: 0, end: duration });
    }
  };

  const getDuration = () => {
    if (!note) return 0;
    return note.duration || note.transcriptionData?.duration || 0;
  };

  const getSegments = () => {
    if (!note) return [];
    return note.transcriptionData?.segments || [];
  };

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <Loader2 size={32} style={{ animation: 'spin 1s linear infinite' }} />
        <span style={{ marginLeft: '12px', color: 'white' }}>加载中...</span>
        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (error && !note) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        color: 'white',
      }}>
        <p style={{ marginBottom: '20px' }}>{error}</p>
        <Link to="/" style={{
          padding: '10px 24px',
          background: 'white',
          color: '#667eea',
          borderRadius: '8px',
          textDecoration: 'none',
          fontWeight: 600,
        }}>
          返回首页
        </Link>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      padding: '20px',
    }}>
      <div style={{
        maxWidth: '1000px',
        margin: '0 auto',
        background: 'rgba(255, 255, 255, 0.95)',
        borderRadius: '20px',
        padding: '32px',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '24px',
        }}>
          <Link
            to="/"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: '#6b7280',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: 500,
            }}
          >
            <ArrowLeft size={18} />
            返回录音
          </Link>

          <h1 style={{
            fontSize: '24px',
            fontWeight: 700,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            编辑笔记
          </h1>

          <div style={{ width: '80px' }} />
        </div>

        {error && (
          <div style={{
            background: '#fee2e2',
            color: '#991b1b',
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '20px',
            textAlign: 'center',
          }}>
            {error}
          </div>
        )}

        <div style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '24px',
        }}>
          <div style={{
            flex: 1,
            position: 'relative',
          }}>
            <Search size={18} style={{
              position: 'absolute',
              left: '14px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#9ca3af',
            }} />
            <input
              type="text"
              placeholder="搜索文字内容..."
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px 12px 44px',
                fontSize: '14px',
                border: '2px solid #e5e7eb',
                borderRadius: '12px',
                outline: 'none',
                transition: 'border-color 0.2s',
              }}
              onFocus={(e) => e.target.style.borderColor = '#667eea'}
              onBlur={(e) => e.target.style.borderColor = '#e5e7eb'}
            />
            {isSearching && (
              <Loader2 size={18} style={{
                position: 'absolute',
                right: '14px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#9ca3af',
                animation: 'spin 1s linear infinite',
              }} />
            )}
          </div>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <Timeline
            segments={searchKeyword && searchResults.length > 0 ? searchResults : getSegments()}
            duration={getDuration()}
            audioUrl={note?.audioUrl}
            onSeek={handleSeek}
            onSegmentClick={handleSegmentClick}
            currentTime={currentTime}
            isPlaying={isPlaying}
            onPlayPause={handlePlayPause}
            highlightKeyword={searchKeyword}
            selection={selection}
            onSelectionChange={setSelection}
            editable={true}
          />
        </div>

        {selection && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px',
            background: '#f0f9ff',
            borderRadius: '12px',
            marginBottom: '24px',
            border: '1px solid #bae6fd',
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}>
                <label style={{
                  fontSize: '12px',
                  color: '#64748b',
                  fontWeight: 500,
                }}>
                  开始
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max={getDuration()}
                  value={selection.start.toFixed(1)}
                  onChange={(e) => setSelection({
                    ...selection,
                    start: Math.max(0, Math.min(parseFloat(e.target.value) || 0, selection.end - 0.5)),
                  })}
                  style={{
                    width: '80px',
                    padding: '8px 12px',
                    fontSize: '14px',
                    border: '1px solid #cbd5e1',
                    borderRadius: '8px',
                    outline: 'none',
                  }}
                />
                <span style={{ color: '#64748b', fontSize: '12px' }}>秒</span>
              </div>

              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}>
                <label style={{
                  fontSize: '12px',
                  color: '#64748b',
                  fontWeight: 500,
                }}>
                  结束
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max={getDuration()}
                  value={selection.end.toFixed(1)}
                  onChange={(e) => setSelection({
                    ...selection,
                    end: Math.min(getDuration(), Math.max(parseFloat(e.target.value) || 0, selection.start + 0.5)),
                  })}
                  style={{
                    width: '80px',
                    padding: '8px 12px',
                    fontSize: '14px',
                    border: '1px solid #cbd5e1',
                    borderRadius: '8px',
                    outline: 'none',
                  }}
                />
                <span style={{ color: '#64748b', fontSize: '12px' }}>秒</span>
              </div>

              <div style={{
                fontSize: '12px',
                color: '#0ea5e9',
                background: '#e0f2fe',
                padding: '6px 12px',
                borderRadius: '6px',
              }}>
                时长: {(selection.end - selection.start).toFixed(1)}秒
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={resetSelection}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '10px 16px',
                  fontSize: '14px',
                  fontWeight: 500,
                  color: '#6b7280',
                  background: '#f3f4f6',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  transition: 'background 0.2s',
                }}
              >
                <RotateCcw size={16} />
                重置
              </button>

              <button
                onClick={handleTrim}
                disabled={isTrimming}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '10px 20px',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: 'white',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: isTrimming ? 'not-allowed' : 'pointer',
                  opacity: isTrimming ? 0.7 : 1,
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  boxShadow: '0 4px 14px rgba(102, 126, 234, 0.3)',
                }}
              >
                {isTrimming ? (
                  <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                ) : (
                  <Scissors size={16} />
                )}
                {isTrimming ? '裁剪中...' : '裁剪并另存为'}
              </button>
            </div>
          </div>
        )}

        {searchKeyword && searchResults.length === 0 && !isSearching && (
          <div style={{
            textAlign: 'center',
            padding: '40px',
            color: '#9ca3af',
          }}>
            未找到包含 "{searchKeyword}" 的内容
          </div>
        )}

        {note && !getSegments()?.length && (
          <div style={{
            textAlign: 'center',
            padding: '40px',
            background: '#fefce8',
            borderRadius: '12px',
            border: '1px solid #fef08a',
          }}>
            <p style={{ color: '#92400e', marginBottom: '8px' }}>
              该笔记没有时间戳数据
            </p>
            <p style={{ color: '#a16207', fontSize: '14px' }}>
              时间戳功能需要配置 OpenAI API Key 才能使用 Whisper 转写
            </p>
          </div>
        )}

        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </div>
  );
}

export default Edit;
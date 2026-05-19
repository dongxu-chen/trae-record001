import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

function RecordingsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { userId, userName } = location.state || {};
  
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRecording, setSelectedRecording] = useState(null);
  const [showPlayer, setShowPlayer] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterExam, setFilterExam] = useState('');
  const [exams, setExams] = useState([]);
  
  const videoRef = useRef(null);

  const fetchRecordings = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:3001/api/janus/recordings');
      const data = await response.json();
      setRecordings(data.recordings || []);
      setLoading(false);
    } catch (error) {
      console.error('获取录制列表失败:', error);
      setLoading(false);
    }
  }, []);

  const fetchExams = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:3001/api/exams');
      const data = await response.json();
      setExams(data.exams || []);
    } catch (error) {
      console.error('获取考试列表失败:', error);
    }
  }, []);

  useEffect(() => {
    fetchRecordings();
    fetchExams();
  }, [fetchRecordings, fetchExams]);

  const playRecording = (recording) => {
    setSelectedRecording(recording);
    setShowPlayer(true);
  };

  const closePlayer = () => {
    setShowPlayer(false);
    setSelectedRecording(null);
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.src = '';
    }
  };

  const deleteRecording = async (recordingId) => {
    if (!window.confirm('确定要删除这个录制文件吗？')) {
      return;
    }
    
    try {
      await fetch(`http://localhost:3001/api/janus/recordings/${recordingId}`, {
        method: 'DELETE'
      });
      fetchRecordings();
    } catch (error) {
      console.error('删除录制失败:', error);
    }
  };

  const downloadRecording = (recording) => {
    const link = document.createElement('a');
    link.href = `http://localhost:3001/api/janus/recordings/${recording.id}/download`;
    link.download = `${recording.filename}.webm`;
    link.click();
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const filteredRecordings = recordings.filter(rec => {
    const matchSearch = !searchTerm || 
      rec.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rec.userName?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rec.userId?.toString().includes(searchTerm);
    const matchExam = !filterExam || rec.examId === filterExam;
    return matchSearch && matchExam;
  });

  const getStreamTypeLabel = (type) => {
    switch (type) {
      case 'camera': return '摄像头';
      case 'screen': return '屏幕共享';
      default: return type;
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8f9fa', padding: '20px' }}>
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '20px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ margin: '0 0 5px 0', color: '#2c3e50' }}>考试录制管理</h2>
            <p style={{ margin: 0, color: '#666' }}>
              共 {recordings.length} 个录制文件
            </p>
          </div>
          <button
            onClick={() => navigate('/')}
            style={{
              padding: '8px 16px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            返回首页
          </button>
        </div>
      </div>

      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '20px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="搜索文件名或考生..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              flex: 1,
              padding: '10px 15px',
              border: '1px solid #ddd',
              borderRadius: '6px',
              fontSize: '14px'
            }}
          />
          <select
            value={filterExam}
            onChange={(e) => setFilterExam(e.target.value)}
            style={{
              padding: '10px 15px',
              border: '1px solid #ddd',
              borderRadius: '6px',
              fontSize: '14px',
              minWidth: '200px'
            }}
          >
            <option value="">所有考试</option>
            {exams.map(exam => (
              <option key={exam.examId} value={exam.examId}>
                {exam.title || exam.examId}
              </option>
            ))}
          </select>
          <button
            onClick={fetchRecordings}
            style={{
              padding: '10px 20px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            刷新
          </button>
        </div>
      </div>

      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '20px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#6c757d' }}>
            <div style={{ fontSize: '48px', marginBottom: '10px' }}>⏳</div>
            <p style={{ fontSize: '16px' }}>加载中...</p>
          </div>
        ) : filteredRecordings.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#6c757d' }}>
            <div style={{ fontSize: '48px', marginBottom: '10px' }}>📹</div>
            <p style={{ fontSize: '16px' }}>暂无录制文件</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa' }}>
                  <th style={{ padding: '12px 15px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>文件名</th>
                  <th style={{ padding: '12px 15px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>考试ID</th>
                  <th style={{ padding: '12px 15px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>考生ID</th>
                  <th style={{ padding: '12px 15px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>考生姓名</th>
                  <th style={{ padding: '12px 15px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>流类型</th>
                  <th style={{ padding: '12px 15px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>大小</th>
                  <th style={{ padding: '12px 15px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>时长</th>
                  <th style={{ padding: '12px 15px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>创建时间</th>
                  <th style={{ padding: '12px 15px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecordings.map((recording) => (
                  <tr key={recording.id} style={{ borderBottom: '1px solid #dee2e6' }}>
                    <td style={{ padding: '12px 15px', fontWeight: 500 }}>
                      {recording.filename}
                    </td>
                    <td style={{ padding: '12px 15px' }}>{recording.examId || '-'}</td>
                    <td style={{ padding: '12px 15px' }}>{recording.userId || '-'}</td>
                    <td style={{ padding: '12px 15px' }}>{recording.userName || '-'}</td>
                    <td style={{ padding: '12px 15px' }}>
                      <span style={{
                        padding: '3px 8px',
                        backgroundColor: recording.streamType === 'camera' ? '#d1ecf1' : '#fff3cd',
                        color: recording.streamType === 'camera' ? '#0c5460' : '#856404',
                        borderRadius: '4px',
                        fontSize: '12px'
                      }}>
                        {getStreamTypeLabel(recording.streamType)}
                      </span>
                    </td>
                    <td style={{ padding: '12px 15px' }}>{formatFileSize(recording.size)}</td>
                    <td style={{ padding: '12px 15px' }}>{formatDuration(recording.duration)}</td>
                    <td style={{ padding: '12px 15px', fontSize: '13px', color: '#666' }}>
                      {new Date(recording.createdAt).toLocaleString()}
                    </td>
                    <td style={{ padding: '12px 15px' }}>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => playRecording(recording)}
                          style={{
                            padding: '6px 12px',
                            backgroundColor: '#28a745',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            fontSize: '12px',
                            cursor: 'pointer'
                          }}
                        >
                          播放
                        </button>
                        <button
                          onClick={() => downloadRecording(recording)}
                          style={{
                            padding: '6px 12px',
                            backgroundColor: '#17a2b8',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            fontSize: '12px',
                            cursor: 'pointer'
                          }}
                        >
                          下载
                        </button>
                        <button
                          onClick={() => deleteRecording(recording.id)}
                          style={{
                            padding: '6px 12px',
                            backgroundColor: '#dc3545',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            fontSize: '12px',
                            cursor: 'pointer'
                          }}
                        >
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showPlayer && selectedRecording && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.9)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 2000
        }}>
          <div style={{
            width: '90%',
            maxWidth: '1200px'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '15px'
            }}>
              <h3 style={{ margin: 0, color: 'white' }}>
                {selectedRecording.filename}
              </h3>
              <button
                onClick={closePlayer}
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  border: 'none',
                  backgroundColor: 'rgba(255,255,255,0.2)',
                  color: 'white',
                  cursor: 'pointer',
                  fontSize: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                ×
              </button>
            </div>
            <div style={{
              backgroundColor: '#000',
              borderRadius: '8px',
              overflow: 'hidden'
            }}>
              <video
                ref={videoRef}
                controls
                autoPlay
                style={{
                  width: '100%',
                  maxHeight: '70vh',
                  backgroundColor: '#000'
                }}
              >
                <source
                  src={`http://localhost:3001/api/janus/recordings/${selectedRecording.id}/play`}
                  type="video/webm"
                />
                您的浏览器不支持视频播放
              </video>
            </div>
            <div style={{
              marginTop: '15px',
              color: '#ccc',
              fontSize: '14px',
              display: 'flex',
              justifyContent: 'space-between'
            }}>
              <div>
                <span>考生: {selectedRecording.userName || selectedRecording.userId}</span>
                <span style={{ marginLeft: '20px' }}>
                  考试ID: {selectedRecording.examId}
                </span>
              </div>
              <div>
                <span>大小: {formatFileSize(selectedRecording.size)}</span>
                <span style={{ marginLeft: '20px' }}>
                  时长: {formatDuration(selectedRecording.duration)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RecordingsPage;

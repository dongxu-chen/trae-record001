import React, { useState, useEffect, useRef, useCallback } from 'react';

function ExamineeCard({ examinee, webrtcManager, onViewStreams, isVisible }) {
  const [isLoading, setIsLoading] = useState(false);
  const [webcamStream, setWebcamStream] = useState(null);
  const [screenStream, setScreenStream] = useState(null);
  const [connectionStates, setConnectionStates] = useState({ webcam: 'disconnected', screen: 'disconnected' });
  
  const webcamRef = useRef(null);
  const screenRef = useRef(null);
  const hasRequestedStreams = useRef(false);

  const handleStreamAdded = useCallback((streamType, stream) => {
    if (streamType === 'webcam') {
      setWebcamStream(stream);
      if (webcamRef.current) {
        webcamRef.current.srcObject = stream;
      }
    } else if (streamType === 'screen') {
      setScreenStream(stream);
      if (screenRef.current) {
        screenRef.current.srcObject = stream;
      }
    }
  }, []);

  const handleConnectionStateChange = useCallback((streamType, state) => {
    setConnectionStates(prev => ({
      ...prev,
      [streamType]: state
    }));
  }, []);

  const viewStreams = useCallback(async () => {
    if (!webrtcManager || hasRequestedStreams.current) return;
    
    setIsLoading(true);
    hasRequestedStreams.current = true;

    try {
      await webrtcManager.requestStream(examinee.socketId, 'webcam');
      await webrtcManager.requestStream(examinee.socketId, 'screen');
    } catch (error) {
      console.error('请求视频流失败:', error);
    } finally {
      setIsLoading(false);
    }

    if (onViewStreams) {
      onViewStreams(examinee.socketId);
    }
  }, [webrtcManager, examinee.socketId, onViewStreams]);

  useEffect(() => {
    if (!webrtcManager) return;

    const originalOnStreamAdded = webrtcManager.onStreamAdded;
    const originalOnConnectionStateChange = webrtcManager.onConnectionStateChange;

    webrtcManager.onStreamAdded = (examineeId, streamType, stream) => {
      if (examineeId === examinee.socketId) {
        handleStreamAdded(streamType, stream);
      }
      if (originalOnStreamAdded) {
        originalOnStreamAdded(examineeId, streamType, stream);
      }
    };

    webrtcManager.onConnectionStateChange = (examineeId, streamType, state) => {
      if (examineeId === examinee.socketId) {
        handleConnectionStateChange(streamType, state);
      }
      if (originalOnConnectionStateChange) {
        originalOnConnectionStateChange(examineeId, streamType, state);
      }
    };

    return () => {
      webrtcManager.onStreamAdded = originalOnStreamAdded;
      webrtcManager.onConnectionStateChange = originalOnConnectionStateChange;
    };
  }, [webrtcManager, examinee.socketId, handleStreamAdded, handleConnectionStateChange]);

  useEffect(() => {
    if (isVisible && !hasRequestedStreams.current && webcamRef.current && !webcamStream) {
    }
  }, [isVisible, webcamStream]);

  useEffect(() => {
    return () => {
      if (webrtcManager && hasRequestedStreams.current) {
        webrtcManager.stopAllStreams(examinee.socketId);
        hasRequestedStreams.current = false;
      }
    };
  }, [webrtcManager, examinee.socketId]);

  const getStatusColor = (state) => {
    const colorMap = {
      'connected': '#28a745',
      'connecting': '#ffc107',
      'disconnected': '#dc3545',
      'failed': '#dc3545',
      'new': '#6c757d',
      'checking': '#ffc107',
      'completed': '#28a745'
    };
    return colorMap[state] || '#6c757d';
  };

  return (
    <div className="examinee-card" style={{
      background: 'white',
      borderRadius: '12px',
      padding: '16px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      height: '100%',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '12px'
      }}>
        <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>
          {examinee.name}
        </h4>
        <div style={{ fontSize: '0.8rem', color: '#666' }}>
          {examinee.userId}
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '10px',
        marginBottom: '12px',
        flex: 1
      }}>
        <div style={{
          backgroundColor: '#1a1a2e',
          borderRadius: '8px',
          overflow: 'hidden',
          aspectRatio: '4/3',
          position: 'relative'
        }}>
          {webcamStream ? (
            <video
              ref={webcamRef}
              autoPlay
              muted
              playsInline
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          ) : (
            <div style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#888',
              fontSize: '0.8rem'
            }}>
              <span style={{ fontSize: '1.5rem', marginBottom: '4px' }}>📷</span>
              <span>摄像头</span>
            </div>
          )}
          <div style={{
            position: 'absolute',
            bottom: '4px',
            left: '4px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: getStatusColor(connectionStates.webcam)
            }} />
          </div>
        </div>

        <div style={{
          backgroundColor: '#1a1a2e',
          borderRadius: '8px',
          overflow: 'hidden',
          aspectRatio: '4/3',
          position: 'relative'
        }}>
          {screenStream ? (
            <video
              ref={screenRef}
              autoPlay
              muted
              playsInline
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          ) : (
            <div style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#888',
              fontSize: '0.8rem'
            }}>
              <span style={{ fontSize: '1.5rem', marginBottom: '4px' }}>🖥️</span>
              <span>屏幕</span>
            </div>
          )}
          <div style={{
            position: 'absolute',
            bottom: '4px',
            left: '4px',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: getStatusColor(connectionStates.screen)
            }} />
          </div>
        </div>
      </div>

      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <div style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            backgroundColor: '#28a745'
          }} />
          <span style={{ fontSize: '0.85rem', color: '#666' }}>在线</span>
        </div>
        <button
          onClick={viewStreams}
          disabled={isLoading || hasRequestedStreams.current}
          style={{
            padding: '6px 16px',
            backgroundColor: hasRequestedStreams.current ? '#6c757d' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: hasRequestedStreams.current ? 'default' : 'pointer',
            fontSize: '0.85rem',
            fontWeight: 500
          }}
        >
          {isLoading ? '连接中...' : hasRequestedStreams.current ? '已连接' : '查看画面'}
        </button>
      </div>
    </div>
  );
}

export default ExamineeCard;

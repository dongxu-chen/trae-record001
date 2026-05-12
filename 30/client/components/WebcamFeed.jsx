import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Card, Button, message, Space } from 'antd';
import { VideoCameraOutlined, VideoCameraAddOutlined, ReloadOutlined } from '@ant-design/icons';

const API_BASE = 'http://localhost:5000/api/proctor';

export default function WebcamFeed({ 
  examId, 
  studentName, 
  snapshotInterval = 10000, 
  onCameraStatusChange 
}) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const snapshotTimerRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState(null);
  const [lastSnapshotTime, setLastSnapshotTime] = useState(null);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: false
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      streamRef.current = stream;
      setCameraActive(true);
      setCameraError(null);
      onCameraStatusChange?.(true);
      message.success('摄像头已启动');

      startSnapshotLoop();

      sendEvent('camera_started', '摄像头启动成功');
    } catch (err) {
      console.error('摄像头启动失败:', err);
      setCameraError(err.message);
      setCameraActive(false);
      onCameraStatusChange?.(false);
      message.error('无法启动摄像头：' + err.message);
      sendEvent('camera_error', err.message);
    }
  }, [examId, studentName, onCameraStatusChange]);

  const stopCamera = useCallback(() => {
    if (snapshotTimerRef.current) {
      clearInterval(snapshotTimerRef.current);
      snapshotTimerRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraActive(false);
    onCameraStatusChange?.(false);
  }, [onCameraStatusChange]);

  const captureSnapshot = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || !cameraActive) {
      return;
    }

    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;

      if (video.videoWidth === 0 || video.videoHeight === 0) {
        return;
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const imageData = canvas.toDataURL('image/jpeg', 0.7);
      const timestamp = new Date().toISOString();

      await uploadSnapshot(imageData, timestamp);
      setLastSnapshotTime(timestamp);

    } catch (err) {
      console.error('快照捕获失败:', err);
      sendEvent('snapshot_error', err.message);
    }
  }, [cameraActive, examId, studentName]);

  const uploadSnapshot = async (imageData, timestamp) => {
    try {
      const response = await fetch(`${API_BASE}/snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          examId,
          studentName,
          imageData,
          timestamp
        })
      });

      if (!response.ok) {
        throw new Error(`上传失败: ${response.status}`);
      }
    } catch (err) {
      console.error('快照上传失败:', err);
    }
  };

  const sendEvent = async (eventType, eventData) => {
    try {
      await fetch(`${API_BASE}/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          examId,
          studentName,
          eventType,
          eventData,
          timestamp: new Date().toISOString()
        })
      });
    } catch (err) {
      console.error('事件发送失败:', err);
    }
  };

  const startSnapshotLoop = () => {
    if (snapshotTimerRef.current) {
      clearInterval(snapshotTimerRef.current);
    }

    captureSnapshot();
    snapshotTimerRef.current = setInterval(captureSnapshot, snapshotInterval);
  };

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  const forceSnapshot = () => {
    if (!cameraActive) {
      message.warning('请先启动摄像头');
      return;
    }
    captureSnapshot();
    message.info('正在捕获快照...');
  };

  return (
    <div>
      <canvas ref={canvasRef} style={{ display: 'none' }} />
      
      <Card
        size="small"
        title={
          <Space>
            <VideoCameraOutlined />
            <span>监考摄像头</span>
            {cameraActive && (
              <span style={{ color: '#52c41a' }}>●</span>
            )}
          </Space>
        }
        extra={
          <Space size="small">
            {!cameraActive ? (
              <Button
                type="primary"
                icon={<VideoCameraAddOutlined />}
                onClick={startCamera}
                size="small"
              >
                启动
              </Button>
            ) : (
              <>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={forceSnapshot}
                  size="small"
                >
                  快照
                </Button>
                <Button
                  danger
                  onClick={stopCamera}
                  size="small"
                >
                  关闭
                </Button>
              </>
            )}
          </Space>
        }
      >
        <div style={{ position: 'relative', backgroundColor: '#000', minHeight: 240 }}>
          <video
            ref={videoRef}
            style={{ 
              width: '100%', 
              display: cameraActive ? 'block' : 'none',
              transform: 'scaleX(-1)'
            }}
            playsInline
            muted
          />
          
          {!cameraActive && (
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: 240,
              color: '#888'
            }}>
              <div style={{ textAlign: 'center' }}>
                <VideoCameraAddOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <div>点击"启动"按钮开启监考摄像头</div>
              </div>
            </div>
          )}

          {cameraActive && lastSnapshotTime && (
            <div style={{
              position: 'absolute',
              bottom: 8,
              right: 8,
              backgroundColor: 'rgba(0,0,0,0.7)',
              padding: '4px 8px',
              borderRadius: 4,
              color: '#fff',
              fontSize: 12
            }}>
              上次快照: {new Date(lastSnapshotTime).toLocaleTimeString()}
            </div>
          )}
        </div>

        {cameraError && (
          <div style={{ color: '#ff4d4f', marginTop: 8, fontSize: 12 }}>
            错误: {cameraError}
          </div>
        )}
      </Card>
    </div>
  );
}

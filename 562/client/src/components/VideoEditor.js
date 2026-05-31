import React, { useState, useRef, useEffect, useCallback } from 'react';
import axios from 'axios';
import './VideoEditor.css';

function VideoEditor() {
  const [video, setVideo] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [totalFrames, setTotalFrames] = useState(0);
  const [processedFrames, setProcessedFrames] = useState([]);
  const [algorithm, setAlgorithm] = useState('edge-guided');
  const [radius, setRadius] = useState(3);
  const [detectText, setDetectText] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackFrame, setPlaybackFrame] = useState(0);
  const [sessionId] = useState(() => 'video_' + Date.now());

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const playbackCanvasRef = useRef(null);
  const animationRef = useRef(null);

  const FPS = 10;

  const handleVideoUpload = (e) => {
    const file = e.target.files[0];
    if (!file || !file.type.startsWith('video/')) return;
    
    setVideo(file);
    if (videoUrl) URL.revokeObjectURL(videoUrl);
    setVideoUrl(URL.createObjectURL(file));
    setProcessedFrames([]);
    setCurrentFrame(0);
    setProgress(0);
  };

  const extractFrame = useCallback((videoElement, time) => {
    const canvas = canvasRef.current;
    if (!canvas || !videoElement) return null;

    const maxWidth = 640;
    const maxHeight = 480;
    let width = videoElement.videoWidth;
    let height = videoElement.videoHeight;

    if (width > maxWidth) {
      height = (maxWidth / width) * height;
      width = maxWidth;
    }
    if (height > maxHeight) {
      width = (maxHeight / height) * width;
      height = maxHeight;
    }

    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoElement, 0, 0, width, height);
    return canvas.toDataURL('image/png');
  }, []);

  const processVideo = async () => {
    if (!video || isProcessing) return;

    const videoEl = document.createElement('video');
    videoEl.src = videoUrl;
    videoEl.muted = true;

    await new Promise((resolve) => {
      videoEl.onloadedmetadata = resolve;
    });

    const duration = videoEl.duration;
    const frameCount = Math.floor(duration * FPS);
    setTotalFrames(frameCount);
    setIsProcessing(true);
    setProgress(0);
    setProcessedFrames([]);

    const results = [];

    for (let i = 0; i < frameCount; i++) {
      const time = i / FPS;
      videoEl.currentTime = time;

      await new Promise((resolve) => {
        videoEl.onseeked = resolve;
      });

      const frameData = extractFrame(videoEl, time);
      if (!frameData) continue;

      setCurrentFrame(i);

      try {
        const response = await axios.post('/api/video-frame', {
          image: frameData,
          frameIndex: i,
          sessionId,
          algorithm,
          radius,
          detectText,
          options: {
            guideEdges: true,
            preserveTexture: true
          }
        });

        results.push({
          index: i,
          result: response.data.result,
          time
        });
      } catch (error) {
        console.error(`处理第 ${i} 帧时出错:`, error);
        results.push({
          index: i,
          result: frameData,
          time,
          error: true
        });
      }

      setProcessedFrames([...results]);
      setProgress(Math.round(((i + 1) / frameCount) * 100));
    }

    setIsProcessing(false);
  };

  useEffect(() => {
    if (isPlaying && processedFrames.length > 0) {
      let frameIndex = playbackFrame;
      
      const animate = () => {
        if (frameIndex >= processedFrames.length) {
          frameIndex = 0;
        }
        
        setPlaybackFrame(frameIndex);
        const canvas = playbackCanvasRef.current;
        if (canvas && processedFrames[frameIndex]) {
          const img = new Image();
          img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
          };
          img.src = processedFrames[frameIndex].result;
        }
        
        frameIndex++;
        animationRef.current = requestAnimationFrame(animate);
      };

      const interval = setInterval(() => {
        animationRef.current = requestAnimationFrame(animate);
      }, 1000 / FPS);

      return () => {
        clearInterval(interval);
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
      };
    }
  }, [isPlaying, processedFrames, playbackFrame]);

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
  };

  const downloadFrames = () => {
    processedFrames.forEach((frame, index) => {
      setTimeout(() => {
        const link = document.createElement('a');
        link.download = `frame_${String(index).padStart(4, '0')}.png`;
        link.href = frame.result;
        link.click();
      }, index * 200);
    });
  };

  const resetVideo = async () => {
    try {
      await axios.post('/api/video-reset', { sessionId });
    } catch (e) { /* ignore */ }
    setVideo(null);
    if (videoUrl) URL.revokeObjectURL(videoUrl);
    setVideoUrl(null);
    setProcessedFrames([]);
    setCurrentFrame(0);
    setProgress(0);
    setIsPlaying(false);
  };

  return (
    <div className="video-editor">
      <div className="video-container">
        <div className="video-upload-area">
          {!video ? (
            <div className="video-drop-zone" onClick={() => document.getElementById('video-input').click()}>
              <input
                id="video-input"
                type="file"
                accept="video/*"
                onChange={handleVideoUpload}
                style={{ display: 'none' }}
              />
              <div className="drop-content">
                <div className="upload-icon">🎬</div>
                <p>点击上传视频文件</p>
                <p className="hint">支持 MP4、WebM、MOV 格式</p>
              </div>
            </div>
          ) : (
            <div className="video-preview">
              {processedFrames.length === 0 ? (
                <video ref={videoRef} src={videoUrl} controls className="video-player" />
              ) : (
                <div className="result-preview">
                  <canvas ref={playbackCanvasRef} className="result-canvas" />
                  <div className="playback-controls">
                    <button className="btn-play" onClick={togglePlayback}>
                      {isPlaying ? '⏸ 暂停' : '▶ 播放'}
                    </button>
                    <span className="frame-info">
                      帧 {playbackFrame + 1} / {processedFrames.length}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <canvas ref={canvasRef} style={{ display: 'none' }} />

        {isProcessing && (
          <div className="processing-overlay">
            <div className="processing-info">
              <h3>处理视频中...</h3>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${progress}%` }} />
                <span className="progress-text">{progress}%</span>
              </div>
              <p>当前帧: {currentFrame + 1} / {totalFrames}</p>
            </div>
          </div>
        )}
      </div>

      <div className="video-tools">
        <div className="tool-group">
          <h3>🎬 视频设置</h3>
          <div className="tool-item">
            <label>修复算法:</label>
            <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}>
              <option value="telea">Telea (快速)</option>
              <option value="edge-guided">边缘引导 (推荐)</option>
              <option value="texture-preserving">纹理保持</option>
              <option value="advanced">高级修复</option>
            </select>
          </div>
          <div className="tool-item">
            <label>修复半径: {radius}</label>
            <input
              type="range"
              min="1"
              max="8"
              value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
            />
          </div>
          <div className="tool-item checkbox-item">
            <label>
              <input
                type="checkbox"
                checked={detectText}
                onChange={(e) => setDetectText(e.target.checked)}
              />
              自动检测文字
            </label>
          </div>
        </div>

        <div className="tool-group">
          <h3>📋 操作</h3>
          <div className="button-group">
            <button
              className="btn btn-primary"
              onClick={processVideo}
              disabled={!video || isProcessing}
            >
              {isProcessing ? '处理中...' : '🚀 开始处理'}
            </button>
            {processedFrames.length > 0 && (
              <button className="btn btn-success" onClick={downloadFrames}>
                💾 下载帧序列
              </button>
            )}
            <button className="btn btn-danger" onClick={resetVideo}>
              🔄 重新上传
            </button>
          </div>
        </div>

        <div className="tool-group">
          <h3>💡 视频处理说明</h3>
          <ul className="tips-list">
            <li>视频将按 {FPS}fps 提取帧进行处理</li>
            <li>开启自动检测可自动框选文字区域</li>
            <li>帧间一致性保持修复结果平滑过渡</li>
            <li>处理完成后可预览和下载帧序列</li>
          </ul>
        </div>

        {processedFrames.length > 0 && (
          <div className="tool-group">
            <h3>📊 处理结果</h3>
            <p>已完成: {processedFrames.length} 帧</p>
            <p>成功: {processedFrames.filter(f => !f.error).length} 帧</p>
            <div className="frame-strip">
              {processedFrames.filter((_, i) => i % 5 === 0).map((frame) => (
                <div key={frame.index} className={`frame-thumb ${frame.error ? 'error' : ''}`}>
                  <img src={frame.result} alt={`Frame ${frame.index}`} />
                  <span>{frame.index}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default VideoEditor;

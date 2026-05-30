import React, { useRef, useEffect, useState, useCallback } from 'react';

function TimelineEditor({ videoInfo, analysisResult, selectedHighlights, onHighlightToggle, onTimeSeek, currentTime }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [scrollOffset, setScrollOffset] = useState(0);
  const [dragging, setDragging] = useState(false);

  const totalDuration = videoInfo?.duration || analysisResult?.video_info?.duration || 100;
  const pixelsPerSecond = 10 * zoom;

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    const width = Math.max(container.clientWidth, totalDuration * pixelsPerSecond);
    const height = 120;

    canvas.width = width * window.devicePixelRatio;
    canvas.height = height * window.devicePixelRatio;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, width, height);

    const interval = zoom >= 2 ? 5 : zoom >= 1 ? 10 : 30;
    for (let t = 0; t <= totalDuration; t += interval) {
      const x = t * pixelsPerSecond - scrollOffset;
      if (x < -50 || x > width + 50) continue;

      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();

      ctx.fillStyle = '#64748b';
      ctx.font = '10px Inter, sans-serif';
      ctx.fillText(formatTime(t), x + 4, height - 8);
    }

    for (let t = 0; t <= totalDuration; t += interval / 5) {
      const x = t * pixelsPerSecond - scrollOffset;
      if (x < -10 || x > width + 10) continue;
      ctx.strokeStyle = '#0f172a';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(x, height - 25);
      ctx.lineTo(x, height - 15);
      ctx.stroke();
    }

    if (analysisResult?.scenes) {
      const sceneColors = ['#1e3a5f', '#1e5f3a', '#5f1e3a', '#3a1e5f', '#5f3a1e'];
      analysisResult.scenes.forEach((scene, idx) => {
        const x = scene.start_time * pixelsPerSecond - scrollOffset;
        const w = (scene.end_time - scene.start_time) * pixelsPerSecond;
        if (x + w < 0 || x > width) return;

        ctx.fillStyle = sceneColors[idx % sceneColors.length] + '40';
        ctx.fillRect(x, 5, w, 30);

        ctx.strokeStyle = sceneColors[idx % sceneColors.length] + '80';
        ctx.lineWidth = 1;
        ctx.strokeRect(x, 5, w, 30);

        if (w > 40) {
          ctx.fillStyle = '#94a3b8';
          ctx.font = '9px Inter, sans-serif';
          const label = `S${scene.scene_idx + 1} ${scene.type || ''}`;
          ctx.fillText(label, x + 4, 24);
        }
      });
    }

    const typeColors = {
      motion: '#f97316',
      color: '#8b5cf6',
      brightness: '#eab308',
      audio_peak: '#06b6d4',
      laughter: '#22c55e',
      multi: '#ec4899'
    };

    (analysisResult?.highlights || []).forEach(h => {
      const isSelected = selectedHighlights.some(sh => sh.id === h.id);
      const x = h.start_time * pixelsPerSecond - scrollOffset;
      const w = (h.end_time - h.start_time) * pixelsPerSecond;

      if (x + w < 0 || x > width) return;

      const color = typeColors[h.type] || '#6366f1';

      ctx.fillStyle = isSelected ? color + '60' : color + '20';
      ctx.fillRect(x, 40, w, 50);

      ctx.strokeStyle = isSelected ? color : color + '60';
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.strokeRect(x, 40, w, 50);

      if (w > 30) {
        ctx.fillStyle = isSelected ? '#fff' : '#94a3b8';
        ctx.font = `${isSelected ? 'bold ' : ''}9px Inter, sans-serif`;
        ctx.fillText(`#${h.id}`, x + 3, 55);
        if (w > 60) {
          ctx.fillText(h.type, x + 3, 68);
        }
        if (w > 90) {
          ctx.fillText(`${h.duration.toFixed(1)}s`, x + 3, 80);
        }
      }

      if (h.confidence) {
        const barW = Math.min(w - 4, 40);
        if (barW > 5) {
          ctx.fillStyle = '#1e293b';
          ctx.fillRect(x + 2, 84, barW, 4);
          ctx.fillStyle = color;
          ctx.fillRect(x + 2, 84, barW * h.confidence, 4);
        }
      }
    });

    const cursorX = currentTime * pixelsPerSecond - scrollOffset;
    if (cursorX >= 0 && cursorX <= width) {
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cursorX, 0);
      ctx.lineTo(cursorX, height);
      ctx.stroke();

      ctx.fillStyle = '#ef4444';
      ctx.beginPath();
      ctx.moveTo(cursorX - 5, 0);
      ctx.lineTo(cursorX + 5, 0);
      ctx.lineTo(cursorX, 8);
      ctx.fill();
    }
  }, [analysisResult, selectedHighlights, currentTime, zoom, scrollOffset, totalDuration, pixelsPerSecond]);

  const handleCanvasClick = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const time = (x + scrollOffset) / pixelsPerSecond;
    onTimeSeek(Math.max(0, Math.min(totalDuration, time)));
  };

  const handleWheel = (e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      setZoom(prev => Math.max(0.5, Math.min(5, prev * delta)));
    } else {
      setScrollOffset(prev => Math.max(0, prev + e.deltaX));
    }
  };

  const handleHighlightClick = (h) => {
    const startX = h.start_time * pixelsPerSecond - scrollOffset;
    const endX = h.end_time * pixelsPerSecond - scrollOffset;
    const rect = canvasRef.current.getBoundingClientRect();
    if (startX >= 0 && startX <= rect.width) {
      onHighlightToggle(h);
    }
  };

  return (
    <div className="timeline-editor">
      <div className="timeline-toolbar">
        <div className="timeline-zoom">
          <button className="btn-icon" onClick={() => setZoom(z => Math.max(0.5, z * 0.8))}>
            <span className="material-icons-round">zoom_out</span>
          </button>
          <span className="zoom-label">{Math.round(zoom * 100)}%</span>
          <button className="btn-icon" onClick={() => setZoom(z => Math.min(5, z * 1.2))}>
            <span className="material-icons-round">zoom_in</span>
          </button>
        </div>
        <div className="timeline-info">
          <span className="material-icons-round">schedule</span>
          {formatTime(currentTime)} / {formatTime(totalDuration)}
        </div>
      </div>
      <div
        className="timeline-canvas-container"
        ref={containerRef}
        onWheel={handleWheel}
      >
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          className="timeline-canvas"
        />
      </div>
      <div className="timeline-legend">
        {[
          { type: 'motion', label: '运动', color: '#f97316' },
          { type: 'color', label: '色彩', color: '#8b5cf6' },
          { type: 'brightness', label: '亮度', color: '#eab308' },
          { type: 'audio_peak', label: '音频', color: '#06b6d4' },
          { type: 'laughter', label: '笑声', color: '#22c55e' },
          { type: 'spectral_change', label: '频谱', color: '#e879f9' },
          { type: 'multi', label: '综合', color: '#ec4899' }
        ].map(item => (
          <span key={item.type} className="legend-item">
            <span className="legend-dot" style={{ backgroundColor: item.color }} />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export default TimelineEditor;

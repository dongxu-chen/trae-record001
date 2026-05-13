import { useRef, useEffect, useState, useCallback } from 'react';
import { Play, Pause, Volume2, VolumeX } from 'lucide-react';

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 100);
  return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
}

function Timeline({
  segments = [],
  duration = 0,
  audioUrl,
  onSeek,
  onSegmentClick,
  currentTime = 0,
  isPlaying = false,
  onPlayPause,
  highlightKeyword,
  selection,
  onSelectionChange,
  editable = true,
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const audioRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragType, setDragType] = useState(null);
  const [hoveredSegment, setHoveredSegment] = useState(null);
  const [localCurrentTime, setLocalCurrentTime] = useState(0);

  useEffect(() => {
    setLocalCurrentTime(currentTime);
  }, [currentTime]);

  const getTimeFromX = useCallback((clientX) => {
    const canvas = canvasRef.current;
    if (!canvas || duration <= 0) return 0;

    const rect = canvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const percent = Math.max(0, Math.min(1, x / rect.width));
    return percent * duration;
  }, [duration]);

  const getXFromTime = useCallback((time, width) => {
    if (duration <= 0) return 0;
    return (time / duration) * width;
  }, [duration]);

  const handleCanvasMouseDown = (e) => {
    if (!editable || duration <= 0) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const width = rect.width;

    const handleRadius = 8;
    const startX = getXFromTime(selection?.start || 0, width);
    const endX = getXFromTime(selection?.end || duration, width);

    if (Math.abs(x - startX) < handleRadius) {
      setIsDragging(true);
      setDragType('start');
    } else if (Math.abs(x - endX) < handleRadius) {
      setIsDragging(true);
      setDragType('end');
    } else if (selection && x >= startX && x <= endX) {
      setIsDragging(true);
      setDragType('move');
    } else {
      const time = getTimeFromX(e.clientX);
      onSeek?.(time);
      setLocalCurrentTime(time);
    }
  };

  const handleCanvasMouseMove = (e) => {
    if (!isDragging || !onSelectionChange || !selection) return;

    const time = getTimeFromX(e.clientX);
    const minGap = 0.5;

    if (dragType === 'start') {
      const newStart = Math.max(0, Math.min(time, selection.end - minGap));
      onSelectionChange({ ...selection, start: newStart });
    } else if (dragType === 'end') {
      const newEnd = Math.min(duration, Math.max(time, selection.start + minGap));
      onSelectionChange({ ...selection, end: newEnd });
    }
  };

  const handleCanvasMouseUp = () => {
    setIsDragging(false);
    setDragType(null);
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleCanvasMouseMove);
      window.addEventListener('mouseup', handleCanvasMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleCanvasMouseMove);
        window.removeEventListener('mouseup', handleCanvasMouseUp);
      };
    }
  }, [isDragging, dragType, selection]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const topPadding = 30;
    const bottomPadding = 10;
    const trackHeight = height - topPadding - bottomPadding;

    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;

    const tickInterval = duration > 60 ? 10 : duration > 30 ? 5 : 1;
    for (let t = 0; t <= duration; t += tickInterval) {
      const x = getXFromTime(t, width);
      ctx.beginPath();
      ctx.moveTo(x, topPadding);
      ctx.lineTo(x, topPadding + trackHeight);
      ctx.stroke();

      ctx.fillStyle = '#9ca3af';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(formatTime(t), x, topPadding - 5);
    }

    if (segments && segments.length > 0) {
      segments.forEach((segment, index) => {
        const segStartX = getXFromTime(segment.start, width);
        const segEndX = getXFromTime(segment.end, width);
        const segWidth = Math.max(2, segEndX - segStartX);

        let fillColor = '#e0e7ff';
        let strokeColor = '#818cf8';

        if (highlightKeyword && segment.text?.toLowerCase().includes(highlightKeyword.toLowerCase())) {
          fillColor = '#fef08a';
          strokeColor = '#eab308';
        }

        if (hoveredSegment === index) {
          fillColor = highlightKeyword ? '#fde047' : '#c7d2fe';
        }

        ctx.fillStyle = fillColor;
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 1;

        const barHeight = trackHeight * 0.6;
        const barTop = topPadding + (trackHeight - barHeight) / 2;

        ctx.fillRect(segStartX, barTop, segWidth, barHeight);
        ctx.strokeRect(segStartX, barTop, segWidth, barHeight);
      });
    } else {
      const barCount = Math.floor(width / 3);
      const barWidth = 2;
      const gap = 1;

      for (let i = 0; i < barCount; i++) {
        const x = i * (barWidth + gap);
        const barHeight = (Math.sin(Date.now() / 1000 + i * 0.1) + 1) * 10 + 15;
        const barTop = topPadding + (trackHeight - barHeight) / 2;

        ctx.fillStyle = '#e5e7eb';
        ctx.fillRect(x, barTop, barWidth, barHeight);
      }
    }

    if (selection) {
      const selStartX = getXFromTime(selection.start, width);
      const selEndX = getXFromTime(selection.end, width);
      const selWidth = selEndX - selStartX;

      ctx.fillStyle = 'rgba(99, 102, 241, 0.15)';
      ctx.fillRect(selStartX, topPadding, selWidth, trackHeight);

      ctx.strokeStyle = '#6366f1';
      ctx.lineWidth = 2;
      ctx.strokeRect(selStartX, topPadding, selWidth, trackHeight);

      const handleY = topPadding + trackHeight / 2;

      [selStartX, selEndX].forEach(x => {
        ctx.fillStyle = '#6366f1';
        ctx.beginPath();
        ctx.arc(x, handleY, 6, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = 'white';
        ctx.beginPath();
        ctx.arc(x, handleY, 3, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    const currentX = getXFromTime(localCurrentTime, width);
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(currentX, topPadding - 10);
    ctx.lineTo(currentX, topPadding + trackHeight + 10);
    ctx.stroke();

    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.arc(currentX, topPadding - 15, 5, 0, Math.PI * 2);
    ctx.fill();
  }, [segments, duration, localCurrentTime, selection, hoveredSegment, highlightKeyword, getXFromTime]);

  const handleSegmentClick = (segment, e) => {
    e.stopPropagation();
    onSegmentClick?.(segment);
    if (onSeek) {
      onSeek(segment.start);
      setLocalCurrentTime(segment.start);
    }
  };

  const handleAudioTimeUpdate = () => {
    if (audioRef.current) {
      setLocalCurrentTime(audioRef.current.currentTime);
    }
  };

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      onPlayPause?.(!isPlaying);
    }
  };

  useEffect(() => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.play().catch(() => {});
      } else {
        audioRef.current.pause();
      }
    }
  }, [isPlaying]);

  return (
    <div style={{ width: '100%' }}>
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onTimeUpdate={handleAudioTimeUpdate}
          onEnded={() => onPlayPause?.(false)}
          style={{ display: 'none' }}
        />
      )}

      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '12px',
        padding: '12px',
        background: '#f8fafc',
        borderRadius: '12px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={togglePlay}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              border: 'none',
              color: 'white',
              cursor: 'pointer',
              transition: 'transform 0.2s',
            }}
          >
            {isPlaying ? <Pause size={18} /> : <Play size={18} />}
          </button>
          <div style={{
            fontSize: '14px',
            fontWeight: 600,
            color: '#374151',
          }}>
            {formatTime(localCurrentTime)} / {formatTime(duration)}
          </div>
        </div>

        {selection && (
          <div style={{
            fontSize: '12px',
            color: '#6b7280',
            background: '#e0e7ff',
            padding: '6px 12px',
            borderRadius: '8px',
          }}>
            选区: {formatTime(selection.start)} - {formatTime(selection.end)}
          </div>
        )}
      </div>

      <div
        ref={containerRef}
        style={{
          position: 'relative',
          marginBottom: '16px',
        }}
      >
        <canvas
          ref={canvasRef}
          onMouseDown={handleCanvasMouseDown}
          style={{
            width: '100%',
            height: '120px',
            borderRadius: '8px',
            cursor: editable && duration > 0 ? 'pointer' : 'default',
          }}
        />
      </div>

      {segments && segments.length > 0 && (
        <div style={{
          maxHeight: '300px',
          overflowY: 'auto',
          borderRadius: '12px',
          background: '#fafafa',
          border: '1px solid #e5e7eb',
        }}>
          {segments.map((segment, index) => {
            const isHighlighted = highlightKeyword &&
              segment.text?.toLowerCase().includes(highlightKeyword.toLowerCase());

            return (
              <div
                key={segment.id || index}
                onMouseEnter={() => setHoveredSegment(index)}
                onMouseLeave={() => setHoveredSegment(null)}
                onClick={(e) => handleSegmentClick(segment, e)}
                style={{
                  display: 'flex',
                  gap: '12px',
                  padding: '12px 16px',
                  borderBottom: '1px solid #f0f0f0',
                  cursor: 'pointer',
                  background: isHighlighted ? '#fef9c3' : hoveredSegment === index ? '#f1f5f9' : 'transparent',
                  transition: 'background 0.15s',
                }}
              >
                <div style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  color: '#6366f1',
                  whiteSpace: 'nowrap',
                  minWidth: '100px',
                }}>
                  {formatTime(segment.start)} - {formatTime(segment.end)}
                </div>
                <div style={{
                  fontSize: '14px',
                  color: '#374151',
                  lineHeight: 1.5,
                  flex: 1,
                }}>
                  {segment.text}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default Timeline;
import { useCallback, useRef, useEffect } from 'react';
import useMeetingStore from '../store/useMeetingStore';
import useSocket from './useSocket';

const useRecording = () => {
  const {
    localStream,
    isRecording,
    recordingInfo,
    setIsRecording,
    setRecordingInfo
  } = useMeetingStore();

  const { socket, connected } = useSocket();

  const mediaRecorderRef = useRef(null);
  const recordingWsRef = useRef(null);
  const recordingStartTimeRef = useRef(null);
  const statsIntervalRef = useRef(null);
  const bytesSentRef = useRef(0);
  const bitrateRef = useRef(0);

  const startRecording = useCallback(async (layout = 'grid') => {
    if (isRecording || !connected || !socket) return { success: false };

    return new Promise((resolve) => {
      socket.emit('start-recording', { roomId: recordingInfo?.roomId, layout }, (result) => {
        if (result.success) {
          setRecordingInfo(result);
          setIsRecording(true);
          recordingStartTimeRef.current = Date.now();
          bytesSentRef.current = 0;
          bitrateRef.current = 0;

          _startStreamingToServer(result.wsPort, result.recordingId);
          _startStatsReporting(result.recordingId);
        }
        resolve(result);
      });
    });
  }, [isRecording, connected, socket, recordingInfo?.roomId, setRecordingInfo, setIsRecording]);

  const _startStreamingToServer = useCallback((wsPort, recordingId) => {
    if (!localStream) return;

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.hostname}:${wsPort}/stream/${recordingId}`;
      const ws = new WebSocket(wsUrl);
      recordingWsRef.current = ws;

      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        console.log('Recording WebSocket connected');
        
        const stream = localStream;
        const audioTrack = stream.getAudioTracks()[0];
        const videoTrack = stream.getVideoTracks()[0];
        
        if (!audioTrack && !videoTrack) {
          console.error('No media tracks available');
          return;
        }

        const recordingStream = new MediaStream();
        if (audioTrack) recordingStream.addTrack(audioTrack);
        if (videoTrack) recordingStream.addTrack(videoTrack);

        const mimeType = _getSupportedMimeType();
        const options = {
          mimeType,
          videoBitsPerSecond: 2_500_000,
          audioBitsPerSecond: 128_000
        };

        const recorder = new MediaRecorder(recordingStream, options);
        mediaRecorderRef.current = recorder;

        recorder.ondataavailable = (event) => {
          if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            const reader = new FileReader();
            reader.onload = () => {
              const arrayBuffer = reader.result;
              bytesSentRef.current += arrayBuffer.byteLength;
              ws.send(arrayBuffer);
            };
            reader.readAsArrayBuffer(event.data);
          }
        };

        recorder.onerror = (event) => {
          console.error('Recording error:', event.error);
        };

        recorder.start(200);
      };

      ws.onclose = () => {
        console.log('Recording WebSocket closed');
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
          mediaRecorderRef.current.stop();
        }
      };

      ws.onerror = (error) => {
        console.error('Recording WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to start streaming:', error);
    }
  }, [localStream]);

  const _getSupportedMimeType = useCallback(() => {
    const types = [
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8,opus',
      'video/webm;codecs=h264,opus',
      'video/webm'
    ];

    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }

    return 'video/webm';
  }, []);

  const _startStatsReporting = useCallback((recordingId) => {
    if (statsIntervalRef.current) {
      clearInterval(statsIntervalRef.current);
    }

    statsIntervalRef.current = setInterval(() => {
      if (mediaRecorderRef.current && socket) {
        const currentBytes = bytesSentRef.current;
        const bitrate = Math.round((currentBytes - (bitrateRef.current || 0)) * 8);
        bitrateRef.current = currentBytes;

        socket.emit('recording-stats', {
          recordingId,
          bytesSent: currentBytes,
          bitrate,
          state: mediaRecorderRef.current.state
        });
      }
    }, 1000);
  }, [socket]);

  const stopRecording = useCallback(async () => {
    if (!isRecording || !connected || !socket) return { success: false };

    return new Promise((resolve) => {
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current);
        statsIntervalRef.current = null;
      }

      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop();
        } catch (e) {
          console.error('Error stopping recorder:', e);
        }
        mediaRecorderRef.current = null;
      }

      if (recordingWsRef.current && recordingWsRef.current.readyState === WebSocket.OPEN) {
        recordingWsRef.current.close();
      }
      recordingWsRef.current = null;

      socket.emit('stop-recording', { roomId: recordingInfo?.roomId }, (result) => {
        if (result.success) {
          setIsRecording(false);
          setRecordingInfo(null);
          recordingStartTimeRef.current = null;
          bytesSentRef.current = 0;
          bitrateRef.current = 0;
        }
        resolve(result);
      });
    });
  }, [isRecording, connected, socket, recordingInfo?.roomId, setIsRecording, setRecordingInfo]);

  const getRecordingStats = useCallback(async () => {
    if (!socket || !recordingInfo) return null;

    return new Promise((resolve) => {
      socket.emit('get-recording-stats', { roomId: recordingInfo.roomId }, (result) => {
        resolve(result.success ? result.stats : null);
      });
    });
  }, [socket, recordingInfo]);

  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.pause();
      return true;
    }
    return false;
  }, []);

  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
      mediaRecorderRef.current.resume();
      return true;
    }
    return false;
  }, []);

  const downloadRecording = useCallback((filename) => {
    if (!filename) return null;
    
    const url = `http://localhost:3001/api/recordings/${filename}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    return { url, filename };
  }, []);

  const getRecordingDuration = useCallback(() => {
    if (!recordingStartTimeRef.current) return 0;
    return Date.now() - recordingStartTimeRef.current;
  }, []);

  const formatDuration = useCallback((ms) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    const secs = seconds % 60;
    const mins = minutes % 60;
    
    if (hours > 0) {
      return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }, []);

  useEffect(() => {
    if (!socket) return;

    const handleRecordingStarted = (info) => {
      setRecordingInfo(info);
      setIsRecording(true);
      recordingStartTimeRef.current = info.startedAt || Date.now();

      if (!mediaRecorderRef.current) {
        _startStreamingToServer(info.wsPort, info.recordingId);
        _startStatsReporting(info.recordingId);
      }
    };

    const handleRecordingStopped = (info) => {
      setIsRecording(false);
      setRecordingInfo(null);
      
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current);
        statsIntervalRef.current = null;
      }

      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop();
        } catch (e) {
          console.error('Error stopping recorder:', e);
        }
        mediaRecorderRef.current = null;
      }

      if (recordingWsRef.current && recordingWsRef.current.readyState === WebSocket.OPEN) {
        recordingWsRef.current.close();
      }
      recordingWsRef.current = null;
    };

    socket.on('recording-started', handleRecordingStarted);
    socket.on('recording-stopped', handleRecordingStopped);

    return () => {
      socket.off('recording-started', handleRecordingStarted);
      socket.off('recording-stopped', handleRecordingStopped);
    };
  }, [socket, setRecordingInfo, setIsRecording, _startStreamingToServer, _startStatsReporting]);

  useEffect(() => {
    return () => {
      if (statsIntervalRef.current) {
        clearInterval(statsIntervalRef.current);
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop();
        } catch (e) {
          console.error('Error stopping recorder on unmount:', e);
        }
      }
      if (recordingWsRef.current && recordingWsRef.current.readyState === WebSocket.OPEN) {
        recordingWsRef.current.close();
      }
    };
  }, []);

  return {
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    downloadRecording,
    getRecordingDuration,
    getRecordingStats,
    formatDuration,
    isRecording,
    recordingInfo
  };
};

export default useRecording;

import { useCallback, useRef, useEffect } from 'react';
import useMeetingStore from '../store/useMeetingStore';
import WebGLVirtualBackground from '../utils/WebGLVirtualBackground';
import { 
  AUDIO_CONSTRAINTS, 
  VIDEO_CONSTRAINTS, 
  SCREEN_SHARE_CONSTRAINTS,
  RESOLUTION_LEVELS 
} from '../config/webrtcConfig';

const useMedia = () => {
  const {
    localStream,
    screenStream,
    setLocalStream,
    setScreenStream,
    isMuted,
    isVideoOn,
    isScreenSharing,
    setIsMuted,
    setIsVideoOn,
    setIsScreenSharing,
    currentResolution,
    setCurrentResolution,
    virtualBackground,
    peers
  } = useMeetingStore();

  const localVideoRef = useRef(null);
  const virtualBgRef = useRef(null);
  const hiddenVideoRef = useRef(null);
  const outputCanvasRef = useRef(null);
  const originalVideoTrackRef = useRef(null);
  const processedVideoTrackRef = useRef(null);
  const audioContextRef = useRef(null);

  const initWebGLBackground = useCallback(() => {
    if (!outputCanvasRef.current) {
      outputCanvasRef.current = document.createElement('canvas');
      outputCanvasRef.current.style.display = 'none';
      document.body.appendChild(outputCanvasRef.current);
    }

    if (!hiddenVideoRef.current) {
      hiddenVideoRef.current = document.createElement('video');
      hiddenVideoRef.current.autoplay = true;
      hiddenVideoRef.current.muted = true;
      hiddenVideoRef.current.playsInline = true;
      hiddenVideoRef.current.style.display = 'none';
      document.body.appendChild(hiddenVideoRef.current);
    }

    try {
      virtualBgRef.current = new WebGLVirtualBackground(outputCanvasRef.current);
      console.log('WebGL Virtual Background initialized successfully');
      return true;
    } catch (error) {
      console.warn('WebGL not supported, falling back to CPU rendering:', error);
      return false;
    }
  }, []);

  const getUserMedia = useCallback(async (resolution = '720p') => {
    try {
      const videoConstraints = VIDEO_CONSTRAINTS[resolution] || VIDEO_CONSTRAINTS['720p'];
      
      const constraints = {
        audio: AUDIO_CONSTRAINTS,
        video: videoConstraints
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      const audioTrack = stream.getAudioTracks()[0];
      if (audioTrack) {
        const settings = audioTrack.getSettings();
        console.log('Audio settings:', {
          echoCancellation: settings.echoCancellation,
          noiseSuppression: settings.noiseSuppression,
          autoGainControl: settings.autoGainControl,
          sampleRate: settings.sampleRate
        });
      }

      const videoTrack = stream.getVideoTracks()[0];
      if (videoTrack) {
        const settings = videoTrack.getSettings();
        setCurrentResolution({ width: settings.width, height: settings.height });
        originalVideoTrackRef.current = videoTrack;
      }

      setLocalStream(stream);
      
      if (virtualBackground && virtualBackground.type !== 'none') {
        initWebGLBackground();
        applyVirtualBackground(stream);
      }

      return stream;
    } catch (error) {
      console.error('Failed to get user media:', error);
      throw error;
    }
  }, [setLocalStream, setCurrentResolution, virtualBackground, initWebGLBackground]);

  const stopScreenShare = useCallback(() => {
    if (screenStream) {
      screenStream.getTracks().forEach(track => track.stop());
      setScreenStream(null);
      setIsScreenSharing(false);
    }
  }, [screenStream, setScreenStream, setIsScreenSharing]);

  const getScreenStream = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: SCREEN_SHARE_CONSTRAINTS.video,
        audio: SCREEN_SHARE_CONSTRAINTS.audio
      });

      setScreenStream(stream);
      setIsScreenSharing(true);

      stream.getVideoTracks()[0].onended = () => {
        stopScreenShare();
      };

      return stream;
    } catch (error) {
      console.error('Failed to get screen stream:', error);
      throw error;
    }
  }, [setScreenStream, setIsScreenSharing, stopScreenShare]);

  const toggleMute = useCallback(() => {
    if (localStream) {
      const audioTrack = localStream.getAudioTracks()[0];
      if (audioTrack) {
        const newMuted = !isMuted;
        audioTrack.enabled = !newMuted;
        setIsMuted(newMuted);
        return newMuted;
      }
    }
    return isMuted;
  }, [localStream, isMuted, setIsMuted]);

  const toggleVideo = useCallback(() => {
    if (localStream) {
      const videoTrack = localStream.getVideoTracks()[0];
      if (videoTrack) {
        const newVideoOn = !isVideoOn;
        videoTrack.enabled = newVideoOn;
        setIsVideoOn(newVideoOn);
        return newVideoOn;
      }
    }
    return isVideoOn;
  }, [localStream, isVideoOn, setIsVideoOn]);

  const changeResolution = useCallback(async (resolutionName) => {
    if (!localStream) return false;

    try {
      const targetLevel = RESOLUTION_LEVELS.find(l => l.name === resolutionName);
      if (!targetLevel) return false;

      const videoTrack = localStream.getVideoTracks()[0];
      if (!videoTrack) return false;

      await videoTrack.applyConstraints({
        width: { ideal: targetLevel.width },
        height: { ideal: targetLevel.height }
      });

      const settings = videoTrack.getSettings();
      setCurrentResolution({ width: settings.width, height: settings.height });

      peers.forEach((peer, peerId) => {
        if (peer.connected && peer._pc) {
          const sender = peer._pc.getSenders().find(s => s.track === videoTrack || s.track === processedVideoTrackRef.current);
          if (sender && sender.setParameters) {
            const parameters = sender.getParameters();
            if (parameters.encodings && parameters.encodings[0]) {
              parameters.encodings[0].maxBitrate = targetLevel.bitrate * 1000;
              sender.setParameters(parameters);
            }
          }
        }
      });

      return true;
    } catch (error) {
      console.error('Failed to change resolution:', error);
      return false;
    }
  }, [localStream, peers, setCurrentResolution]);

  const switchCamera = useCallback(async () => {
    if (!localStream) return null;

    try {
      const currentVideoTrack = processedVideoTrackRef.current || localStream.getVideoTracks()[0];
      if (!currentVideoTrack) return null;

      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(d => d.kind === 'videoinput');

      if (videoDevices.length <= 1) return null;

      const originalTrack = originalVideoTrackRef.current || currentVideoTrack;
      const currentDeviceId = originalTrack.getSettings().deviceId;
      const nextDevice = videoDevices.find(d => d.deviceId !== currentDeviceId);

      if (!nextDevice) return null;

      stopVirtualBackground();

      const newStream = await navigator.mediaDevices.getUserMedia({
        video: {
          deviceId: { exact: nextDevice.deviceId },
          width: currentResolution.width,
          height: currentResolution.height
        },
        audio: false
      });

      const newVideoTrack = newStream.getVideoTracks()[0];
      
      if (processedVideoTrackRef.current) {
        processedVideoTrackRef.current.stop();
        processedVideoTrackRef.current = null;
      }
      
      if (originalVideoTrackRef.current) {
        originalVideoTrackRef.current.stop();
      }
      
      localStream.removeTrack(currentVideoTrack);
      localStream.addTrack(newVideoTrack);
      originalVideoTrackRef.current = newVideoTrack;

      peers.forEach((peer, peerId) => {
        if (peer.connected && peer._pc) {
          const sender = peer._pc.getSenders().find(s => 
            s.track && s.track.kind === 'video'
          );
          if (sender) {
            sender.replaceTrack(newVideoTrack);
          }
        }
      });

      if (virtualBackground && virtualBackground.type !== 'none') {
        initWebGLBackground();
        applyVirtualBackground(localStream);
      }

      return localStream;
    } catch (error) {
      console.error('Failed to switch camera:', error);
      return null;
    }
  }, [localStream, currentResolution, peers, virtualBackground, initWebGLBackground]);

  const setupAudioProcessing = useCallback(() => {
    if (!localStream || audioContextRef.current) return;

    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;

      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(localStream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      
      const checkAudioLevel = () => {
        if (!audioContextRef.current) return;
        
        analyser.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        
        if (average > 30) {
        }
      };

      const interval = setInterval(checkAudioLevel, 100);

      return () => {
        clearInterval(interval);
        if (audioContextRef.current) {
          audioContextRef.current.close();
          audioContextRef.current = null;
        }
      };
    } catch (error) {
      console.error('Failed to setup audio processing:', error);
    }
  }, [localStream]);

  const applyVirtualBackground = useCallback((stream) => {
    if (!virtualBackground || virtualBackground.type === 'none') {
      stopVirtualBackground();
      return;
    }

    try {
      if (!virtualBgRef.current) {
        if (!initWebGLBackground()) {
          return;
        }
      }

      if (!hiddenVideoRef.current || !outputCanvasRef.current) {
        initWebGLBackground();
      }

      const videoTrack = stream.getVideoTracks()[0];
      if (!videoTrack) return;

      hiddenVideoRef.current.srcObject = stream;
      hiddenVideoRef.current.play().catch(e => console.warn('Hidden video play failed:', e));

      virtualBgRef.current.setBackground(virtualBackground);
      virtualBgRef.current.start(hiddenVideoRef.current);

      const canvasStream = virtualBgRef.current.getCanvasStream();
      const newVideoTrack = canvasStream.getVideoTracks()[0];

      if (newVideoTrack && localStream) {
        if (processedVideoTrackRef.current) {
          localStream.removeTrack(processedVideoTrackRef.current);
          processedVideoTrackRef.current.stop();
        }

        localStream.removeTrack(videoTrack);
        localStream.addTrack(newVideoTrack);
        processedVideoTrackRef.current = newVideoTrack;

        peers.forEach((peer, peerId) => {
          if (peer.connected && peer._pc) {
            const sender = peer._pc.getSenders().find(s => 
              s.track && s.track.kind === 'video'
            );
            if (sender) {
              sender.replaceTrack(newVideoTrack);
            }
          }
        });
      }

      console.log('WebGL Virtual Background applied with GPU acceleration');
    } catch (error) {
      console.error('Failed to apply WebGL virtual background:', error);
    }
  }, [virtualBackground, localStream, peers, initWebGLBackground]);

  const stopVirtualBackground = useCallback(() => {
    if (virtualBgRef.current) {
      virtualBgRef.current.stop();
    }

    if (processedVideoTrackRef.current && localStream && originalVideoTrackRef.current) {
      try {
        localStream.removeTrack(processedVideoTrackRef.current);
        processedVideoTrackRef.current.stop();
        processedVideoTrackRef.current = null;

        if (!localStream.getVideoTracks().includes(originalVideoTrackRef.current)) {
          localStream.addTrack(originalVideoTrackRef.current);
        }

        peers.forEach((peer, peerId) => {
          if (peer.connected && peer._pc) {
            const sender = peer._pc.getSenders().find(s => 
              s.track && s.track.kind === 'video'
            );
            if (sender && originalVideoTrackRef.current) {
              sender.replaceTrack(originalVideoTrackRef.current);
            }
          }
        });
      } catch (error) {
        console.error('Failed to restore original video track:', error);
      }
    }
  }, [localStream, peers]);

  const stopAllStreams = useCallback(() => {
    if (localStream) {
      localStream.getTracks().forEach(track => track.stop());
      setLocalStream(null);
    }
    if (screenStream) {
      screenStream.getTracks().forEach(track => track.stop());
      setScreenStream(null);
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (virtualBgRef.current) {
      virtualBgRef.current.destroy();
      virtualBgRef.current = null;
    }
    if (hiddenVideoRef.current) {
      hiddenVideoRef.current.srcObject = null;
      hiddenVideoRef.current.remove();
      hiddenVideoRef.current = null;
    }
    if (outputCanvasRef.current) {
      outputCanvasRef.current.remove();
      outputCanvasRef.current = null;
    }
    if (processedVideoTrackRef.current) {
      processedVideoTrackRef.current.stop();
      processedVideoTrackRef.current = null;
    }
    originalVideoTrackRef.current = null;
    stopVirtualBackground();
  }, [localStream, screenStream, setLocalStream, setScreenStream, stopVirtualBackground]);

  useEffect(() => {
    if (virtualBackground && localStream) {
      if (virtualBackground.type !== 'none') {
        applyVirtualBackground(localStream);
      } else {
        stopVirtualBackground();
      }
    }
  }, [virtualBackground, localStream, applyVirtualBackground, stopVirtualBackground]);

  useEffect(() => {
    return () => {
      stopAllStreams();
    };
  }, [stopAllStreams]);

  return {
    getUserMedia,
    getScreenStream,
    stopScreenShare,
    toggleMute,
    toggleVideo,
    changeResolution,
    switchCamera,
    setupAudioProcessing,
    applyVirtualBackground,
    stopVirtualBackground,
    stopAllStreams,
    localVideoRef,
    outputCanvasRef,
    virtualBgRef
  };
};

export default useMedia;

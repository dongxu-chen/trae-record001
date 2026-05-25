import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import useMeetingStore from '../store/useMeetingStore';
import useSocket from '../hooks/useSocket';
import useMedia from '../hooks/useMedia';
import useWebRTC from '../hooks/useWebRTC';
import useBandwidthAdaptation from '../hooks/useBandwidthAdaptation';
import useRecording from '../hooks/useRecording';
import useMeetingMinutes from '../hooks/useMeetingMinutes';
import useGestureRecognition from '../hooks/useGestureRecognition';
import WebGLVirtualBackground from '../utils/WebGLVirtualBackground';
import VideoGrid from '../components/VideoGrid';
import ControlBar from '../components/ControlBar';
import ChatPanel from '../components/ChatPanel';
import ParticipantsPanel from '../components/ParticipantsPanel';
import SettingsPanel from '../components/SettingsPanel';
import MinutesPanel from '../components/MinutesPanel';
import BeautyPanel from '../components/BeautyPanel';
import { GestureEffect, GestureToast } from '../components/GestureEffect';
import { CopyIcon, RecordIcon, StopIcon, MagicIcon, DocumentIcon, SparklesIcon } from '../components/icons';

const MeetingPage = () => {
  const { roomId: urlRoomId } = useParams();
  const navigate = useNavigate();

  const {
    socket,
    connect,
    updateMediaState,
    sendMessage,
    raiseHand,
    leaveRoom
  } = useSocket();

  const {
    getUserMedia,
    getScreenStream,
    stopScreenShare,
    toggleMute,
    toggleVideo,
    changeResolution,
    switchCamera,
    stopAllStreams,
    localVideoRef
  } = useMedia();

  const {
    roomId,
    user,
    isMuted,
    isVideoOn,
    isScreenSharing,
    isChatOpen,
    isParticipantsOpen,
    isSettingsOpen,
    localStream,
    virtualBackground,
    beautyConfig,
    connectionQuality,
    participants,
    setParticipants,
    setMessages,
    setRoomId,
    setIsChatOpen,
    setIsParticipantsOpen,
    setIsSettingsOpen,
    setIsScreenSharing,
    setIsMuted,
    setIsVideoOn,
    setVirtualBackground,
    setBeautyConfig,
    reset
  } = useMeetingStore();

  const webrtc = useWebRTC(socket);
  const bandwidth = useBandwidthAdaptation(webrtc.peers, changeResolution);
  const recording = useRecording();
  const minutes = useMeetingMinutes();
  const gesture = useGestureRecognition(localVideoRef, true);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCopied, setIsCopied] = useState(false);
  const [isBeautyOpen, setIsBeautyOpen] = useState(false);
  const [isMinutesOpen, setIsMinutesOpen] = useState(false);
  const [showGestureEffect, setShowGestureEffect] = useState(false);
  const [lastGesture, setLastGesture] = useState(null);
  const [beautyEffect, setBeautyEffect] = useState(null);
  const [offscreenCanvas, setOffscreenCanvas] = useState(null);
  const initializedRef = useRef(false);
  const beautyRef = useRef(null);

  useEffect(() => {
    const canvas = document.createElement('canvas');
    canvas.style.display = 'none';
    document.body.appendChild(canvas);
    setOffscreenCanvas(canvas);

    return () => {
      if (canvas.parentNode) {
        canvas.parentNode.removeChild(canvas);
      }
    };
  }, []);

  useEffect(() => {
    if (!offscreenCanvas || !localVideoRef) return;

    beautyRef.current = new WebGLVirtualBackground(offscreenCanvas);
    beautyRef.current.setBeauty({
      enabled: beautyConfig?.enabled || false,
      smoothLevel: beautyConfig?.smoothLevel ?? 0.5,
      whitenLevel: beautyConfig?.whitenLevel ?? 0.3,
      slimLevel: beautyConfig?.slimLevel ?? 0.2
    });

    return () => {
      if (beautyRef.current) {
        beautyRef.current.destroy();
      }
    };
  }, [offscreenCanvas, localVideoRef]);

  useEffect(() => {
    if (!beautyRef.current || !localVideoRef) return;

    beautyRef.current.setBeauty({
      enabled: beautyConfig?.enabled || false,
      smoothLevel: beautyConfig?.smoothLevel ?? 0.5,
      whitenLevel: beautyConfig?.whitenLevel ?? 0.3,
      slimLevel: beautyConfig?.slimLevel ?? 0.2
    });

    if (beautyConfig?.enabled || virtualBackground) {
      beautyRef.current.start(localVideoRef);
    } else {
      beautyRef.current.stop();
    }
  }, [beautyConfig, virtualBackground, localVideoRef]);

  useEffect(() => {
    if (!urlRoomId || !user) {
      navigate('/');
      return;
    }

    const init = async () => {
      if (initializedRef.current) return;
      initializedRef.current = true;

      try {
        connect();
        await getUserMedia('720p');
        setRoomId(urlRoomId);
        setIsLoading(false);
      } catch (err) {
        console.error('Failed to initialize media:', err);
        setError('无法访问摄像头或麦克风，请检查权限设置');
        setIsLoading(false);
      }
    };

    init();

    return () => {
      handleHangUp();
    };
  }, [urlRoomId, user, navigate, connect, getUserMedia, setRoomId]);

  useEffect(() => {
    if (!socket || isLoading) return;

    const onParticipantJoined = ({ id, user: participantUser, participants: newParticipants }) => {
      setParticipants(newParticipants);
      
      const others = newParticipants.filter(p => p.user.id !== user?.id);
      webrtc.connectToParticipants(others);
    };

    const onParticipantLeft = ({ id, user: leftUser }) => {
      webrtc.cleanupPeer(id);
    };

    const onMediaStateUpdated = ({ id, isMuted, isVideoOn, isScreenSharing }) => {
    };

    const onMessageReceived = (message) => {
    };

    const onHandRaised = ({ id, raised, user: handUser }) => {
    };

    socket.on('participant-joined', onParticipantJoined);
    socket.on('participant-left', onParticipantLeft);
    socket.on('media-state-updated', onMediaStateUpdated);
    socket.on('message-received', onMessageReceived);
    socket.on('hand-raised', onHandRaised);

    return () => {
      socket.off('participant-joined', onParticipantJoined);
      socket.off('participant-left', onParticipantLeft);
      socket.off('media-state-updated', onMediaStateUpdated);
      socket.off('message-received', onMessageReceived);
      socket.off('hand-raised', onHandRaised);
    };
  }, [socket, isLoading, user, setParticipants, webrtc]);

  useEffect(() => {
    if (!isLoading && participants.length > 0 && socket) {
      const others = participants.filter(p => p.user.id !== user?.id);
      if (others.length > 0 && webrtc.peers.size === 0) {
        webrtc.connectToParticipants(others);
      }
    }
  }, [isLoading, participants, user, socket, webrtc]);

  useEffect(() => {
    if (isScreenSharing) {
      webrtc.updatePeerStreams();
    }
  }, [isScreenSharing, webrtc]);

  useEffect(() => {
    if (!gesture.currentGesture) return;

    setLastGesture(gesture.currentGesture);
    setShowGestureEffect(true);

    if (gesture.currentGesture.type === 'hand_raise') {
      raiseHand(roomId, true);
      setTimeout(() => raiseHand(roomId, false), 3000);
    } else if (gesture.currentGesture.type === 'thumbs_up') {
      sendMessage(roomId, '👍 点赞！', 'emoji');
    }
  }, [gesture.currentGesture, roomId, raiseHand, sendMessage]);

  const handleToggleMute = useCallback(() => {
    const newMuted = toggleMute();
    setIsMuted(newMuted);
    updateMediaState(roomId, { isMuted: newMuted });
  }, [toggleMute, setIsMuted, updateMediaState, roomId]);

  const handleToggleVideo = useCallback(() => {
    const newVideoOn = toggleVideo();
    setIsVideoOn(newVideoOn);
    updateMediaState(roomId, { isVideoOn: newVideoOn });
  }, [toggleVideo, setIsVideoOn, updateMediaState, roomId]);

  const handleToggleScreenShare = useCallback(async () => {
    if (isScreenSharing) {
      stopScreenShare();
      setIsScreenSharing(false);
      updateMediaState(roomId, { isScreenSharing: false });
      webrtc.updatePeerStreams();
    } else {
      try {
        await getScreenStream();
        setIsScreenSharing(true);
        updateMediaState(roomId, { isScreenSharing: true });
        webrtc.updatePeerStreams();
      } catch (err) {
        console.error('Failed to start screen share:', err);
      }
    }
  }, [isScreenSharing, getScreenStream, stopScreenShare, setIsScreenSharing, 
      updateMediaState, roomId, webrtc]);

  const handleToggleChat = useCallback(() => {
    setIsChatOpen(!isChatOpen);
    setIsParticipantsOpen(false);
    setIsSettingsOpen(false);
    setIsBeautyOpen(false);
    setIsMinutesOpen(false);
  }, [isChatOpen, setIsChatOpen, setIsParticipantsOpen, setIsSettingsOpen, setIsBeautyOpen, setIsMinutesOpen]);

  const handleToggleParticipants = useCallback(() => {
    setIsParticipantsOpen(!isParticipantsOpen);
    setIsChatOpen(false);
    setIsSettingsOpen(false);
    setIsBeautyOpen(false);
    setIsMinutesOpen(false);
  }, [isParticipantsOpen, setIsParticipantsOpen, setIsChatOpen, setIsSettingsOpen, setIsBeautyOpen, setIsMinutesOpen]);

  const handleToggleSettings = useCallback(() => {
    setIsSettingsOpen(!isSettingsOpen);
    setIsChatOpen(false);
    setIsParticipantsOpen(false);
    setIsBeautyOpen(false);
    setIsMinutesOpen(false);
  }, [isSettingsOpen, setIsSettingsOpen, setIsChatOpen, setIsParticipantsOpen, setIsBeautyOpen, setIsMinutesOpen]);

  const handleToggleBeauty = useCallback(() => {
    setIsBeautyOpen(!isBeautyOpen);
    setIsChatOpen(false);
    setIsParticipantsOpen(false);
    setIsSettingsOpen(false);
    setIsMinutesOpen(false);
  }, [isBeautyOpen, setIsBeautyOpen, setIsChatOpen, setIsParticipantsOpen, setIsSettingsOpen, setIsMinutesOpen]);

  const handleToggleMinutes = useCallback(() => {
    setIsMinutesOpen(!isMinutesOpen);
    setIsChatOpen(false);
    setIsParticipantsOpen(false);
    setIsSettingsOpen(false);
    setIsBeautyOpen(false);
  }, [isMinutesOpen, setIsMinutesOpen, setIsChatOpen, setIsParticipantsOpen, setIsSettingsOpen, setIsBeautyOpen]);

  const handleBeautyChange = useCallback((config) => {
    setBeautyConfig(config);
  }, [setBeautyConfig]);

  const handleHangUp = useCallback(() => {
    leaveRoom(roomId);
    stopAllStreams();
    webrtc.disconnectAll();
    
    if (beautyRef.current) {
      beautyRef.current.destroy();
      beautyRef.current = null;
    }
    
    reset();
    navigate('/');
  }, [roomId, leaveRoom, stopAllStreams, webrtc, reset, navigate]);

  const handleChangeResolution = useCallback(async (resolutionName) => {
    const success = await changeResolution(resolutionName);
    if (success) {
      await webrtc.updatePeerBitrate(resolutionName);
    }
    return success;
  }, [changeResolution, webrtc]);

  const handleSwitchCamera = useCallback(async () => {
    await switchCamera();
  }, [switchCamera]);

  const handleRaiseHand = useCallback((raised) => {
    raiseHand(roomId, raised);
  }, [raiseHand, roomId]);

  const handleSendMessage = useCallback((roomId, content, type) => {
    sendMessage(roomId, content, type);
  }, [sendMessage]);

  const handleCopyRoomId = useCallback(() => {
    navigator.clipboard.writeText(roomId);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  }, [roomId]);

  const handleGestureEffectComplete = useCallback(() => {
    setShowGestureEffect(false);
    setLastGesture(null);
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white text-lg">正在加入会议...</p>
          <p className="text-slate-400 text-sm mt-2">请允许访问摄像头和麦克风</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-800 rounded-2xl p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">无法加入会议</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="bg-primary-500 hover:bg-primary-600 text-white font-medium py-3 px-8 rounded-xl transition-all"
          >
            返回
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-slate-900 overflow-hidden">
      <div className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-white font-semibold">视频会议</h1>
          <button
            onClick={handleCopyRoomId}
            className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 px-3 py-1.5 rounded-lg text-sm transition-colors"
          >
            <span className="text-slate-300">房间号:</span>
            <span className="text-white font-mono font-semibold">{roomId}</span>
            <CopyIcon className="w-4 h-4 text-slate-400" />
            {isCopied && <span className="text-green-400 text-xs">已复制</span>}
          </button>
        </div>
        <div className="flex items-center gap-3">
          {gesture.isDetecting && (
            <div className="flex items-center gap-2 bg-purple-500/20 text-purple-400 px-3 py-1.5 rounded-lg">
              <SparklesIcon className="w-4 h-4" />
              <span className="text-xs">手势识别中</span>
            </div>
          )}
          {beautyConfig?.enabled && (
            <div className="flex items-center gap-2 bg-pink-500/20 text-pink-400 px-3 py-1.5 rounded-lg">
              <MagicIcon className="w-4 h-4" />
              <span className="text-xs">美颜中</span>
            </div>
          )}
          {recording.isRecording && (
            <div className="flex items-center gap-2 bg-red-500/20 text-red-400 px-3 py-1.5 rounded-lg">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              <span className="text-sm font-medium">
                录制中 {recording.formatDuration(recording.getRecordingDuration())}
              </span>
            </div>
          )}
          <span className="text-sm text-slate-400">
            {participants.length + 1} 人参会
          </span>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-hidden">
          <VideoGrid />
        </div>

        {isChatOpen && (
          <ChatPanel
            onSendMessage={handleSendMessage}
            roomId={roomId}
          />
        )}

        {isParticipantsOpen && <ParticipantsPanel />}
        {isSettingsOpen && <SettingsPanel />}
        {isBeautyOpen && (
          <BeautyPanel
            onClose={() => setIsBeautyOpen(false)}
            onBeautyChange={handleBeautyChange}
            initialConfig={beautyConfig}
          />
        )}
        {isMinutesOpen && (
          <MinutesPanel
            onClose={() => setIsMinutesOpen(false)}
          />
        )}
      </div>

      <ControlBar
        onToggleMute={handleToggleMute}
        onToggleVideo={handleToggleVideo}
        onToggleScreenShare={handleToggleScreenShare}
        onToggleChat={handleToggleChat}
        onToggleParticipants={handleToggleParticipants}
        onToggleSettings={handleToggleSettings}
        onToggleBeauty={handleToggleBeauty}
        onToggleMinutes={handleToggleMinutes}
        onHangUp={handleHangUp}
        onChangeResolution={handleChangeResolution}
        onSwitchCamera={handleSwitchCamera}
        onRaiseHand={handleRaiseHand}
        connectionQuality={connectionQuality}
        getQualityText={bandwidth.getQualityText}
        isBeautyOpen={isBeautyOpen}
        isMinutesOpen={isMinutesOpen}
        beautyEnabled={beautyConfig?.enabled}
      />

      {showGestureEffect && lastGesture && (
        <>
          <GestureEffect
            gesture={lastGesture}
            onComplete={handleGestureEffectComplete}
          />
          <GestureToast
            gesture={lastGesture}
            onClose={handleGestureEffectComplete}
          />
        </>
      )}
    </div>
  );
};

export default MeetingPage;

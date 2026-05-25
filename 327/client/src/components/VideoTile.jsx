import React, { useRef, useEffect, useState } from 'react';
import useMeetingStore from '../store/useMeetingStore';
import { MicIcon, VideoIcon, SignalIcon } from './icons';

const VideoTile = ({ participant, isLocal = false, isDominant = false }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const { virtualBackground, applyVirtualBackground, stopVirtualBackground } = useMeetingStore();

  useEffect(() => {
    if (!videoRef.current) return;

    if (isLocal) {
      const { localStream } = useMeetingStore.getState();
      if (localStream && videoRef.current) {
        videoRef.current.srcObject = localStream;
        videoRef.current.muted = true;
      }
    } else if (participant) {
      const { peers } = useMeetingStore.getState();
      const peer = peers.get(participant.id);
      if (peer && peer._remoteStream) {
        videoRef.current.srcObject = peer._remoteStream;
        videoRef.current.muted = false;
      }
    }

    return () => {
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [isLocal, participant]);

  useEffect(() => {
    if (isLocal && videoRef.current && canvasRef.current) {
      if (virtualBackground && virtualBackground.type !== 'none') {
        applyVirtualBackground(videoRef.current, canvasRef.current);
      } else {
        stopVirtualBackground();
      }
    }

    return () => {
      stopVirtualBackground();
    };
  }, [isLocal, virtualBackground, applyVirtualBackground, stopVirtualBackground]);

  const videoId = isLocal ? 'video-local' : `video-${participant?.id}`;
  const audioId = isLocal ? 'audio-local' : `audio-${participant?.id}`;

  const showVirtualBg = isLocal && virtualBackground && virtualBackground.type !== 'none';

  return (
    <div className={`video-container ${isDominant ? 'ring-2 ring-primary-500' : ''}`}>
      <video
        ref={videoRef}
        id={videoId}
        autoPlay
        playsInline
        className={isLocal ? 'mirrored' : ''}
        style={{ display: showVirtualBg ? 'none' : 'block' }}
      />
      
      {showVirtualBg && (
        <canvas
          ref={canvasRef}
          className="virtual-bg-canvas mirrored"
          style={{ display: 'block' }}
        />
      )}

      <audio id={audioId} autoPlay playsInline style={{ display: 'none' }} />

      {!participant?.isVideoOn && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-800">
          <div className="w-20 h-20 rounded-full bg-slate-700 flex items-center justify-center text-2xl font-bold text-white">
            {participant?.user?.name?.charAt(0).toUpperCase() || 'U'}
          </div>
        </div>
      )}

      {isSpeaking && <div className="speaker-indicator" />}

      <div className="name-badge">
        <span className="flex items-center gap-1.5">
          {participant?.isMuted ? (
            <MicIcon className="w-3 h-3 text-red-400" muted={true} />
          ) : (
            <MicIcon className="w-3 h-3 text-green-400" muted={false} />
          )}
          {participant?.user?.name || (isLocal ? '你' : '未知用户')}
          {isLocal && ' (你)'}
        </span>
      </div>

      <div className="absolute top-2 right-2 flex items-center gap-2">
        {!isLocal && participant && (
          <div className="bg-black/50 rounded px-1.5 py-0.5">
            <SignalIcon className="w-4 h-4" quality="good" />
          </div>
        )}
        {participant?.isScreenSharing && (
          <div className="bg-blue-500 text-white text-xs px-2 py-1 rounded">
            屏幕共享
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoTile;

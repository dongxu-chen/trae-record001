import React, { useState, useEffect } from 'react';
import useMeetingStore from '../store/useMeetingStore';
import {
  MicIcon,
  VideoIcon,
  ScreenShareIcon,
  ChatIcon,
  UsersIcon,
  SettingsIcon,
  RecordIcon,
  HangUpIcon,
  SwitchCameraIcon,
  HandIcon,
  DownloadIcon,
  SignalIcon,
  MagicIcon,
  DocumentIcon
} from './icons';
import useRecording from '../hooks/useRecording';
import { RESOLUTION_LEVELS } from '../config/webrtcConfig';

const ControlBar = ({
  onToggleMute,
  onToggleVideo,
  onToggleScreenShare,
  onToggleChat,
  onToggleParticipants,
  onToggleSettings,
  onToggleBeauty,
  onToggleMinutes,
  onHangUp,
  onChangeResolution,
  onSwitchCamera,
  onRaiseHand,
  connectionQuality,
  getQualityText,
  isBeautyOpen,
  isMinutesOpen,
  beautyEnabled
}) => {
  const {
    isMuted,
    isVideoOn,
    isScreenSharing,
    isChatOpen,
    isParticipantsOpen,
    isSettingsOpen,
    currentResolution,
    isRecording,
    recordingInfo,
    raisedHands,
    socket
  } = useMeetingStore();

  const {
    startRecording,
    stopRecording,
    getRecordingDuration,
    formatDuration,
    downloadRecording
  } = useRecording();

  const [recordingTime, setRecordingTime] = useState(0);
  const [isHandRaised, setIsHandRaised] = useState(false);
  const [showResolutionMenu, setShowResolutionMenu] = useState(false);
  const [lastRecording, setLastRecording] = useState(null);

  useEffect(() => {
    let interval;
    if (isRecording) {
      interval = setInterval(() => {
        setRecordingTime(getRecordingDuration());
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRecording, getRecordingDuration]);

  useEffect(() => {
    if (!socket) return;

    const handleRecordingStopped = (info) => {
      setLastRecording(info);
      setRecordingTime(0);
    };

    socket.on('recording-stopped', handleRecordingStopped);
    return () => socket.off('recording-stopped', handleRecordingStopped);
  }, [socket]);

  const handleToggleRecording = async () => {
    if (isRecording) {
      const result = await stopRecording();
      if (result?.success) {
        setLastRecording(result);
      }
      setRecordingTime(0);
    } else {
      const result = await startRecording('grid');
      if (result?.success) {
        setLastRecording(null);
      }
    }
  };

  const handleDownloadRecording = () => {
    if (lastRecording?.filename) {
      downloadRecording(lastRecording.filename);
    }
  };

  const handleToggleHand = () => {
    const newState = !isHandRaised;
    setIsHandRaised(newState);
    onRaiseHand?.(newState);
  };

  const handleChangeResolution = async (resolutionName) => {
    await onChangeResolution?.(resolutionName);
    setShowResolutionMenu(false);
  };

  const currentResolutionName = RESOLUTION_LEVELS.find(
    l => l.width === currentResolution.width
  )?.name || '720p';

  return (
    <div className="bg-slate-900/95 backdrop-blur-sm border-t border-slate-700 px-6 py-4">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center gap-4">
          {isRecording && (
            <div className="flex items-center gap-2 bg-red-500/20 text-red-400 px-4 py-2 rounded-lg">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              <span className="font-medium">录制中 {formatDuration(recordingTime)}</span>
              {recordingInfo && (
                <span className="text-xs text-slate-400">服务端合流</span>
              )}
            </div>
          )}

          {!isRecording && lastRecording && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-green-400">
                录制完成: {lastRecording.filename}
              </span>
              <button
                onClick={handleDownloadRecording}
                className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors"
              >
                <DownloadIcon className="w-4 h-4" />
                <span>下载录制</span>
              </button>
            </div>
          )}

          <div className="flex items-center gap-2 text-sm text-slate-400">
            <SignalIcon quality={connectionQuality} />
            <span>{getQualityText?.(connectionQuality)}</span>
            <span className="text-xs">({currentResolution.width}x{currentResolution.height})</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onToggleMute}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
              isMuted
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title={isMuted ? '取消静音' : '静音'}
          >
            <MicIcon muted={isMuted} />
          </button>

          <button
            onClick={onToggleVideo}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
              !isVideoOn
                ? 'bg-red-500 hover:bg-red-600 text-white'
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title={isVideoOn ? '关闭摄像头' : '开启摄像头'}
          >
            <VideoIcon off={!isVideoOn} />
          </button>

          <button
            onClick={onToggleScreenShare}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
              isScreenSharing
                ? 'bg-green-500 hover:bg-green-600 text-white'
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title={isScreenSharing ? '停止共享' : '共享屏幕'}
          >
            <ScreenShareIcon active={isScreenSharing} />
          </button>

          <div className="relative">
            <button
              onClick={() => setShowResolutionMenu(!showResolutionMenu)}
              className="w-12 h-12 rounded-full flex items-center justify-center bg-slate-700 hover:bg-slate-600 text-white transition-all"
              title="分辨率"
            >
              <span className="text-xs font-bold">{currentResolutionName.replace('p', '')}</span>
            </button>

            {showResolutionMenu && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-slate-800 rounded-lg shadow-xl border border-slate-700 py-2 min-w-32">
                {RESOLUTION_LEVELS.map((level) => (
                  <button
                    key={level.name}
                    onClick={() => handleChangeResolution(level.name)}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-slate-700 transition-colors ${
                      currentResolutionName === level.name
                        ? 'text-primary-400 bg-slate-700/50'
                        : 'text-white'
                    }`}
                  >
                    {level.name} ({level.width}x{level.height})
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={onSwitchCamera}
            className="w-12 h-12 rounded-full flex items-center justify-center bg-slate-700 hover:bg-slate-600 text-white transition-all"
            title="切换摄像头"
          >
            <SwitchCameraIcon />
          </button>

          <button
            onClick={handleToggleHand}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
              isHandRaised
                ? 'bg-yellow-500 hover:bg-yellow-600 text-white'
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title={isHandRaised ? '放下手' : '举手'}
          >
            <HandIcon raised={isHandRaised} />
          </button>

          <button
            onClick={handleToggleRecording}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
              isRecording
                ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title={isRecording ? '停止录制' : '开始录制'}
          >
            <RecordIcon active={isRecording} />
          </button>

          <button
            onClick={onHangUp}
            className="w-16 h-12 rounded-full flex items-center justify-center bg-red-500 hover:bg-red-600 text-white transition-all ml-2"
            title="离开会议"
          >
            <HangUpIcon />
          </button>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onToggleChat}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
              isChatOpen
                ? 'bg-primary-500 text-white'
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title="聊天"
          >
            <ChatIcon active={isChatOpen} />
          </button>

          <button
            onClick={onToggleParticipants}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
              isParticipantsOpen
                ? 'bg-primary-500 text-white'
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title="参与者"
          >
            <UsersIcon active={isParticipantsOpen} />
          </button>

          <button
            onClick={onToggleSettings}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
              isSettingsOpen
                ? 'bg-primary-500 text-white'
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title="设置"
          >
            <SettingsIcon active={isSettingsOpen} />
          </button>

          <button
            onClick={onToggleBeauty}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
              isBeautyOpen
                ? 'bg-pink-500 text-white'
                : beautyEnabled
                ? 'bg-pink-500/20 text-pink-400 hover:bg-pink-500/30'
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title="美颜"
          >
            <MagicIcon />
          </button>

          <button
            onClick={onToggleMinutes}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
              isMinutesOpen
                ? 'bg-indigo-500 text-white'
                : 'bg-slate-700 hover:bg-slate-600 text-white'
            }`}
            title="会议纪要"
          >
            <DocumentIcon />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ControlBar;

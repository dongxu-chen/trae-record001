import React, { useMemo } from 'react';
import useMeetingStore from '../store/useMeetingStore';
import { MicIcon, VideoIcon, HandIcon } from './icons';

const ParticipantsPanel = () => {
  const { participants, user, raisedHands } = useMeetingStore();

  const allParticipants = useMemo(() => {
    const { socket, isMuted, isVideoOn, isScreenSharing } = useMeetingStore.getState();
    
    const localParticipant = {
      id: socket?.id || 'local',
      user,
      isMuted,
      isVideoOn,
      isScreenSharing,
      isLocal: true
    };

    const others = participants
      .filter(p => p.user.id !== user?.id)
      .map(p => ({ ...p, isLocal: false }));

    const sorted = [localParticipant, ...others].sort((a, b) => {
      if (raisedHands.has(a.id) && !raisedHands.has(b.id)) return -1;
      if (!raisedHands.has(a.id) && raisedHands.has(b.id)) return 1;
      return 0;
    });

    return sorted;
  }, [participants, user, raisedHands]);

  return (
    <div className="w-80 h-full bg-slate-800 border-l border-slate-700 flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <h3 className="text-lg font-semibold text-white">参与者</h3>
        <p className="text-sm text-slate-400">{allParticipants.length} 人</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {allParticipants.map((participant) => (
          <div
            key={participant.id}
            className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
              raisedHands.has(participant.id)
                ? 'bg-yellow-500/20 border border-yellow-500/50'
                : 'bg-slate-700/50 hover:bg-slate-700'
            }`}
          >
            <div className="relative">
              <div className="w-10 h-10 rounded-full bg-slate-600 flex items-center justify-center text-white font-semibold">
                {participant.user?.avatar ? (
                  <img
                    src={participant.user.avatar}
                    alt={participant.user.name}
                    className="w-full h-full rounded-full object-cover"
                  />
                ) : (
                  participant.user?.name?.charAt(0).toUpperCase() || 'U'
                )}
              </div>
              {raisedHands.has(participant.id) && (
                <div className="absolute -top-1 -right-1 w-5 h-5 bg-yellow-500 rounded-full flex items-center justify-center">
                  <HandIcon className="w-3 h-3 text-white" raised={true} />
                </div>
              )}
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate">
                {participant.user?.name || '未知用户'}
                {participant.isLocal && <span className="text-slate-400 ml-1">(你)</span>}
              </p>
              {participant.isScreenSharing && (
                <p className="text-xs text-blue-400">正在共享屏幕</p>
              )}
            </div>

            <div className="flex items-center gap-2">
              <div className={`p-1.5 rounded ${
                participant.isMuted ? 'bg-red-500/20' : 'bg-green-500/20'
              }`}>
                <MicIcon
                  className={`w-4 h-4 ${participant.isMuted ? 'text-red-400' : 'text-green-400'}`}
                  muted={participant.isMuted}
                />
              </div>
              <div className={`p-1.5 rounded ${
                !participant.isVideoOn ? 'bg-red-500/20' : 'bg-green-500/20'
              }`}>
                <VideoIcon
                  className={`w-4 h-4 ${!participant.isVideoOn ? 'text-red-400' : 'text-green-400'}`}
                  off={!participant.isVideoOn}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-slate-700">
        <p className="text-xs text-slate-500 text-center">
          最多支持 50 人参会
        </p>
      </div>
    </div>
  );
};

export default ParticipantsPanel;

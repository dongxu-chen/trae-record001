import React, { useMemo } from 'react';
import VideoTile from './VideoTile';
import useMeetingStore from '../store/useMeetingStore';

const VideoGrid = () => {
  const { participants, user, screenStream, isScreenSharing } = useMeetingStore();

  const screenSharingParticipant = useMemo(() => {
    return participants.find(p => p.isScreenSharing);
  }, [participants]);

  const otherParticipants = useMemo(() => {
    if (screenSharingParticipant) {
      return participants.filter(p => p.id !== screenSharingParticipant.id);
    }
    return participants;
  }, [participants, screenSharingParticipant]);

  const localParticipant = useMemo(() => {
    const { socket, isMuted, isVideoOn, isScreenSharing } = useMeetingStore.getState();
    return {
      id: socket?.id || 'local',
      user,
      isMuted,
      isVideoOn,
      isScreenSharing
    };
  }, [user]);

  const allParticipants = useMemo(() => {
    const others = otherParticipants.filter(p => p.user.id !== user?.id);
    return [localParticipant, ...others];
  }, [localParticipant, otherParticipants, user]);

  const layoutClass = useMemo(() => {
    const count = allParticipants.length;
    if (count <= 1) return 'layout-1';
    if (count === 2) return 'layout-2';
    if (count === 3) return 'layout-3';
    if (count === 4) return 'layout-4';
    if (count <= 6) return 'layout-6';
    if (count <= 9) return 'layout-9';
    return 'layout-12';
  }, [allParticipants.length]);

  if (screenSharingParticipant && screenStream) {
    return (
      <div className="flex flex-col h-full p-4 gap-4">
        <div className="flex-1 screen-share-view rounded-xl overflow-hidden bg-black">
          <video
            id={`video-${screenSharingParticipant.id}`}
            autoPlay
            playsInline
            className="w-full h-full object-contain"
            ref={(el) => {
              if (el && screenStream) {
                const { peers } = useMeetingStore.getState();
                if (screenSharingParticipant.id === localParticipant.id) {
                  el.srcObject = screenStream;
                  el.muted = true;
                } else {
                  const peer = peers.get(screenSharingParticipant.id);
                  if (peer && peer._remoteStream) {
                    el.srcObject = peer._remoteStream;
                  }
                }
              }
            }}
          />
          <div className="absolute bottom-4 left-4 bg-black/60 px-3 py-1.5 rounded-lg text-white text-sm">
            {screenSharingParticipant.user.name} 正在共享屏幕
          </div>
        </div>

        <div className="h-32 flex gap-3 overflow-x-auto pb-2">
          {allParticipants.map((participant, index) => (
            <div key={participant.id || index} className="w-48 h-full flex-shrink-0">
              <VideoTile
                participant={participant}
                isLocal={participant.id === localParticipant.id}
              />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={`grid-layout ${layoutClass}`}>
      {allParticipants.map((participant, index) => (
        <VideoTile
          key={participant.id || index}
          participant={participant}
          isLocal={participant.id === localParticipant.id}
          isDominant={index === 0 && allParticipants.length > 1}
        />
      ))}
    </div>
  );
};

export default VideoGrid;

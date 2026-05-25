import { create } from 'zustand';

const useMeetingStore = create((set, get) => ({
  socket: null,
  localStream: null,
  screenStream: null,
  peers: new Map(),
  participants: [],
  messages: [],
  roomId: null,
  user: null,
  isMuted: false,
  isVideoOn: true,
  isScreenSharing: false,
  isRecording: false,
  recordingInfo: null,
  recordingStream: null,
  mediaRecorder: null,
  recordedChunks: [],
  virtualBackground: null,
  beautyConfig: {
    enabled: false,
    smoothLevel: 0.5,
    whitenLevel: 0.3,
    slimLevel: 0.2
  },
  connectionQuality: 'good',
  currentResolution: { width: 1280, height: 720 },
  activeSpeaker: null,
  raisedHands: new Set(),
  isChatOpen: false,
  isParticipantsOpen: false,
  isSettingsOpen: false,

  setSocket: (socket) => set({ socket }),
  setLocalStream: (stream) => set({ localStream: stream }),
  setScreenStream: (stream) => set({ screenStream: stream }),
  setRoomId: (roomId) => set({ roomId }),
  setUser: (user) => set({ user }),
  setIsMuted: (isMuted) => set({ isMuted }),
  setIsVideoOn: (isVideoOn) => set({ isVideoOn }),
  setIsScreenSharing: (isScreenSharing) => set({ isScreenSharing }),
  setIsRecording: (isRecording) => set({ isRecording }),
  setRecordingInfo: (recordingInfo) => set({ recordingInfo }),
  setRecordingStream: (recordingStream) => set({ recordingStream }),
  setMediaRecorder: (mediaRecorder) => set({ mediaRecorder }),
  setRecordedChunks: (recordedChunks) => set({ recordedChunks }),
  setVirtualBackground: (virtualBackground) => set({ virtualBackground }),
  setBeautyConfig: (beautyConfig) => set((state) => ({
    beautyConfig: { ...state.beautyConfig, ...beautyConfig }
  })),
  setConnectionQuality: (connectionQuality) => set({ connectionQuality }),
  setCurrentResolution: (currentResolution) => set({ currentResolution }),
  setActiveSpeaker: (activeSpeaker) => set({ activeSpeaker }),
  setIsChatOpen: (isChatOpen) => set({ isChatOpen }),
  setIsParticipantsOpen: (isParticipantsOpen) => set({ isParticipantsOpen }),
  setIsSettingsOpen: (isSettingsOpen) => set({ isSettingsOpen }),

  setParticipants: (participants) => set({ participants }),
  
  addParticipant: (participant) => set((state) => ({
    participants: [...state.participants, participant]
  })),

  removeParticipant: (id) => set((state) => ({
    participants: state.participants.filter(p => p.id !== id)
  })),

  updateParticipant: (id, updates) => set((state) => ({
    participants: state.participants.map(p => 
      p.id === id ? { ...p, ...updates } : p
    )
  })),

  addPeer: (peerId, peer) => set((state) => {
    const newPeers = new Map(state.peers);
    newPeers.set(peerId, peer);
    return { peers: newPeers };
  }),

  removePeer: (peerId) => set((state) => {
    const newPeers = new Map(state.peers);
    newPeers.delete(peerId);
    return { peers: newPeers };
  }),

  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),

  setMessages: (messages) => set({ messages }),

  toggleHandRaise: (participantId) => set((state) => {
    const newRaisedHands = new Set(state.raisedHands);
    if (newRaisedHands.has(participantId)) {
      newRaisedHands.delete(participantId);
    } else {
      newRaisedHands.add(participantId);
    }
    return { raisedHands: newRaisedHands };
  }),

  reset: () => set({
    localStream: null,
    screenStream: null,
    peers: new Map(),
    participants: [],
    messages: [],
    roomId: null,
    isMuted: false,
    isVideoOn: true,
    isScreenSharing: false,
    isRecording: false,
    recordingInfo: null,
    recordingStream: null,
    mediaRecorder: null,
    recordedChunks: [],
    virtualBackground: null,
    beautyConfig: {
      enabled: false,
      smoothLevel: 0.5,
      whitenLevel: 0.3,
      slimLevel: 0.2
    },
    activeSpeaker: null,
    raisedHands: new Set(),
    isChatOpen: false,
    isParticipantsOpen: false,
    isSettingsOpen: false,
  })
}));

export default useMeetingStore;

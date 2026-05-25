import { useEffect, useCallback } from 'react';
import { io } from 'socket.io-client';
import useMeetingStore from '../store/useMeetingStore';

const useSocket = () => {
  const {
    socket,
    setSocket,
    setParticipants,
    addParticipant,
    removeParticipant,
    updateParticipant,
    addMessage,
    setMessages,
    toggleHandRaise,
    addPeer,
    removePeer,
    peers
  } = useMeetingStore();

  const connect = useCallback(() => {
    const newSocket = io('http://localhost:3001', {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });

    newSocket.on('connect', () => {
      console.log('Connected to signaling server:', newSocket.id);
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected from signaling server');
    });

    newSocket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
    });

    newSocket.on('participant-joined', ({ id, user, participants }) => {
      setParticipants(participants);
    });

    newSocket.on('participant-left', ({ id, user }) => {
      removeParticipant(id);
      const peer = peers.get(id);
      if (peer) {
        peer.destroy();
        removePeer(id);
      }
    });

    newSocket.on('media-state-updated', ({ id, isMuted, isVideoOn, isScreenSharing }) => {
      updateParticipant(id, { isMuted, isVideoOn, isScreenSharing });
    });

    newSocket.on('message-received', (message) => {
      addMessage(message);
    });

    newSocket.on('hand-raised', ({ id, raised, user }) => {
      toggleHandRaise(id);
    });

    setSocket(newSocket);
    return newSocket;
  }, [setSocket, setParticipants, addParticipant, removeParticipant, 
      updateParticipant, addMessage, setMessages, toggleHandRaise, 
      addPeer, removePeer, peers]);

  const disconnect = useCallback(() => {
    if (socket) {
      socket.disconnect();
      setSocket(null);
    }
  }, [socket, setSocket]);

  const createRoom = useCallback(async (user) => {
    if (!socket) return null;
    return new Promise((resolve) => {
      socket.emit('create-room', { user }, (response) => {
        resolve(response);
      });
    });
  }, [socket]);

  const joinRoom = useCallback(async (roomId, user) => {
    if (!socket) return null;
    return new Promise((resolve) => {
      socket.emit('join-room', { roomId, user }, (response) => {
        resolve(response);
      });
    });
  }, [socket]);

  const leaveRoom = useCallback((roomId) => {
    if (socket && roomId) {
      socket.emit('leave-room', { roomId });
    }
  }, [socket]);

  const sendOffer = useCallback((to, offer) => {
    if (socket) {
      socket.emit('offer', { to, offer });
    }
  }, [socket]);

  const sendAnswer = useCallback((to, answer) => {
    if (socket) {
      socket.emit('answer', { to, answer });
    }
  }, [socket]);

  const sendIceCandidate = useCallback((to, candidate) => {
    if (socket) {
      socket.emit('ice-candidate', { to, candidate });
    }
  }, [socket]);

  const updateMediaState = useCallback((roomId, state) => {
    if (socket) {
      socket.emit('update-media-state', { roomId, ...state });
    }
  }, [socket]);

  const sendMessage = useCallback((roomId, content, type = 'text') => {
    if (socket) {
      socket.emit('send-message', { roomId, content, type });
    }
  }, [socket]);

  const raiseHand = useCallback((roomId, raised) => {
    if (socket) {
      socket.emit('raise-hand', { roomId, raised });
    }
  }, [socket]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    socket,
    connect,
    disconnect,
    createRoom,
    joinRoom,
    leaveRoom,
    sendOffer,
    sendAnswer,
    sendIceCandidate,
    updateMediaState,
    sendMessage,
    raiseHand
  };
};

export default useSocket;

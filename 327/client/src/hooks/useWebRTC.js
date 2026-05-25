import { useCallback, useEffect, useRef } from 'react';
import Peer from 'simple-peer';
import useMeetingStore from '../store/useMeetingStore';
import { PEER_CONFIG, RESOLUTION_LEVELS } from '../config/webrtcConfig';

const useWebRTC = (socket) => {
  const {
    localStream,
    screenStream,
    addPeer,
    removePeer,
    setConnectionQuality,
    isScreenSharing
  } = useMeetingStore();

  const peerRefs = useRef(new Map());
  const bandwidthStats = useRef(new Map());
  const cleanupPeerRef = useRef(null);
  const startBandwidthMonitoringRef = useRef(null);

  const cleanupPeer = useCallback((peerId) => {
    const peer = peerRefs.current.get(peerId);
    if (peer) {
      if (peer._statsInterval) {
        clearInterval(peer._statsInterval);
      }
      try {
        peer.destroy();
      } catch (e) {
        console.error('Error destroying peer:', e);
      }
      peerRefs.current.delete(peerId);
      bandwidthStats.current.delete(`${peerId}-bytes`);
      bandwidthStats.current.delete(`${peerId}-quality`);
    }
    removePeer(peerId);

    const videoElement = document.getElementById(`video-${peerId}`);
    if (videoElement && videoElement.srcObject) {
      videoElement.srcObject = null;
    }

    const audioElement = document.getElementById(`audio-${peerId}`);
    if (audioElement && audioElement.srcObject) {
      audioElement.srcObject = null;
    }
  }, [removePeer]);

  useEffect(() => {
    cleanupPeerRef.current = cleanupPeer;
  }, [cleanupPeer]);

  const startBandwidthMonitoring = useCallback((peerId, peer) => {
    if (!peer || !peer._pc) return;

    const statsInterval = setInterval(async () => {
      if (!peer._pc || peer.destroyed) {
        clearInterval(statsInterval);
        return;
      }

      try {
        const stats = await peer._pc.getStats(null);
        let totalBitrate = 0;
        let packetsLost = 0;
        let totalPackets = 0;

        stats.forEach(report => {
          if (report.type === 'inbound-rtp' && report.mediaType === 'video') {
            if (report.bytesReceived) {
              const prevBytes = bandwidthStats.current.get(`${peerId}-bytes`) || 0;
              const bitrate = ((report.bytesReceived - prevBytes) * 8) / 1000;
              totalBitrate += bitrate;
              bandwidthStats.current.set(`${peerId}-bytes`, report.bytesReceived);
            }
            if (report.packetsLost) {
              packetsLost += report.packetsLost;
            }
            if (report.packetsReceived) {
              totalPackets += report.packetsReceived;
            }
          }
        });

        const packetLossPercent = totalPackets > 0 ? (packetsLost / totalPackets) * 100 : 0;

        let quality = 'poor';
        if (totalBitrate > 2000 && packetLossPercent < 1) {
          quality = 'excellent';
        } else if (totalBitrate > 1000 && packetLossPercent < 3) {
          quality = 'good';
        } else if (totalBitrate > 500 && packetLossPercent < 5) {
          quality = 'fair';
        }

        setConnectionQuality(quality);
        bandwidthStats.current.set(`${peerId}-quality`, quality);

      } catch (error) {
        console.error('Failed to get stats:', error);
      }
    }, 2000);

    peer._statsInterval = statsInterval;
  }, [setConnectionQuality]);

  useEffect(() => {
    startBandwidthMonitoringRef.current = startBandwidthMonitoring;
  }, [startBandwidthMonitoring]);

  const createPeer = useCallback((targetId, initiator) => {
    if (!localStream) {
      console.error('No local stream available');
      return null;
    }

    if (peerRefs.current.has(targetId)) {
      return peerRefs.current.get(targetId);
    }

    try {
      const peer = new Peer({
        ...PEER_CONFIG,
        initiator,
        stream: localStream,
        objectMode: true
      });

      peer._targetId = targetId;
      peer._isInitiator = initiator;

      peer.on('signal', (data) => {
        if (!socket) return;
        
        if (data.type === 'offer') {
          socket.emit('offer', { to: targetId, offer: data });
        } else if (data.type === 'answer') {
          socket.emit('answer', { to: targetId, answer: data });
        } else if (data.candidate) {
          socket.emit('ice-candidate', { to: targetId, candidate: data });
        }
      });

      peer.on('stream', (remoteStream) => {
        console.log('Received remote stream from:', targetId);
        peer._remoteStream = remoteStream;
        
        const videoElement = document.getElementById(`video-${targetId}`);
        if (videoElement) {
          videoElement.srcObject = remoteStream;
        }

        const audioElement = document.getElementById(`audio-${targetId}`);
        if (audioElement) {
          audioElement.srcObject = remoteStream;
        }
      });

      peer.on('track', (track, stream) => {
        console.log('Received track:', track.kind);
      });

      peer.on('connect', () => {
        console.log('Peer connection established with:', targetId);
        peer._connected = true;
        if (startBandwidthMonitoringRef.current) {
          startBandwidthMonitoringRef.current(targetId, peer);
        }
      });

      peer.on('close', () => {
        console.log('Peer connection closed:', targetId);
        if (cleanupPeerRef.current) {
          cleanupPeerRef.current(targetId);
        }
      });

      peer.on('error', (err) => {
        console.error('Peer connection error:', targetId, err);
        if (cleanupPeerRef.current) {
          cleanupPeerRef.current(targetId);
        }
      });

      peerRefs.current.set(targetId, peer);
      addPeer(targetId, peer);

      return peer;
    } catch (err) {
      console.error('Failed to create peer:', err);
      return null;
    }
  }, [localStream, socket, addPeer]);

  const handleOffer = useCallback((from, offer) => {
    if (!socket) return;
    
    let peer = peerRefs.current.get(from);
    
    if (!peer) {
      peer = createPeer(from, false);
    }

    if (peer) {
      peer.signal(offer);
    }
  }, [socket, createPeer]);

  const handleAnswer = useCallback((from, answer) => {
    const peer = peerRefs.current.get(from);
    if (peer) {
      peer.signal(answer);
    }
  }, []);

  const handleIceCandidate = useCallback((from, candidate) => {
    const peer = peerRefs.current.get(from);
    if (peer) {
      peer.signal(candidate);
    }
  }, []);

  const connectToParticipants = useCallback((otherParticipants) => {
    if (!socket || !localStream) return;

    otherParticipants.forEach(participant => {
      if (!peerRefs.current.has(participant.id)) {
        console.log('Creating peer to:', participant.id);
        createPeer(participant.id, true);
      }
    });
  }, [socket, localStream, createPeer]);

  const updatePeerStreams = useCallback(() => {
    peerRefs.current.forEach((peer, peerId) => {
      if (peer.connected && peer._pc) {
        const senders = peer._pc.getSenders();
        
        if (isScreenSharing && screenStream) {
          const videoTrack = screenStream.getVideoTracks()[0];
          const videoSender = senders.find(s => s.track && s.track.kind === 'video');
          if (videoSender && videoTrack) {
            videoSender.replaceTrack(videoTrack);
          }
        } else if (localStream) {
          const videoTrack = localStream.getVideoTracks()[0];
          const videoSender = senders.find(s => s.track && s.track.kind === 'video');
          if (videoSender && videoTrack) {
            videoSender.replaceTrack(videoTrack);
          }
        }
      }
    });
  }, [isScreenSharing, screenStream, localStream]);

  const updatePeerBitrate = useCallback(async (resolutionName) => {
    const targetLevel = RESOLUTION_LEVELS.find(l => l.name === resolutionName);
    if (!targetLevel) return;

    peerRefs.current.forEach((peer, peerId) => {
      if (peer.connected && peer._pc) {
        const senders = peer._pc.getSenders();
        senders.forEach(sender => {
          if (sender.track && sender.track.kind === 'video' && sender.setParameters) {
            const parameters = sender.getParameters();
            if (parameters.encodings && parameters.encodings[0]) {
              parameters.encodings[0].maxBitrate = targetLevel.bitrate * 1000;
              sender.setParameters(parameters);
            }
          }
        });
      }
    });
  }, []);

  const getPeerConnectionQuality = useCallback((peerId) => {
    return bandwidthStats.current.get(`${peerId}-quality`) || 'unknown';
  }, []);

  const disconnectAll = useCallback(() => {
    peerRefs.current.forEach((peer, peerId) => {
      cleanupPeer(peerId);
    });
    peerRefs.current.clear();
    bandwidthStats.current.clear();
  }, [cleanupPeer]);

  useEffect(() => {
    if (!socket) return;

    const onOffer = ({ from, offer }) => handleOffer(from, offer);
    const onAnswer = ({ from, answer }) => handleAnswer(from, answer);
    const onIceCandidate = ({ from, candidate }) => handleIceCandidate(from, candidate);

    socket.on('offer', onOffer);
    socket.on('answer', onAnswer);
    socket.on('ice-candidate', onIceCandidate);

    return () => {
      socket.off('offer', onOffer);
      socket.off('answer', onAnswer);
      socket.off('ice-candidate', onIceCandidate);
    };
  }, [socket, handleOffer, handleAnswer, handleIceCandidate]);

  useEffect(() => {
    return () => {
      disconnectAll();
    };
  }, [disconnectAll]);

  return {
    createPeer,
    handleOffer,
    handleAnswer,
    handleIceCandidate,
    connectToParticipants,
    updatePeerStreams,
    updatePeerBitrate,
    getPeerConnectionQuality,
    disconnectAll,
    cleanupPeer,
    peers: peerRefs.current
  };
};

export default useWebRTC;

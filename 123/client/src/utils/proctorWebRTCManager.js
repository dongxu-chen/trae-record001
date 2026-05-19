class ProctorWebRTCManager {
  constructor(socket, config = {}) {
    this.socket = socket;
    this.peerConnections = new Map();
    this.remoteStreams = new Map();
    this.reconnectAttempts = new Map();
    this.maxReconnectAttempts = config.maxReconnectAttempts || 5;
    this.reconnectDelay = config.reconnectDelay || 2000;
    this.iceServers = config.iceServers || [
      { urls: 'stun:stun.l.google.com:19302' }
    ];
    this.onStreamAdded = config.onStreamAdded || (() => {});
    this.onStreamRemoved = config.onStreamRemoved || (() => {});
    this.onConnectionStateChange = config.onConnectionStateChange || (() => {});
  }

  getPeerKey(examineeId, streamType) {
    return `${examineeId}-${streamType}`;
  }

  async requestStream(examineeId, streamType) {
    const key = this.getPeerKey(examineeId, streamType);
    
    if (this.peerConnections.has(key)) {
      const pc = this.peerConnections.get(key);
      if (pc.connectionState === 'connected' || pc.connectionState === 'connecting') {
        return;
      }
    }

    const pc = new RTCPeerConnection({
      iceServers: this.iceServers,
      iceTransportPolicy: 'all'
    });

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        this.socket.emit('ice-candidate', {
          targetId: examineeId,
          candidate: event.candidate,
          streamType
        });
      }
    };

    pc.oniceconnectionstatechange = () => {
      const state = pc.iceConnectionState;
      this.onConnectionStateChange(examineeId, streamType, state);
      
      if (state === 'failed' || state === 'disconnected') {
        this.handleReconnection(examineeId, streamType);
      }
    };

    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;
      if (state === 'failed') {
        this.handleReconnection(examineeId, streamType);
      }
    };

    pc.ontrack = (event) => {
      const [stream] = event.streams;
      this.remoteStreams.set(key, stream);
      this.onStreamAdded(examineeId, streamType, stream);
    };

    this.peerConnections.set(key, pc);

    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      
      this.socket.emit('offer', {
        targetId: examineeId,
        offer,
        streamType
      });
    } catch (error) {
      console.error('创建Offer失败:', error);
      this.handleReconnection(examineeId, streamType);
    }
  }

  async handleAnswer(answer, senderId, streamType) {
    const key = this.getPeerKey(senderId, streamType);
    const pc = this.peerConnections.get(key);
    
    if (pc) {
      try {
        await pc.setRemoteDescription(new RTCSessionDescription(answer));
        this.reconnectAttempts.delete(key);
      } catch (error) {
        console.error('处理Answer失败:', error);
      }
    }
  }

  async handleIceCandidate(candidate, senderId, streamType) {
    const key = this.getPeerKey(senderId, streamType);
    const pc = this.peerConnections.get(key);
    
    if (pc && candidate) {
      try {
        await pc.addIceCandidate(new RTCIceCandidate(candidate));
      } catch (error) {
        console.error('添加ICE候选者失败:', error);
      }
    }
  }

  handleReconnection(examineeId, streamType) {
    const key = this.getPeerKey(examineeId, streamType);
    const attempts = this.reconnectAttempts.get(key) || 0;

    if (attempts >= this.maxReconnectAttempts) {
      console.error(`达到最大重连次数 ${this.maxReconnectAttempts}，停止重连`);
      this.onStreamRemoved(examineeId, streamType);
      this.closeConnection(examineeId, streamType);
      return;
    }

    this.reconnectAttempts.set(key, attempts + 1);
    console.log(`开始第 ${attempts + 1} 次重连: ${key}`);

    setTimeout(async () => {
      try {
        this.closeConnection(examineeId, streamType);
        await this.requestStream(examineeId, streamType);
      } catch (error) {
        console.error('重连失败:', error);
        this.handleReconnection(examineeId, streamType);
      }
    }, this.reconnectDelay * (attempts + 1));
  }

  stopStream(examineeId, streamType) {
    const key = this.getPeerKey(examineeId, streamType);
    this.closeConnection(examineeId, streamType);
    this.remoteStreams.delete(key);
    this.onStreamRemoved(examineeId, streamType);
  }

  closeConnection(examineeId, streamType) {
    const key = this.getPeerKey(examineeId, streamType);
    const pc = this.peerConnections.get(key);
    if (pc) {
      pc.close();
      this.peerConnections.delete(key);
    }
    this.reconnectAttempts.delete(key);
  }

  stopAllStreams(examineeId) {
    ['webcam', 'screen'].forEach(streamType => {
      this.stopStream(examineeId, streamType);
    });
  }

  getStream(examineeId, streamType) {
    const key = this.getPeerKey(examineeId, streamType);
    return this.remoteStreams.get(key);
  }

  hasActiveConnection(examineeId, streamType) {
    const key = this.getPeerKey(examineeId, streamType);
    const pc = this.peerConnections.get(key);
    return pc && (pc.connectionState === 'connected' || pc.connectionState === 'connecting');
  }

  destroy() {
    this.peerConnections.forEach((pc, key) => {
      pc.close();
    });
    this.peerConnections.clear();
    this.remoteStreams.clear();
    this.reconnectAttempts.clear();
  }
}

export default ProctorWebRTCManager;

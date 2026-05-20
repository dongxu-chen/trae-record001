class WebRTCManager {
  constructor(socket, config) {
    this.socket = socket;
    this.peerConnections = new Map();
    this.localStreams = new Map();
    this.reconnectAttempts = new Map();
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000;
    this.iceServers = config.iceServers || [
      { urls: 'stun:stun.l.google.com:19302' }
    ];
  }

  setLocalStream(streamType, stream) {
    this.localStreams.set(streamType, stream);
  }

  getLocalStream(streamType) {
    return this.localStreams.get(streamType);
  }

  createPeerConnection(peerId, streamType) {
    const key = `${peerId}-${streamType}`;
    
    if (this.peerConnections.has(key)) {
      return this.peerConnections.get(key);
    }

    const pc = new RTCPeerConnection({
      iceServers: this.iceServers,
      iceTransportPolicy: 'all',
      bundlePolicy: 'max-bundle',
      rtcpMuxPolicy: 'require'
    });

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        this.socket.emit('ice-candidate', {
          targetId: peerId,
          candidate: event.candidate
        });
      }
    };

    pc.oniceconnectionstatechange = () => {
      const state = pc.iceConnectionState;
      console.log(`ICE连接状态变化: ${state}`);
      
      this.socket.emit('connection-state-change', {
        targetId: peerId,
        state
      });

      if (state === 'failed' || state === 'disconnected') {
        this.handleReconnection(peerId, streamType);
      }
    };

    pc.onconnectionstatechange = () => {
      const state = pc.connectionState;
      console.log(`连接状态变化: ${state}`);
      
      if (state === 'failed') {
        this.handleReconnection(peerId, streamType);
      }
    };

    const localStream = this.localStreams.get(streamType);
    if (localStream) {
      localStream.getTracks().forEach(track => {
        pc.addTrack(track, localStream);
      });
    }

    this.peerConnections.set(key, pc);
    return pc;
  }

  async handleReconnection(peerId, streamType) {
    const key = `${peerId}-${streamType}`;
    const attempts = this.reconnectAttempts.get(key) || 0;

    if (attempts >= this.maxReconnectAttempts) {
      console.error(`达到最大重连次数 ${this.maxReconnectAttempts}，停止重连`);
      this.reconnectAttempts.delete(key);
      return;
    }

    this.reconnectAttempts.set(key, attempts + 1);
    console.log(`开始第 ${attempts + 1} 次重连...`);

    setTimeout(async () => {
      try {
        const pc = this.peerConnections.get(key);
        if (pc) {
          pc.close();
        }
        this.peerConnections.delete(key);

        this.socket.emit('reconnect-request', {
          targetId: peerId,
          streamType
        });
      } catch (error) {
        console.error('重连失败:', error);
        this.handleReconnection(peerId, streamType);
      }
    }, this.reconnectDelay * (attempts + 1));
  }

  async handleOffer(offer, senderId, streamType) {
    const pc = this.createPeerConnection(senderId, streamType);
    
    try {
      await pc.setRemoteDescription(new RTCSessionDescription(offer));
      
      const localStream = this.localStreams.get(streamType);
      if (localStream && pc.getSenders().length === 0) {
        localStream.getTracks().forEach(track => {
          pc.addTrack(track, localStream);
        });
      }

      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      this.socket.emit('answer', {
        targetId: senderId,
        answer,
        reconnectAttempt: this.reconnectAttempts.get(`${senderId}-${streamType}`) || 0
      });

      this.reconnectAttempts.delete(`${senderId}-${streamType}`);
    } catch (error) {
      console.error('处理Offer失败:', error);
      this.handleReconnection(senderId, streamType);
    }
  }

  async handleAnswer(answer, senderId, streamType) {
    const key = `${senderId}-${streamType}`;
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
    const key = `${senderId}-${streamType}`;
    const pc = this.peerConnections.get(key);
    
    if (pc && candidate) {
      try {
        await pc.addIceCandidate(new RTCIceCandidate(candidate));
      } catch (error) {
        console.error('添加ICE候选者失败:', error);
      }
    }
  }

  closeAllConnections() {
    this.peerConnections.forEach((pc) => {
      try {
        pc.close();
      } catch (e) {
        console.error('关闭连接失败:', e);
      }
    });
    this.peerConnections.clear();
    this.reconnectAttempts.clear();
  }

  closeConnection(peerId, streamType) {
    const key = `${peerId}-${streamType}`;
    const pc = this.peerConnections.get(key);
    if (pc) {
      pc.close();
      this.peerConnections.delete(key);
    }
    this.reconnectAttempts.delete(key);
  }
}

export default WebRTCManager;

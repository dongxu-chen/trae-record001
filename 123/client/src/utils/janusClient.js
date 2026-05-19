class JanusClient {
  constructor(config) {
    this.server = config.server || 'ws://localhost:8188';
    this.apiSecret = config.apiSecret || 'janus-exam-secret-2024';
    this.roomId = config.roomId || 1234567890;
    
    this.socket = null;
    this.sessionId = null;
    this.pluginHandle = null;
    this.privateId = null;
    this.connected = false;
    this.joined = false;
    
    this.transactionCallbacks = new Map();
    this.transactionCounter = 0;
    
    this.eventHandlers = new Map();
    
    this.localStreams = new Map();
    this.remoteStreams = new Map();
    this.publishers = new Map();
    
    this.iceServers = config.iceServers || [
      { urls: 'stun:stun.l.google.com:19302' }
    ];
  }

  on(event, handler) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event).push(handler);
  }

  off(event, handler) {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach(handler => handler(data));
    }
  }

  generateTransaction() {
    return `${Date.now()}-${++this.transactionCounter}`;
  }

  async connect() {
    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(this.server);
        
        this.socket.onopen = async () => {
          console.log('[Janus] WebSocket connected');
          this.connected = true;
          
          try {
            await this.createSession();
            await this.attachPlugin();
            resolve();
          } catch (error) {
            reject(error);
          }
        };

        this.socket.onmessage = (event) => {
          this.handleMessage(event.data);
        };

        this.socket.onerror = (error) => {
          console.error('[Janus] WebSocket error:', error);
          this.emit('error', error);
          reject(error);
        };

        this.socket.onclose = () => {
          console.log('[Janus] WebSocket disconnected');
          this.connected = false;
          this.joined = false;
          this.emit('disconnected');
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  handleMessage(data) {
    const message = JSON.parse(data);
    
    if (message.transaction) {
      const callback = this.transactionCallbacks.get(message.transaction);
      if (callback) {
        this.transactionCallbacks.delete(message.transaction);
        if (message.janus === 'error') {
          callback.reject(new Error(message.error?.reason || 'Janus error'));
        } else {
          callback.resolve(message);
        }
      }
    }

    if (message.janus === 'event') {
      this.handleEvent(message);
    } else if (message.janus === 'webrtcup') {
      this.emit('webrtcup', { handleId: message.sender });
    } else if (message.janus === 'hangup') {
      this.emit('hangup', { handleId: message.sender, reason: message.reason });
    } else if (message.janus === 'media') {
      this.emit('media', { handleId: message.sender, type: message.type, receiving: message.receiving });
    } else if (message.janus === 'slowlink') {
      this.emit('slowlink', { handleId: message.sender, uplink: message.uplink, lost: message.lost });
    }
  }

  handleEvent(message) {
    const plugindata = message.plugindata?.data;
    if (!plugindata) return;

    if (plugindata.videoroom === 'joined') {
      this.privateId = plugindata.private_id;
      this.joined = true;
      this.emit('joined', {
        room: plugindata.room,
        privateId: this.privateId,
        publishers: plugindata.publishers || []
      });
      
      if (plugindata.publishers) {
        plugindata.publishers.forEach(pub => {
          this.publishers.set(pub.id, pub);
        });
      }
    } else if (plugindata.videoroom === 'event') {
      if (plugindata.publishers) {
        plugindata.publishers.forEach(pub => {
          this.publishers.set(pub.id, pub);
        });
        this.emit('publishers', plugindata.publishers);
      }
      
      if (plugindata.leaving) {
        const leavingId = plugindata.leaving;
        this.publishers.delete(leavingId);
        this.remoteStreams.delete(leavingId);
        this.emit('publisherLeft', leavingId);
      }
      
      if (plugindata['configured']) {
        this.emit('configured', plugindata);
      }
    } else if (plugindata.videoroom === 'attached') {
      this.emit('attached', {
        room: plugindata.room,
        feedId: plugindata.id
      });
    }
  }

  send(message) {
    return new Promise((resolve, reject) => {
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      const transaction = this.generateTransaction();
      message.transaction = transaction;
      message.apisecret = this.apiSecret;

      this.transactionCallbacks.set(transaction, { resolve, reject });
      this.socket.send(JSON.stringify(message));

      setTimeout(() => {
        if (this.transactionCallbacks.has(transaction)) {
          this.transactionCallbacks.delete(transaction);
          reject(new Error('Request timeout'));
        }
      }, 30000);
    });
  }

  async createSession() {
    const response = await this.send({
      janus: 'create'
    });
    this.sessionId = response.data.id;
    console.log('[Janus] Session created:', this.sessionId);
    return this.sessionId;
  }

  async attachPlugin() {
    const response = await this.send({
      janus: 'attach',
      session_id: this.sessionId,
      plugin: 'janus.plugin.videoroom'
    });
    this.pluginHandle = response.data.id;
    console.log('[Janus] Plugin attached:', this.pluginHandle);
    return this.pluginHandle;
  }

  async joinRoom(userId, displayName, isPublisher = true) {
    const response = await this.send({
      janus: 'message',
      session_id: this.sessionId,
      handle_id: this.pluginHandle,
      body: {
        request: 'join',
        room: this.roomId,
        ptype: isPublisher ? 'publisher' : 'subscriber',
        id: userId,
        display: displayName
      }
    });
    return response;
  }

  async publish(stream, options = {}) {
    const pc = new RTCPeerConnection({
      iceServers: this.iceServers
    });

    stream.getTracks().forEach(track => {
      pc.addTrack(track, stream);
    });

    const offer = await pc.createOffer({
      offerToReceiveAudio: false,
      offerToReceiveVideo: false
    });
    await pc.setLocalDescription(offer);

    const jsep = {
      type: offer.type,
      sdp: offer.sdp
    };

    const response = await this.send({
      janus: 'message',
      session_id: this.sessionId,
      handle_id: this.pluginHandle,
      body: {
        request: 'configure',
        audio: options.audio !== false,
        video: options.video !== false,
        record: options.record !== false,
        filename: options.filename || `exam_${Date.now()}`
      },
      jsep
    });

    if (response.jsep) {
      await pc.setRemoteDescription(new RTCSessionDescription(response.jsep));
    }

    const streamId = options.streamId || `publisher_${Date.now()}`;
    this.localStreams.set(streamId, { pc, stream });

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        this.send({
          janus: 'trickle',
          session_id: this.sessionId,
          handle_id: this.pluginHandle,
          candidate: event.candidate
        }).catch(console.error);
      }
    };

    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'connected') {
        this.emit('streamPublished', { streamId, pc });
      }
    };

    return { streamId, pc };
  }

  async subscribe(publisherId) {
    const subscriberHandle = await this.createSubscriberHandle();
    
    const response = await this.send({
      janus: 'message',
      session_id: this.sessionId,
      handle_id: subscriberHandle,
      body: {
        request: 'join',
        room: this.roomId,
        ptype: 'subscriber',
        feed: publisherId,
        private_id: this.privateId
      }
    });

    if (response.jsep) {
      const pc = await this.handleSubscriberJsep(subscriberHandle, response.jsep);
      
      const streamInfo = {
        handleId: subscriberHandle,
        pc,
        publisherId
      };
      
      this.remoteStreams.set(publisherId, streamInfo);
      
      return { publisherId, pc, handleId: subscriberHandle };
    }
    
    throw new Error('Failed to subscribe');
  }

  async createSubscriberHandle() {
    const response = await this.send({
      janus: 'attach',
      session_id: this.sessionId,
      plugin: 'janus.plugin.videoroom'
    });
    return response.data.id;
  }

  async handleSubscriberJsep(handleId, jsep) {
    const pc = new RTCPeerConnection({
      iceServers: this.iceServers
    });

    await pc.setRemoteDescription(new RTCSessionDescription(jsep));
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);

    await this.send({
      janus: 'message',
      session_id: this.sessionId,
      handle_id: handleId,
      body: {
        request: 'start',
        room: this.roomId
      },
      jsep: {
        type: answer.type,
        sdp: answer.sdp
      }
    });

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        this.send({
          janus: 'trickle',
          session_id: this.sessionId,
          handle_id: handleId,
          candidate: event.candidate
        }).catch(console.error);
      }
    };

    pc.ontrack = (event) => {
      this.emit('track', {
        handleId,
        track: event.track,
        stream: event.streams[0]
      });
    };

    return pc;
  }

  async unsubscribe(publisherId) {
    const streamInfo = this.remoteStreams.get(publisherId);
    if (streamInfo) {
      streamInfo.pc.close();
      this.remoteStreams.delete(publisherId);
      
      await this.send({
        janus: 'hangup',
        session_id: this.sessionId,
        handle_id: streamInfo.handleId
      }).catch(() => {});
      
      await this.send({
        janus: 'detach',
        session_id: this.sessionId,
        handle_id: streamInfo.handleId
      }).catch(() => {});
    }
  }

  async listPublishers() {
    const response = await this.send({
      janus: 'message',
      session_id: this.sessionId,
      handle_id: this.pluginHandle,
      body: {
        request: 'listparticipants',
        room: this.roomId
      }
    });
    return response.plugindata?.data?.participants || [];
  }

  async startRecording(filename) {
    return await this.send({
      janus: 'message',
      session_id: this.sessionId,
      handle_id: this.pluginHandle,
      body: {
        request: 'configure',
        record: true,
        filename: filename || `recording_${Date.now()}`
      }
    });
  }

  async stopRecording() {
    return await this.send({
      janus: 'message',
      session_id: this.sessionId,
      handle_id: this.pluginHandle,
      body: {
        request: 'configure',
        record: false
      }
    });
  }

  async leave() {
    for (const [streamId, info] of this.localStreams) {
      info.pc.close();
      if (info.stream) {
        info.stream.getTracks().forEach(track => track.stop());
      }
    }
    this.localStreams.clear();

    for (const [publisherId] of this.remoteStreams) {
      await this.unsubscribe(publisherId);
    }

    if (this.pluginHandle) {
      await this.send({
        janus: 'hangup',
        session_id: this.sessionId,
        handle_id: this.pluginHandle
      }).catch(() => {});

      await this.send({
        janus: 'detach',
        session_id: this.sessionId,
        handle_id: this.pluginHandle
      }).catch(() => {});
    }

    this.joined = false;
    this.emit('left');
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
    }
    this.connected = false;
    this.joined = false;
  }

  destroy() {
    this.leave();
    this.disconnect();
    this.eventHandlers.clear();
    this.transactionCallbacks.clear();
  }
}

export default JanusClient;

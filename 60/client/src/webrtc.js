import { io } from 'socket.io-client';
import {
  exportPublicKey,
  importPublicKey,
  deriveSharedKey,
  encryptMessage,
  decryptMessage,
  generateKeyFingerprint,
  verifyKeyExchange,
  encryptForOffline,
  decryptFromOffline,
  encryptHistoryMessage,
  decryptHistoryMessage,
  deriveRoomKey,
  exportPrivateKey,
  importPrivateKey
} from './crypto.js';

const ICE_CONFIG = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
    { urls: 'stun:stun2.l.google.com:19302' },
    { urls: 'stun:stun3.l.google.com:19302' },
    { urls: 'stun:stun4.l.google.com:19302' }
  ]
};

const ICE_TIMEOUT = 30000;
const TYPING_INTERVAL = 3000;

class WebRTCChat {
  constructor(signalingServerUrl) {
    this.socket = io(signalingServerUrl);
    this.connections = new Map();
    this.dataChannels = new Map();
    this.sharedKeys = new Map();
    this.myKeyPair = null;
    this.myPublicKeyExported = null;
    this.myKeyFingerprint = null;
    this.roomId = null;
    this.peerPublicKeys = new Map();
    this.peerFingerprints = new Map();
    this.verifiedPeers = new Set();
    this.typingPeers = new Set();
    this.roomKey = null;
    this.decryptWorker = null;
    this.onMessage = null;
    this.onPeerConnected = null;
    this.onPeerDisconnected = null;
    this.onPeerVerified = null;
    this.onTyping = null;
    this.onHistoryLoaded = null;
    this.onOfflineMessages = null;
    this.onDecryptProgress = null;
    this.setupSocketListeners();
    this.lastTypingTime = 0;
  }

  async initialize() {
    const { generateKeyPair } = await import('./crypto.js');
    this.myKeyPair = await generateKeyPair();
    this.myPublicKeyExported = await exportPublicKey(this.myKeyPair.publicKey);
    this.myKeyFingerprint = await generateKeyFingerprint(this.myPublicKeyExported);
  }

  setupSocketListeners() {
    this.socket.on('room-users', async (users) => {
      const otherUsers = users.filter(id => id !== this.socket.id);
      for (const userId of otherUsers) {
        await this.createConnection(userId, true);
      }
    });

    this.socket.on('user-joined', async (userId) => {
      await this.createConnection(userId, false);
    });

    this.socket.on('user-left', (userId) => {
      this.typingPeers.delete(userId);
      if (this.onTyping) {
        this.onTyping(Array.from(this.typingPeers));
      }
      this.closeConnection(userId);
      if (this.onPeerDisconnected) {
        this.onPeerDisconnected(userId);
      }
    });

    this.socket.on('typing', (data) => {
      const { userId, isTyping } = data;
      if (isTyping) {
        this.typingPeers.add(userId);
      } else {
        this.typingPeers.delete(userId);
      }
      if (this.onTyping) {
        this.onTyping(Array.from(this.typingPeers));
      }
    });

    this.socket.on('offline-messages', async (data) => {
      const { messages } = data;
      if (messages && messages.length > 0) {
        const decrypted = await this.processOfflineMessages(messages);
        if (this.onOfflineMessages) {
          this.onOfflineMessages(decrypted);
        }
      }
    });

    this.socket.on('offer', async (data) => {
      await this.handleOffer(data.from, data.offer);
    });

    this.socket.on('answer', async (data) => {
      await this.handleAnswer(data.from, data.answer);
    });

    this.socket.on('ice-candidate', async (data) => {
      await this.handleIceCandidate(data.from, data.candidate);
    });

    this.socket.on('key-verify', async (data) => {
      await this.handleKeyVerify(data.from, data);
    });

    this.socket.on('key-confirm', async (data) => {
      await this.handleKeyConfirm(data.from, data);
    });
  }

  async joinRoom(roomId) {
    this.roomId = roomId;
    this.socket.emit('join-room', roomId);
    
    setTimeout(() => {
      this.socket.emit('request-offline-messages');
    }, 1000);
  }

  sendTyping(isTyping) {
    const now = Date.now();
    if (!isTyping || now - this.lastTypingTime > TYPING_INTERVAL) {
      this.socket.emit('typing', { isTyping });
      this.lastTypingTime = now;
    }
  }

  async loadHistory(signalingServerBase) {
    try {
      const response = await fetch(`${signalingServerBase}/api/history/${this.roomId}`);
      const result = await response.json();
      
      if (!result.success || !result.messages || result.messages.length === 0) {
        return [];
      }
      
      if (!this.roomKey) {
        await this.deriveRoomKeyFromPeers();
      }
      
      if (!this.roomKey) {
        return [];
      }
      
      const decrypted = await this.decryptHistoryMessages(result.messages);
      
      if (this.onHistoryLoaded) {
        this.onHistoryLoaded(decrypted);
      }
      
      return decrypted;
    } catch (error) {
      console.error('Error loading history:', error);
      return [];
    }
  }

  async saveMessageToHistory(message, signalingServerBase) {
    if (!this.roomKey) {
      await this.deriveRoomKeyFromPeers();
    }
    
    if (!this.roomKey) {
      return null;
    }
    
    try {
      const encrypted = await encryptHistoryMessage(message, this.roomKey);
      
      const response = await fetch(`${signalingServerBase}/api/history/${this.roomId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(encrypted)
      });
      
      return response.json();
    } catch (error) {
      console.error('Error saving to history:', error);
      return null;
    }
  }

  async deriveRoomKeyFromPeers() {
    const sharedKeys = Array.from(this.sharedKeys.values());
    if (sharedKeys.length === 0) {
      return null;
    }
    
    try {
      this.roomKey = await deriveRoomKey(sharedKeys);
      return this.roomKey;
    } catch (error) {
      console.error('Error deriving room key:', error);
      return null;
    }
  }

  async decryptHistoryMessages(encryptedMessages) {
    if (!this.roomKey) {
      return [];
    }
    
    const results = [];
    
    for (const msg of encryptedMessages) {
      try {
        const decrypted = await decryptHistoryMessage(msg, this.roomKey);
        results.push({
          ...decrypted,
          fromHistory: true,
          storedAt: msg.storedAt
        });
      } catch (error) {
        console.warn('Failed to decrypt history message:', error);
      }
    }
    
    return results.sort((a, b) => (a.storedAt || a.timestamp) - (b.storedAt || b.timestamp));
  }

  async processOfflineMessages(offlineMessages) {
    const results = [];
    
    for (const msg of offlineMessages) {
      try {
        const decrypted = await decryptFromOffline(msg.encryptedMessage, this.myKeyPair.privateKey);
        const messageData = JSON.parse(decrypted);
        results.push({
          ...messageData,
          fromOffline: true,
          storedAt: msg.timestamp
        });
      } catch (error) {
        console.warn('Failed to decrypt offline message:', error);
      }
    }
    
    return results.sort((a, b) => (a.storedAt || a.timestamp) - (b.storedAt || b.timestamp));
  }

  async sendOfflineMessage(targetUserId, message, anonymousId) {
    const peerPublicKey = this.peerPublicKeys.get(targetUserId);
    if (!peerPublicKey) {
      console.error('No public key for offline message target:', targetUserId);
      return false;
    }
    
    try {
      const peerPublicKeyString = await exportPublicKey(peerPublicKey);
      const messageData = {
        anonymousId,
        text: message,
        timestamp: Date.now(),
        isOffline: true
      };
      
      const encrypted = await encryptForOffline(JSON.stringify(messageData), peerPublicKeyString);
      
      this.socket.emit('offline-message', {
        targetUserId,
        encryptedMessage: encrypted
      });
      
      return true;
    } catch (error) {
      console.error('Error sending offline message:', error);
      return false;
    }
  }

  async createConnection(peerId, isInitiator) {
    if (this.connections.has(peerId)) {
      return;
    }

    const pc = new RTCPeerConnection(ICE_CONFIG);
    this.connections.set(peerId, pc);

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        this.socket.emit('ice-candidate', {
          to: peerId,
          candidate: event.candidate
        });
      }
    };

    pc.onicegatheringstatechange = () => {
      console.log('ICE gathering state:', pc.iceGatheringState, 'for peer:', peerId);
    };

    pc.oniceconnectionstatechange = () => {
      console.log('ICE connection state:', pc.iceConnectionState, 'for peer:', peerId);
      if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
        console.log('ICE connected for peer:', peerId);
      } else if (pc.iceConnectionState === 'failed') {
        console.warn('ICE connection failed for peer:', peerId);
        this.attemptReconnect(peerId, isInitiator);
      } else if (pc.iceConnectionState === 'disconnected') {
        console.warn('ICE disconnected for peer:', peerId);
      }
    };

    pc.onsignalingstatechange = () => {
      console.log('Signaling state:', pc.signalingState, 'for peer:', peerId);
    };

    if (isInitiator) {
      const dc = pc.createDataChannel('chat', {
        ordered: true,
        negotiated: false
      });
      this.setupDataChannel(dc, peerId);
      
      await this.createAndSendOffer(peerId, pc);
    } else {
      pc.ondatachannel = (event) => {
        this.setupDataChannel(event.channel, peerId);
      };
    }
  }

  async createAndSendOffer(peerId, pc) {
    try {
      const offer = await pc.createOffer({
        iceRestart: false,
        offerToReceiveAudio: false,
        offerToReceiveVideo: false
      });
      await pc.setLocalDescription(offer);

      await this.waitForIceGatheringComplete(pc, peerId);

      this.socket.emit('offer', {
        to: peerId,
        offer: {
          type: pc.localDescription.type,
          sdp: pc.localDescription.sdp,
          publicKey: this.myPublicKeyExported,
          fingerprint: this.myKeyFingerprint
        }
      });
    } catch (error) {
      console.error('Error creating offer for peer', peerId, ':', error);
    }
  }

  async waitForIceGatheringComplete(pc, peerId) {
    if (pc.iceGatheringState === 'complete') {
      return;
    }

    return new Promise((resolve) => {
      const timeoutId = setTimeout(() => {
        console.warn('ICE gathering timeout for peer:', peerId);
        cleanup();
        resolve();
      }, ICE_TIMEOUT);

      const checkState = () => {
        if (pc.iceGatheringState === 'complete') {
          cleanup();
          resolve();
        }
      };

      const onIceGatheringStateChange = () => {
        checkState();
      };

      const cleanup = () => {
        clearTimeout(timeoutId);
        pc.removeEventListener('icegatheringstatechange', onIceGatheringStateChange);
      };

      pc.addEventListener('icegatheringstatechange', onIceGatheringStateChange);
      checkState();
    });
  }

  async attemptReconnect(peerId, isInitiator) {
    console.log('Attempting to reconnect to peer:', peerId);
    this.closeConnection(peerId);
    
    setTimeout(async () => {
      if (this.socket.connected) {
        await this.createConnection(peerId, isInitiator);
      }
    }, 3000);
  }

  async handleOffer(peerId, offer) {
    const pc = this.connections.get(peerId) || new RTCPeerConnection(ICE_CONFIG);
    if (!this.connections.has(peerId)) {
      this.connections.set(peerId, pc);
      pc.onicecandidate = (event) => {
        if (event.candidate) {
          this.socket.emit('ice-candidate', {
            to: peerId,
            candidate: event.candidate
          });
        }
      };
      pc.oniceconnectionstatechange = () => {
        if (pc.iceConnectionState === 'failed') {
          this.attemptReconnect(peerId, false);
        }
      };
      pc.ondatachannel = (event) => {
        this.setupDataChannel(event.channel, peerId);
      };
    }

    if (offer.publicKey && offer.fingerprint) {
      const isValid = await verifyKeyExchange(offer.publicKey, offer.fingerprint);
      if (!isValid) {
        console.error('Key verification failed for peer:', peerId);
        return;
      }

      const peerPublicKey = await importPublicKey(offer.publicKey);
      this.peerPublicKeys.set(peerId, peerPublicKey);
      this.peerFingerprints.set(peerId, offer.fingerprint);
      
      const sharedKey = await deriveSharedKey(this.myKeyPair.privateKey, peerPublicKey);
      this.sharedKeys.set(peerId, sharedKey);
    }

    try {
      await pc.setRemoteDescription(new RTCSessionDescription({
        type: offer.type,
        sdp: offer.sdp
      }));

      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);

      await this.waitForIceGatheringComplete(pc, peerId);

      this.socket.emit('answer', {
        to: peerId,
        answer: {
          type: pc.localDescription.type,
          sdp: pc.localDescription.sdp,
          publicKey: this.myPublicKeyExported,
          fingerprint: this.myKeyFingerprint
        }
      });
    } catch (error) {
      console.error('Error handling offer from peer', peerId, ':', error);
    }
  }

  async handleAnswer(peerId, answer) {
    const pc = this.connections.get(peerId);
    if (!pc) return;

    if (answer.publicKey && answer.fingerprint) {
      const isValid = await verifyKeyExchange(answer.publicKey, answer.fingerprint);
      if (!isValid) {
        console.error('Key verification failed for peer:', peerId);
        return;
      }

      const peerPublicKey = await importPublicKey(answer.publicKey);
      this.peerPublicKeys.set(peerId, peerPublicKey);
      this.peerFingerprints.set(peerId, answer.fingerprint);
      
      const sharedKey = await deriveSharedKey(this.myKeyPair.privateKey, peerPublicKey);
      this.sharedKeys.set(peerId, sharedKey);
      
      this.verifiedPeers.add(peerId);
      if (this.onPeerVerified) {
        this.onPeerVerified(peerId);
      }
    }

    try {
      await pc.setRemoteDescription(new RTCSessionDescription({
        type: answer.type,
        sdp: answer.sdp
      }));
    } catch (error) {
      console.error('Error handling answer from peer', peerId, ':', error);
    }
  }

  async handleIceCandidate(peerId, candidate) {
    const pc = this.connections.get(peerId);
    if (!pc || !candidate) return;

    try {
      await pc.addIceCandidate(new RTCIceCandidate(candidate));
    } catch (error) {
      console.warn('Error adding ICE candidate for peer', peerId, ':', error);
    }
  }

  async handleKeyVerify(peerId, data) {
    if (!data.fingerprint) return;
    
    const sharedKey = this.sharedKeys.get(peerId);
    if (!sharedKey) return;

    this.socket.emit('key-confirm', {
      to: peerId,
      fingerprint: this.myKeyFingerprint
    });
  }

  async handleKeyConfirm(peerId, data) {
    if (!data.fingerprint) return;
    
    const storedFingerprint = this.peerFingerprints.get(peerId);
    if (storedFingerprint === data.fingerprint) {
      this.verifiedPeers.add(peerId);
      if (this.onPeerVerified) {
        this.onPeerVerified(peerId);
      }
    }
  }

  setupDataChannel(dc, peerId) {
    dc.onopen = () => {
      console.log('Data channel opened for peer:', peerId);
      this.dataChannels.set(peerId, dc);
      if (this.onPeerConnected) {
        this.onPeerConnected(peerId);
      }
    };

    dc.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'chat') {
          const sharedKey = this.sharedKeys.get(peerId);
          if (sharedKey && this.verifiedPeers.has(peerId)) {
            const decrypted = await decryptMessage(data.encrypted, sharedKey);
            const messageData = JSON.parse(decrypted);
            if (this.onMessage) {
              this.onMessage({
                from: peerId,
                ...messageData
              });
            }
          }
        }
      } catch (e) {
        console.error('Error processing message:', e);
      }
    };

    dc.onclose = () => {
      console.log('Data channel closed for peer:', peerId);
      this.dataChannels.delete(peerId);
      this.typingPeers.delete(peerId);
      if (this.onTyping) {
        this.onTyping(Array.from(this.typingPeers));
      }
      if (this.onPeerDisconnected) {
        this.onPeerDisconnected(peerId);
      }
    };

    dc.onerror = (error) => {
      console.error('Data channel error for peer', peerId, ':', error);
    };
  }

  async sendMessage(message, anonymousId) {
    const peers = Array.from(this.dataChannels.entries());
    if (peers.length === 0) return;

    const messageData = {
      anonymousId,
      text: message,
      timestamp: Date.now()
    };

    const messageJson = JSON.stringify(messageData);

    for (const [peerId, dc] of peers) {
      if (dc.readyState === 'open' && this.verifiedPeers.has(peerId)) {
        const sharedKey = this.sharedKeys.get(peerId);
        if (sharedKey) {
          try {
            const encrypted = await encryptMessage(messageJson, sharedKey);
            dc.send(JSON.stringify({
              type: 'chat',
              encrypted
            }));
          } catch (error) {
            console.error('Error sending message to peer', peerId, ':', error);
          }
        }
      }
    }
  }

  getSocketId() {
    return this.socket.id;
  }

  getTypingPeers() {
    return Array.from(this.typingPeers);
  }

  getConnectedPeers() {
    return Array.from(this.dataChannels.keys());
  }

  closeConnection(peerId) {
    const pc = this.connections.get(peerId);
    const dc = this.dataChannels.get(peerId);

    try {
      if (dc) dc.close();
      if (pc) pc.close();
    } catch (error) {
      console.warn('Error closing connection for peer', peerId, ':', error);
    }

    this.connections.delete(peerId);
    this.dataChannels.delete(peerId);
    this.sharedKeys.delete(peerId);
    this.peerPublicKeys.delete(peerId);
    this.peerFingerprints.delete(peerId);
    this.verifiedPeers.delete(peerId);
    this.typingPeers.delete(peerId);
  }

  disconnect() {
    for (const peerId of this.connections.keys()) {
      this.closeConnection(peerId);
    }
    this.roomKey = null;
    this.typingPeers.clear();
    if (this.decryptWorker) {
      this.decryptWorker.terminate();
      this.decryptWorker = null;
    }
    this.socket.disconnect();
  }
}

export default WebRTCChat;

class WebRTCManager {
    constructor() {
        this.peerConnection = null;
        this.localStream = null;
        this.isConnected = false;
        this.iceServers = [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ];
    }

    async startLocalVideo(videoElement) {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                },
                audio: false
            });
            
            if (videoElement) {
                videoElement.srcObject = this.localStream;
            }
            
            return true;
        } catch (error) {
            console.error('Error accessing camera:', error);
            throw error;
        }
    }

    async startScreenShare(videoElement) {
        try {
            this.localStream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    cursor: 'always'
                },
                audio: false
            });
            
            if (videoElement) {
                videoElement.srcObject = this.localStream;
            }
            
            this.localStream.getVideoTracks()[0].onended = () => {
                console.log('Screen share stopped by user');
                this.stopLocalStream();
            };
            
            return true;
        } catch (error) {
            console.error('Error starting screen share:', error);
            throw error;
        }
    }

    stopLocalStream() {
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
    }

    async createPeerConnection(onIceCandidate, onTrack) {
        this.peerConnection = new RTCPeerConnection({
            iceServers: this.iceServers
        });

        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });
        }

        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate && onIceCandidate) {
                onIceCandidate(event.candidate);
            }
        };

        this.peerConnection.oniceconnectionstatechange = () => {
            console.log('ICE connection state:', this.peerConnection.iceConnectionState);
            this.isConnected = this.peerConnection.iceConnectionState === 'connected' || 
                              this.peerConnection.iceConnectionState === 'completed';
        };

        this.peerConnection.ontrack = (event) => {
            if (onTrack) {
                onTrack(event.streams[0]);
            }
        };

        return this.peerConnection;
    }

    async createOffer() {
        if (!this.peerConnection) {
            throw new Error('Peer connection not initialized');
        }
        
        const offer = await this.peerConnection.createOffer();
        await this.peerConnection.setLocalDescription(offer);
        return offer;
    }

    async handleAnswer(answer) {
        if (!this.peerConnection) {
            throw new Error('Peer connection not initialized');
        }
        
        await this.peerConnection.setRemoteDescription(
            new RTCSessionDescription(answer)
        );
    }

    async handleOffer(offer) {
        if (!this.peerConnection) {
            throw new Error('Peer connection not initialized');
        }
        
        await this.peerConnection.setRemoteDescription(
            new RTCSessionDescription(offer)
        );
        
        const answer = await this.peerConnection.createAnswer();
        await this.peerConnection.setLocalDescription(answer);
        return answer;
    }

    async addIceCandidate(candidate) {
        if (!this.peerConnection) {
            throw new Error('Peer connection not initialized');
        }
        
        await this.peerConnection.addIceCandidate(
            new RTCIceCandidate(candidate)
        );
    }

    close() {
        this.stopLocalStream();
        
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        
        this.isConnected = false;
    }

    captureFrame(videoElement) {
        if (!videoElement) return null;
        
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth || 640;
        canvas.height = videoElement.videoHeight || 480;
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        
        return canvas.toDataURL('image/jpeg', 0.8);
    }
}

class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        
        this.onMessage = null;
        this.onOpen = null;
        this.onClose = null;
        this.onError = null;
    }

    connect() {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(this.url);
                
                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.reconnectAttempts = 0;
                    if (this.onOpen) this.onOpen();
                    resolve();
                };
                
                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        if (this.onMessage) this.onMessage(data);
                    } catch (e) {
                        console.error('Error parsing WebSocket message:', e);
                    }
                };
                
                this.ws.onclose = (event) => {
                    console.log('WebSocket closed:', event.code, event.reason);
                    if (this.onClose) this.onClose(event);
                    
                    if (this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.reconnectAttempts++;
                        setTimeout(() => {
                            console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
                            this.connect();
                        }, this.reconnectDelay * this.reconnectAttempts);
                    }
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    if (this.onError) this.onError(error);
                    reject(error);
                };
                
            } catch (error) {
                console.error('Error connecting WebSocket:', error);
                reject(error);
            }
        });
    }

    send(type, data = {}) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type, data }));
            return true;
        }
        console.warn('WebSocket not connected, message not sent');
        return false;
    }

    close() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

window.WebRTCManager = WebRTCManager;
window.WebSocketClient = WebSocketClient;

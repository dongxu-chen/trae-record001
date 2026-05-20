class StreamManager {
    constructor() {
        this.mediaStream = null;
        this.peerConnection = null;
        this.isStreaming = false;
        this.streamKey = '';
        this.canvasStream = null;
        this.audioStream = null;
        
        this.onStreamStateChange = null;
        this.onViewerCountChange = null;
        this.viewerCount = 0;
        
        this.iceServers = [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ];
    }
    
    async startStream(canvas, streamKey = '') {
        if (this.isStreaming) {
            this.log('已经在推流中');
            return false;
        }
        
        try {
            this.streamKey = streamKey;
            this.log('开始初始化推流...');
            
            this.canvasStream = canvas.captureStream(30);
            
            try {
                this.audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this.audioStream.getAudioTracks().forEach(track => {
                    this.canvasStream.addTrack(track);
                });
                this.log('音频轨道已添加');
            } catch (e) {
                this.log('无音频设备，仅推视频流');
            }
            
            this.mediaStream = this.canvasStream;
            
            this.setupPeerConnection();
            
            this.isStreaming = true;
            
            if (this.onStreamStateChange) {
                this.onStreamStateChange(true);
            }
            
            this.log('推流已启动');
            return true;
        } catch (error) {
            this.log(`推流启动失败: ${error.message}`);
            console.error(error);
            return false;
        }
    }
    
    setupPeerConnection() {
        this.peerConnection = new RTCPeerConnection({
            iceServers: this.iceServers
        });
        
        this.mediaStream.getTracks().forEach(track => {
            this.peerConnection.addTrack(track, this.mediaStream);
        });
        
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.log(`ICE候选: ${event.candidate.candidate.substring(0, 50)}...`);
            }
        };
        
        this.peerConnection.onconnectionstatechange = () => {
            this.log(`连接状态: ${this.peerConnection.connectionState}`);
        };
        
        this.peerConnection.onicegatheringstatechange = () => {
            this.log(`ICE收集状态: ${this.peerConnection.iceGatheringState}`);
        };
        
        this.createOffer();
    }
    
    async createOffer() {
        try {
            const offer = await this.peerConnection.createOffer({
                offerToReceiveAudio: false,
                offerToReceiveVideo: false
            });
            
            await this.peerConnection.setLocalDescription(offer);
            
            this.log(`SDP Offer已创建 (${offer.sdp.length} 字符)`);
            
            this.simulateViewerCount();
        } catch (error) {
            this.log(`创建Offer失败: ${error.message}`);
        }
    }
    
    simulateViewerCount() {
        setInterval(() => {
            if (this.isStreaming) {
                this.viewerCount = Math.floor(Math.random() * 50) + 10;
                if (this.onViewerCountChange) {
                    this.onViewerCountChange(this.viewerCount);
                }
            }
        }, 5000);
    }
    
    stopStream() {
        if (!this.isStreaming) {
            this.log('当前没有推流');
            return;
        }
        
        try {
            if (this.peerConnection) {
                this.peerConnection.close();
                this.peerConnection = null;
            }
            
            if (this.mediaStream) {
                this.mediaStream.getTracks().forEach(track => track.stop());
                this.mediaStream = null;
            }
            
            this.isStreaming = false;
            
            if (this.onStreamStateChange) {
                this.onStreamStateChange(false);
            }
            
            this.log('推流已停止');
        } catch (error) {
            this.log(`停止推流失败: ${error.message}`);
        }
    }
    
    getStream() {
        return this.mediaStream;
    }
    
    getStreamStats() {
        if (!this.peerConnection) return null;
        return this.peerConnection.getStats();
    }
    
    setStreamKey(key) {
        this.streamKey = key;
    }
    
    getViewerCount() {
        return this.viewerCount;
    }
    
    isStreamingNow() {
        return this.isStreaming;
    }
    
    async toggleAudio(enabled) {
        if (!this.audioStream) return;
        
        this.audioStream.getAudioTracks().forEach(track => {
            track.enabled = enabled;
        });
        
        this.log(enabled ? '音频已开启' : '音频已静音');
    }
    
    async toggleVideo(enabled) {
        if (!this.canvasStream) return;
        
        this.canvasStream.getVideoTracks().forEach(track => {
            track.enabled = enabled;
        });
        
        this.log(enabled ? '视频已开启' : '视频已暂停');
    }
    
    getPreviewVideo() {
        const video = document.createElement('video');
        video.srcObject = this.mediaStream;
        video.autoplay = true;
        video.muted = true;
        return video;
    }
    
    log(message) {
        const debugInfo = document.getElementById('debugInfo');
        if (debugInfo) {
            const timestamp = new Date().toLocaleTimeString();
            const newContent = `<div style="color: #FF6B6B">[${timestamp}] ${message}</div>` + debugInfo.innerHTML;
            debugInfo.innerHTML = newContent.substring(0, 3000);
        }
    }
}
export class VideoRecorder {
  constructor() {
    this.mediaRecorder = null;
    this.chunks = [];
    this.isRecording = false;
    this.isPaused = false;
    
    this.recordingCanvas = null;
    this.recordingContext = null;
    this.captureStream = null;
    
    this.audioStream = null;
    this.combinedStream = null;
    
    this.startTime = 0;
    this.pauseTime = 0;
    this.totalPausedTime = 0;
    
    this.onStart = null;
    this.onStop = null;
    this.onPause = null;
    this.onResume = null;
    this.onError = null;
    this.onDataAvailable = null;
    
    this.mimeType = 'video/webm;codecs=vp9';
    this.fps = 30;
    this.videoBitrate = 5000000;
    this.audioBitrate = 128000;
    
    this.includeAudio = false;
    this.includeMicAudio = false;
  }

  init(canvas, options = {}) {
    this.recordingCanvas = canvas;
    this.recordingContext = canvas.getContext('2d');
    
    if (options.fps !== undefined) this.fps = options.fps;
    if (options.videoBitrate !== undefined) this.videoBitrate = options.videoBitrate;
    if (options.audioBitrate !== undefined) this.audioBitrate = options.audioBitrate;
    if (options.mimeType !== undefined) this.mimeType = options.mimeType;
    if (options.includeAudio !== undefined) this.includeAudio = options.includeAudio;
    if (options.includeMicAudio !== undefined) this.includeMicAudio = options.includeMicAudio;
    
    if (!this._isMimeTypeSupported(this.mimeType)) {
      if (this._isMimeTypeSupported('video/webm;codecs=vp8')) {
        this.mimeType = 'video/webm;codecs=vp8';
      } else if (this._isMimeTypeSupported('video/webm')) {
        this.mimeType = 'video/webm';
      } else {
        throw new Error('No supported video codec found');
      }
    }
  }

  _isMimeTypeSupported(mimeType) {
    try {
      return MediaRecorder.isTypeSupported(mimeType);
    } catch (e) {
      return false;
    }
  }

  async start() {
    if (this.isRecording) {
      console.warn('Already recording');
      return false;
    }
    
    try {
      this.captureStream = this.recordingCanvas.captureStream(this.fps);
      
      this.combinedStream = new MediaStream([...this.captureStream.getVideoTracks()]);
      
      if (this.includeMicAudio) {
        this.audioStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });
        
        this.combinedStream.addTrack(this.audioStream.getAudioTracks()[0]);
      }
      
      this.chunks = [];
      this.mediaRecorder = new MediaRecorder(this.combinedStream, {
        mimeType: this.mimeType,
        videoBitsPerSecond: this.videoBitrate,
        audioBitsPerSecond: this.audioBitrate
      });
      
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.chunks.push(event.data);
          if (this.onDataAvailable) {
            this.onDataAvailable(event.data);
          }
        }
      };
      
      this.mediaRecorder.onstop = () => {
        this.isRecording = false;
        if (this.onStop) {
          const blob = this.getBlob();
          this.onStop(blob, this.getDuration());
        }
      };
      
      this.mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event);
        if (this.onError) {
          this.onError(event);
        }
      };
      
      this.mediaRecorder.start(100);
      
      this.isRecording = true;
      this.isPaused = false;
      this.startTime = Date.now();
      this.totalPausedTime = 0;
      
      if (this.onStart) {
        this.onStart();
      }
      
      return true;
    } catch (error) {
      console.error('Failed to start recording:', error);
      if (this.onError) {
        this.onError(error);
      }
      return false;
    }
  }

  pause() {
    if (!this.isRecording || this.isPaused) return;
    
    this.mediaRecorder.pause();
    this.isPaused = true;
    this.pauseTime = Date.now();
    
    if (this.onPause) {
      this.onPause();
    }
  }

  resume() {
    if (!this.isRecording || !this.isPaused) return;
    
    this.mediaRecorder.resume();
    this.isPaused = false;
    
    if (this.pauseTime > 0) {
      this.totalPausedTime += Date.now() - this.pauseTime;
      this.pauseTime = 0;
    }
    
    if (this.onResume) {
      this.onResume();
    }
  }

  stop() {
    if (!this.isRecording) return;
    
    this.mediaRecorder.stop();
  }

  getBlob() {
    if (this.chunks.length === 0) return null;
    
    const mimeType = this.mimeType.split(';')[0];
    return new Blob(this.chunks, { type: mimeType });
  }

  getDuration() {
    let elapsed = 0;
    
    if (this.startTime > 0) {
      const endTime = this.isRecording ? Date.now() : this.startTime;
      elapsed = (endTime - this.startTime) - this.totalPausedTime;
    }
    
    if (this.isPaused && this.pauseTime > 0) {
      elapsed -= (Date.now() - this.pauseTime);
    }
    
    return Math.max(0, elapsed);
  }

  getDurationFormatted() {
    const ms = this.getDuration();
    const seconds = Math.floor((ms / 1000) % 60);
    const minutes = Math.floor((ms / 60000) % 60);
    const hours = Math.floor(ms / 3600000);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }

  download(filename = 'recording.webm') {
    const blob = this.getBlob();
    if (!blob) return false;
    
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    return true;
  }

  getRecordingState() {
    return {
      isRecording: this.isRecording,
      isPaused: this.isPaused,
      duration: this.getDuration(),
      durationFormatted: this.getDurationFormatted(),
      chunksCount: this.chunks.length,
      mimeType: this.mimeType
    };
  }

  setIncludeMicAudio(enabled) {
    if (this.isRecording) {
      console.warn('Cannot change audio settings while recording');
      return;
    }
    this.includeMicAudio = enabled;
  }

  setVideoBitrate(bitrate) {
    if (this.isRecording) {
      console.warn('Cannot change bitrate while recording');
      return;
    }
    this.videoBitrate = bitrate;
  }

  setFPS(fps) {
    if (this.isRecording) {
      console.warn('Cannot change FPS while recording');
      return;
    }
    this.fps = fps;
  }

  dispose() {
    this.stop();
    
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      try {
        this.mediaRecorder.stop();
      } catch (e) {}
    }
    
    if (this.audioStream) {
      this.audioStream.getTracks().forEach(track => track.stop());
      this.audioStream = null;
    }
    
    if (this.captureStream) {
      this.captureStream.getTracks().forEach(track => track.stop());
      this.captureStream = null;
    }
    
    this.combinedStream = null;
    this.chunks = [];
    this.mediaRecorder = null;
    this.isRecording = false;
    this.isPaused = false;
  }
}

export default VideoRecorder;

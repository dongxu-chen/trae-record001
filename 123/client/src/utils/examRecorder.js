class ExamRecorder {
  constructor(config = {}) {
    this.videoStream = null;
    this.screenStream = null;
    this.videoRecorder = null;
    this.screenRecorder = null;
    this.videoChunks = [];
    this.screenChunks = [];
    this.isRecording = false;
    this.recordingId = null;
    
    this.userId = config.userId;
    this.examId = config.examId;
    this.userName = config.userName;
    this.apiBaseUrl = config.apiBaseUrl || 'http://localhost:3001';
    
    this.chunkSize = config.chunkSize || 5000;
    this.videoChunkIndex = 0;
    this.screenChunkIndex = 0;
    
    this.onRecordingStart = config.onRecordingStart || (() => {});
    this.onRecordingStop = config.onRecordingStop || (() => {});
    this.onChunkUploaded = config.onChunkUploaded || (() => {});
    this.onError = config.onError || (() => {});
  }

  setVideoStream(stream) {
    this.videoStream = stream;
  }

  setScreenStream(stream) {
    this.screenStream = stream;
  }

  generateRecordingId() {
    return `rec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  async start() {
    if (this.isRecording) {
      console.warn('录制已在进行中');
      return;
    }

    this.recordingId = this.generateRecordingId();
    this.videoChunks = [];
    this.screenChunks = [];
    this.videoChunkIndex = 0;
    this.screenChunkIndex = 0;

    try {
      if (this.videoStream) {
        this.videoRecorder = new MediaRecorder(this.videoStream, {
          mimeType: this.getSupportedMimeType()
        });
        
        this.videoRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            this.videoChunks.push(event.data);
            this.uploadChunk('video', event.data);
          }
        };

        this.videoRecorder.start(this.chunkSize);
      }

      if (this.screenStream) {
        this.screenRecorder = new MediaRecorder(this.screenStream, {
          mimeType: this.getSupportedMimeType()
        });
        
        this.screenRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            this.screenChunks.push(event.data);
            this.uploadChunk('screen', event.data);
          }
        };

        this.screenRecorder.start(this.chunkSize);
      }

      this.isRecording = true;
      this.onRecordingStart({ recordingId: this.recordingId });
      console.log('考试录制已开始:', this.recordingId);
    } catch (error) {
      console.error('启动录制失败:', error);
      this.onError(error);
    }
  }

  async stop() {
    if (!this.isRecording) return;

    try {
      if (this.videoRecorder && this.videoRecorder.state !== 'inactive') {
        this.videoRecorder.stop();
      }

      if (this.screenRecorder && this.screenRecorder.state !== 'inactive') {
        this.screenRecorder.stop();
      }

      const duration = Date.now() - parseInt(this.recordingId.split('_')[1]);
      
      await this.finishRecording(duration);

      this.isRecording = false;
      this.onRecordingStop({ 
        recordingId: this.recordingId,
        duration,
        videoChunks: this.videoChunks.length,
        screenChunks: this.screenChunks.length
      });
      
      console.log('考试录制已结束:', this.recordingId);
    } catch (error) {
      console.error('停止录制失败:', error);
      this.onError(error);
    }
  }

  async uploadChunk(type, blob) {
    try {
      const base64 = await this.blobToBase64(blob);
      
      const response = await fetch(`${this.apiBaseUrl}/api/recordings/chunk`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          recordingId: this.recordingId,
          chunkIndex: type === 'video' ? this.videoChunkIndex++ : this.screenChunkIndex++,
          chunkType: type,
          data: base64,
          userId: this.userId,
          examId: this.examId,
          userName: this.userName
        })
      });

      if (!response.ok) {
        throw new Error(`上传${type}块失败`);
      }

      this.onChunkUploaded({ type, chunkIndex: type === 'video' ? this.videoChunkIndex : this.screenChunkIndex });
    } catch (error) {
      console.error(`上传${type}块失败:`, error);
    }
  }

  async finishRecording(duration) {
    try {
      await fetch(`${this.apiBaseUrl}/api/recordings/finish`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          recordingId: this.recordingId,
          duration
        })
      });
    } catch (error) {
      console.error('结束录制失败:', error);
    }
  }

  getSupportedMimeType() {
    const types = [
      'video/webm;codecs=vp9',
      'video/webm;codecs=vp8',
      'video/webm',
      'video/mp4'
    ];
    
    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }
    
    return '';
  }

  blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  getVideoBlob() {
    if (this.videoChunks.length === 0) return null;
    return new Blob(this.videoChunks, { type: 'video/webm' });
  }

  getScreenBlob() {
    if (this.screenChunks.length === 0) return null;
    return new Blob(this.screenChunks, { type: 'video/webm' });
  }

  downloadVideo() {
    const blob = this.getVideoBlob();
    if (!blob) return;
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `exam_video_${this.recordingId}.webm`;
    a.click();
    URL.revokeObjectURL(url);
  }

  downloadScreen() {
    const blob = this.getScreenBlob();
    if (!blob) return;
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `exam_screen_${this.recordingId}.webm`;
    a.click();
    URL.revokeObjectURL(url);
  }

  destroy() {
    this.stop().catch(console.error);
    this.videoStream = null;
    this.screenStream = null;
    this.videoChunks = [];
    this.screenChunks = [];
  }
}

export default ExamRecorder;

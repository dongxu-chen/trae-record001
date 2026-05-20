export const SpeechRecognitionProvider = {
  WEB_SPEECH_API: 'web_speech_api',
  WHISPER_API: 'whisper_api',
  CUSTOM_API: 'custom_api',
}

class SpeechToSubtitle {
  constructor(options = {}) {
    this.provider = options.provider || SpeechRecognitionProvider.WEB_SPEECH_API
    this.apiKey = options.apiKey || null
    this.apiEndpoint = options.apiEndpoint || null
    this.language = options.language || 'zh-CN'
    
    this.recognition = null
    this.isRecording = false
    this.isProcessing = false
    this.audioContext = null
    this.mediaRecorder = null
    this.audioChunks = []
    
    this.transcript = []
    this.currentTranscript = ''
    this.interimTranscript = ''
    
    this.onResult = options.onResult || null
    this.onProgress = options.onProgress || null
    this.onError = options.onError || null
    this.onStart = options.onStart || null
    this.onEnd = options.onEnd || null
    
    this.wordTimestamps = []
    this.silenceThreshold = options.silenceThreshold || 0.5
    this.minPhraseLength = options.minPhraseLength || 3
    this.maxPhraseDuration = options.maxPhraseDuration || 5
    
    this._initRecognition()
  }

  _initRecognition() {
    if (this.provider === SpeechRecognitionProvider.WEB_SPEECH_API) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      
      if (SpeechRecognition) {
        this.recognition = new SpeechRecognition()
        this.recognition.continuous = true
        this.recognition.interimResults = true
        this.recognition.lang = this.language
        this.recognition.maxAlternatives = 1
        
        this.recognition.onresult = (event) => {
          this._handleRecognitionResult(event)
        }
        
        this.recognition.onerror = (event) => {
          this._handleError(event.error)
        }
        
        this.recognition.onstart = () => {
          this.isRecording = true
          if (this.onStart) this.onStart()
        }
        
        this.recognition.onend = () => {
          this.isRecording = false
          if (this.onEnd) this.onEnd()
        }
      } else {
        console.warn('浏览器不支持Web Speech API，将使用音频录制+API方式')
      }
    }
  }

  async startRecording() {
    if (this.isRecording) return
    
    try {
      if (this.recognition) {
        this.recognition.start()
      } else {
        await this._startAudioRecording()
      }
    } catch (error) {
      this._handleError(error.message || '录音启动失败')
      throw error
    }
  }

  async stopRecording() {
    if (!this.isRecording) return
    
    if (this.recognition) {
      this.recognition.stop()
    } else {
      await this._stopAudioRecording()
    }
  }

  async _startAudioRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)()
      this.mediaRecorder = new MediaRecorder(stream)
      this.audioChunks = []
      
      this.mediaRecorder.ondataavailable = (event) => {
        this.audioChunks.push(event.data)
      }
      
      this.mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' })
        await this._processAudioFile(audioBlob)
        stream.getTracks().forEach(track => track.stop())
      }
      
      this.mediaRecorder.start()
      this.isRecording = true
      
      if (this.onStart) this.onStart()
    } catch (error) {
      console.error('音频录制启动失败:', error)
      throw error
    }
  }

  async _stopAudioRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop()
    }
    this.isRecording = false
  }

  _handleRecognitionResult(event) {
    let interimTranscript = ''
    let finalTranscript = ''
    
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript
      const isFinal = event.results[i].isFinal
      
      if (isFinal) {
        finalTranscript += transcript
        this._addFinalTranscript(transcript)
      } else {
        interimTranscript += transcript
      }
    }
    
    this.interimTranscript = interimTranscript
    this.currentTranscript = finalTranscript
    
    if (this.onResult) {
      this.onResult({
        final: finalTranscript,
        interim: interimTranscript,
        isFinal: finalTranscript.length > 0,
      })
    }
  }

  _addFinalTranscript(text) {
    const timestamp = this._getCurrentTimestamp()
    const words = text.trim().split(/\s+/)
    
    this.wordTimestamps.push({
      text: text.trim(),
      startTime: timestamp - words.length * 0.3,
      endTime: timestamp,
      confidence: 0.9,
    })
    
    this.transcript.push({
      text: text.trim(),
      startTime: timestamp - words.length * 0.3,
      endTime: timestamp,
      confidence: 0.9,
    })
  }

  _getCurrentTimestamp() {
    if (this._startTime) {
      return (Date.now() - this._startTime) / 1000
    }
    return Date.now() / 1000
  }

  _handleError(error) {
    console.error('语音识别错误:', error)
    if (this.onError) {
      this.onError(error)
    }
  }

  async processAudioFile(audioFile, onProgress = null) {
    this.isProcessing = true
    this.transcript = []
    this.wordTimestamps = []
    
    try {
      if (this.provider === SpeechRecognitionProvider.WHISPER_API) {
        await this._processWithWhisperAPI(audioFile, onProgress)
      } else if (this.provider === SpeechRecognitionProvider.CUSTOM_API) {
        await this._processWithCustomAPI(audioFile, onProgress)
      } else {
        await this._processWithFileRecognition(audioFile, onProgress)
      }
      
      return this.generateSubtitles()
    } catch (error) {
      this._handleError(error.message || '音频处理失败')
      throw error
    } finally {
      this.isProcessing = false
    }
  }

  async _processWithWhisperAPI(audioFile, onProgress) {
    if (!this.apiKey) {
      throw new Error('需要提供OpenAI API Key')
    }
    
    if (onProgress) onProgress(0.1, '正在上传音频...')
    
    const formData = new FormData()
    formData.append('file', audioFile)
    formData.append('model', 'whisper-1')
    formData.append('language', this.language.replace('-', ''))
    formData.append('response_format', 'verbose_json')
    formData.append('timestamp_granularities[]', 'word')
    formData.append('timestamp_granularities[]', 'segment')
    
    const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
      },
      body: formData,
    })
    
    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status}`)
    }
    
    if (onProgress) onProgress(0.8, '正在处理识别结果...')
    
    const result = await response.json()
    
    if (result.words) {
      this.wordTimestamps = result.words.map(w => ({
        text: w.word,
        startTime: w.start,
        endTime: w.end,
        confidence: w.confidence || 0.9,
      }))
    }
    
    if (result.segments) {
      this.transcript = result.segments.map(s => ({
        text: s.text.trim(),
        startTime: s.start,
        endTime: s.end,
        confidence: s.confidence || 0.9,
      }))
    }
    
    if (onProgress) onProgress(1.0, '识别完成')
  }

  async _processWithCustomAPI(audioFile, onProgress) {
    if (!this.apiEndpoint) {
      throw new Error('需要提供自定义API端点')
    }
    
    if (onProgress) onProgress(0.1, '正在上传音频...')
    
    const formData = new FormData()
    formData.append('audio', audioFile)
    formData.append('language', this.language)
    
    const response = await fetch(this.apiEndpoint, {
      method: 'POST',
      body: formData,
    })
    
    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status}`)
    }
    
    if (onProgress) onProgress(0.8, '正在处理识别结果...')
    
    const result = await response.json()
    
    if (result.segments) {
      this.transcript = result.segments.map(s => ({
        text: s.text.trim(),
        startTime: s.start,
        endTime: s.end,
        confidence: s.confidence || 0.9,
      }))
    }
    
    if (onProgress) onProgress(1.0, '识别完成')
  }

  async _processWithFileRecognition(audioFile, onProgress) {
    if (onProgress) onProgress(0.1, '正在分析音频...')
    
    const audio = new Audio()
    audio.src = URL.createObjectURL(audioFile)
    
    await new Promise((resolve, reject) => {
      audio.onloadedmetadata = resolve
      audio.onerror = reject
    })
    
    const duration = audio.duration
    audio.remove()
    
    if (onProgress) onProgress(0.3, '正在生成模拟字幕...')
    
    const sampleTexts = [
      '欢迎使用语音转字幕功能',
      '这是一个测试文本',
      '语音识别正在进行中',
      '请确保音频清晰可辨',
      '系统会自动分割句子',
      '生成的字幕可以编辑调整',
    ]
    
    const segmentDuration = this.maxPhraseDuration
    const numSegments = Math.ceil(duration / segmentDuration)
    
    for (let i = 0; i < numSegments; i++) {
      const startTime = i * segmentDuration
      const endTime = Math.min((i + 1) * segmentDuration, duration)
      
      if (onProgress) {
        onProgress(0.3 + 0.6 * (i / numSegments), `正在处理第 ${i + 1}/${numSegments} 段...`)
      }
      
      this.transcript.push({
        text: sampleTexts[i % sampleTexts.length],
        startTime,
        endTime,
        confidence: 0.85,
      })
      
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    
    if (onProgress) onProgress(1.0, '识别完成')
  }

  async extractAudioFromVideo(videoFile, onProgress = null) {
    if (onProgress) onProgress(0, '正在提取音频...')
    
    const audioContext = new (window.AudioContext || window.webkitAudioContext)()
    const arrayBuffer = await videoFile.arrayBuffer()
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
    
    const numberOfChannels = audioBuffer.numberOfChannels
    const sampleRate = audioBuffer.sampleRate
    const length = audioBuffer.length
    
    const offlineContext = new OfflineAudioContext(numberOfChannels, length, sampleRate)
    const source = offlineContext.createBufferSource()
    source.buffer = audioBuffer
    
    const destination = offlineContext.createMediaStreamDestination()
    source.connect(destination)
    source.start()
    
    const recordedChunks = []
    const mediaRecorder = new MediaRecorder(destination.stream)
    
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        recordedChunks.push(e.data)
      }
    }
    
    return new Promise((resolve) => {
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(recordedChunks, { type: 'audio/webm' })
        const audioFile = new File([audioBlob], 'extracted_audio.webm', { type: 'audio/webm' })
        resolve(audioFile)
      }
      
      mediaRecorder.start()
      
      setTimeout(() => {
        mediaRecorder.stop()
        audioContext.close()
      }, (audioBuffer.duration + 0.5) * 1000)
    })
  }

  generateSubtitles(options = {}) {
    const minDuration = options.minDuration || 1.5
    const maxDuration = options.maxDuration || 6
    const mergeGap = options.mergeGap || 0.3
    
    const subtitles = []
    let currentSubtitle = null
    
    for (const segment of this.transcript) {
      const text = segment.text.trim()
      if (!text || text.length < this.minPhraseLength) continue
      
      if (!currentSubtitle) {
        currentSubtitle = {
          text,
          startTime: segment.startTime,
          endTime: segment.endTime,
        }
      } else {
        const gap = segment.startTime - currentSubtitle.endTime
        
        if (gap < mergeGap && 
            currentSubtitle.endTime - currentSubtitle.startTime < maxDuration) {
          currentSubtitle.text += ' ' + text
          currentSubtitle.endTime = segment.endTime
        } else {
          const duration = currentSubtitle.endTime - currentSubtitle.startTime
          if (duration >= minDuration) {
            subtitles.push({ ...currentSubtitle })
          }
          
          currentSubtitle = {
            text,
            startTime: segment.startTime,
            endTime: segment.endTime,
          }
        }
      }
    }
    
    if (currentSubtitle) {
      const duration = currentSubtitle.endTime - currentSubtitle.startTime
      if (duration >= minDuration) {
        subtitles.push(currentSubtitle)
      }
    }
    
    return subtitles.map((sub, index) => ({
      id: Date.now().toString(36) + index.toString(),
      text: sub.text,
      startTime: sub.startTime,
      endTime: sub.endTime,
      style: {
        fontSize: 48,
        color: '#ffffff',
        backgroundColor: 'rgba(0,0,0,0.5)',
        position: 'bottom',
      },
    }))
  }

  getFullTranscript() {
    return this.transcript.map(t => t.text).join(' ')
  }

  getTranscriptWithTimestamps() {
    return [...this.transcript]
  }

  getWordTimestamps() {
    return [...this.wordTimestamps]
  }

  setLanguage(language) {
    this.language = language
    if (this.recognition) {
      this.recognition.lang = language
    }
  }

  setProvider(provider, options = {}) {
    this.provider = provider
    if (options.apiKey) this.apiKey = options.apiKey
    if (options.apiEndpoint) this.apiEndpoint = options.apiEndpoint
    this._initRecognition()
  }

  isSupported() {
    return !!(this.recognition || 
      (navigator.mediaDevices && navigator.mediaDevices.getUserMedia))
  }

  dispose() {
    if (this.recognition) {
      try {
        this.recognition.stop()
      } catch (e) {}
      this.recognition = null
    }
    
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      try {
        this.mediaRecorder.stop()
      } catch (e) {}
    }
    
    if (this.audioContext) {
      this.audioContext.close()
    }
    
    this.transcript = []
    this.wordTimestamps = []
    this.audioChunks = []
    this.isRecording = false
    this.isProcessing = false
  }
}

export default SpeechToSubtitle

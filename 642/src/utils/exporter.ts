interface FrameData {
  imageData: ImageData
  timestamp: number
}

export class AnimationExporter {
  private canvas: HTMLCanvasElement | null = null
  private ctx: CanvasRenderingContext2D | null = null
  private targetFps: number = 30
  private frameInterval: number = 1000 / 30
  private isRecording: boolean = false
  private startTime: number = 0
  private lastFrameTime: number = 0
  private frameCount: number = 0
  private animationId: number | null = null
  private recordedFrames: FrameData[] = []
  private videoWidth: number = 0
  private videoHeight: number = 0
  private mediaRecorder: MediaRecorder | null = null
  private recordedChunks: Blob[] = []
  private stream: MediaStream | null = null
  private captureCanvas: HTMLCanvasElement | null = null
  private captureCtx: CanvasRenderingContext2D | null = null

  constructor(targetFps: number = 30) {
    this.targetFps = targetFps
    this.frameInterval = 1000 / targetFps
  }

  start(canvas: HTMLCanvasElement): void {
    this.canvas = canvas
    this.videoWidth = canvas.width
    this.videoHeight = canvas.height
    this.isRecording = true
    this.startTime = performance.now()
    this.lastFrameTime = 0
    this.frameCount = 0
    this.recordedFrames = []
    this.recordedChunks = []

    this.captureCanvas = document.createElement('canvas')
    this.captureCanvas.width = this.videoWidth
    this.captureCanvas.height = this.videoHeight
    this.captureCtx = this.captureCanvas.getContext('2d', { willReadFrequently: true })

    this.stream = this.captureCanvas.captureStream(this.targetFps)

    const mimeTypes = [
      'video/webm;codecs=vp9',
      'video/webm;codecs=vp8',
      'video/webm',
    ]

    let selectedMimeType = ''
    for (const mimeType of mimeTypes) {
      if (MediaRecorder.isTypeSupported(mimeType)) {
        selectedMimeType = mimeType
        break
      }
    }

    if (!selectedMimeType) {
      throw new Error('No supported video format found')
    }

    this.mediaRecorder = new MediaRecorder(this.stream, {
      mimeType: selectedMimeType,
      videoBitsPerSecond: 8000000,
    })

    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        this.recordedChunks.push(e.data)
      }
    }

    this.mediaRecorder.start(100)

    this.captureFrame()
  }

  private captureFrame = (): void => {
    if (!this.isRecording || !this.canvas || !this.captureCtx) {
      return
    }

    const currentTime = performance.now() - this.startTime
    const expectedFrameCount = Math.floor(currentTime / this.frameInterval)

    while (this.frameCount < expectedFrameCount) {
      const frameTimestamp = this.frameCount * this.frameInterval

      this.captureCtx.drawImage(this.canvas, 0, 0)

      this.frameCount++
      this.lastFrameTime = frameTimestamp
    }

    this.animationId = requestAnimationFrame(this.captureFrame)
  }

  stop(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder) {
        reject(new Error('Recording not started'))
        return
      }

      this.isRecording = false

      if (this.animationId) {
        cancelAnimationFrame(this.animationId)
        this.animationId = null
      }

      this.mediaRecorder.onstop = () => {
        const blob = new Blob(this.recordedChunks, { type: 'video/webm' })
        this.cleanup()
        resolve(blob)
      }

      this.mediaRecorder.stop()
    })
  }

  download(filename: string = 'fluid-simulation.webm'): void {
    this.stop().then((blob) => {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    })
  }

  private cleanup(): void {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop())
      this.stream = null
    }
    this.mediaRecorder = null
    this.canvas = null
    this.captureCtx = null
    this.captureCanvas = null
    this.recordedFrames = []
  }

  getRecordingState(): { isRecording: boolean; frameCount: number; fps: number } {
    return {
      isRecording: this.isRecording,
      frameCount: this.frameCount,
      fps: this.targetFps,
    }
  }

  setTargetFps(fps: number): void {
    this.targetFps = fps
    this.frameInterval = 1000 / fps
  }
}

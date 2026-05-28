import { FFmpeg } from '@ffmpeg/ffmpeg'
import { fetchFile, toBlobURL } from '@ffmpeg/util'

export interface AudioSegment {
  id: string
  index: number
  startTime: number
  endTime: number
  duration: number
  inputFile?: File
  processed?: boolean
  outputUrl?: string
  outputBlob?: Blob
}

export interface SegmentConfig {
  segmentDuration: number
  overlapDuration: number
  targetSampleRate: number
  targetChannels: number
}

const DEFAULT_CONFIG: SegmentConfig = {
  segmentDuration: 30,
  overlapDuration: 1,
  targetSampleRate: 44100,
  targetChannels: 2,
}

export class AudioSegmentProcessor {
  private ffmpeg: FFmpeg | null = null
  private loadingPromise: Promise<void> | null = null
  private config: SegmentConfig

  constructor(config?: Partial<SegmentConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config }
  }

  async loadFFmpeg(): Promise<FFmpeg> {
    if (this.ffmpeg) return this.ffmpeg
    if (this.loadingPromise) {
      await this.loadingPromise
      return this.ffmpeg!
    }

    this.loadingPromise = (async () => {
      const ffmpeg = new FFmpeg()
      const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/esm'

      await ffmpeg.load({
        coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
        wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
      })
      this.ffmpeg = ffmpeg
    })()

    await this.loadingPromise
    return this.ffmpeg!
  }

  createSegments(duration: number): AudioSegment[] {
    const segments: AudioSegment[] = []
    const { segmentDuration, overlapDuration } = this.config

    let index = 0
    for (let startTime = 0; startTime < duration; startTime += segmentDuration - overlapDuration) {
      const endTime = Math.min(startTime + segmentDuration, duration)
      segments.push({
        id: `seg_${index}_${Date.now()}`,
        index,
        startTime,
        endTime,
        duration: endTime - startTime,
        processed: false,
      })
      index++

      if (endTime >= duration) break
    }

    return segments
  }

  async extractSegment(
    inputFile: File,
    segment: AudioSegment
  ): Promise<Blob> {
    const ffmpeg = await this.loadFFmpeg()
    const inputName = `input_${segment.id}`
    const outputName = `output_${segment.id}.wav`

    await ffmpeg.writeFile(inputName, await fetchFile(inputFile))

    const args = [
      '-ss', String(segment.startTime),
      '-t', String(segment.duration),
      '-i', inputName,
      '-ar', String(this.config.targetSampleRate),
      '-ac', String(this.config.targetChannels),
      '-codec:a', 'pcm_s16le',
      '-y',
      outputName,
    ]

    await ffmpeg.exec(args)

    const data = await ffmpeg.readFile(outputName)
    const blob = new Blob([data.buffer as ArrayBuffer], { type: 'audio/wav' })

    await ffmpeg.deleteFile(inputName)
    await ffmpeg.deleteFile(outputName)

    return blob
  }

  async processSegmentWithEffects(
    inputFile: File,
    segment: AudioSegment,
    effects: {
      volume?: number
      fadeIn?: number
      fadeOut?: number
      clipStart?: number
      clipEnd?: number
    }
  ): Promise<Blob> {
    const ffmpeg = await this.loadFFmpeg()
    const inputName = `input_${segment.id}`
    const outputName = `output_${segment.id}.wav`

    await ffmpeg.writeFile(inputName, await fetchFile(inputFile))

    const filterParts: string[] = []

    if (effects.volume !== undefined && effects.volume !== 1) {
      filterParts.push(`volume=${effects.volume}`)
    }

    const segmentDuration = segment.duration

    if (effects.fadeIn && effects.fadeIn > 0 && segment.startTime === 0) {
      filterParts.push(`afade=t=in:st=0:d=${effects.fadeIn}`)
    }

    if (effects.fadeOut && effects.fadeOut > 0) {
      const fadeStart = Math.max(0, segmentDuration - effects.fadeOut)
      filterParts.push(`afade=t=out:st=${fadeStart}:d=${effects.fadeOut}`)
    }

    const args: string[] = [
      '-ss', String(segment.startTime),
      '-t', String(segment.duration),
      '-i', inputName,
    ]

    if (filterParts.length > 0) {
      args.push('-af', filterParts.join(','))
    }

    args.push(
      '-ar', String(this.config.targetSampleRate),
      '-ac', String(this.config.targetChannels),
      '-codec:a', 'pcm_s16le',
      '-y',
      outputName
    )

    await ffmpeg.exec(args)

    const data = await ffmpeg.readFile(outputName)
    const blob = new Blob([data.buffer as ArrayBuffer], { type: 'audio/wav' })

    await ffmpeg.deleteFile(inputName)
    await ffmpeg.deleteFile(outputName)

    return blob
  }

  async mergeSegments(
    segmentBlobs: Blob[],
    outputFormat: 'wav' | 'mp3' | 'ogg' = 'wav',
    progressCallback?: (progress: number) => void
  ): Promise<Blob> {
    if (segmentBlobs.length === 0) {
      throw new Error('No segments to merge')
    }

    if (segmentBlobs.length === 1) {
      return segmentBlobs[0]
    }

    const ffmpeg = await this.loadFFmpeg()
    const inputFiles: string[] = []

    for (let i = 0; i < segmentBlobs.length; i++) {
      const fileName = `seg_${i}.wav`
      await ffmpeg.writeFile(fileName, await fetchFile(segmentBlobs[i]))
      inputFiles.push(fileName)
    }

    const concatFile = 'concat_list.txt'
    const concatContent = inputFiles.map(f => `file '${f}'`).join('\n')
    await ffmpeg.writeFile(concatFile, new TextEncoder().encode(concatContent))

    ffmpeg.on('progress', ({ progress }) => {
      progressCallback?.(progress)
    })

    const outputName = `merged.${outputFormat}`
    const codecMap: Record<string, string[]> = {
      wav: ['-codec:a', 'pcm_s16le'],
      mp3: ['-codec:a', 'libmp3lame', '-b:a', '320k'],
      ogg: ['-codec:a', 'libvorbis', '-b:a', '320k'],
    }

    const args = [
      '-f', 'concat',
      '-safe', '0',
      '-i', concatFile,
      ...codecMap[outputFormat],
      '-y',
      outputName,
    ]

    await ffmpeg.exec(args)

    const data = await ffmpeg.readFile(outputName)
    const mimeTypes: Record<string, string> = {
      wav: 'audio/wav',
      mp3: 'audio/mpeg',
      ogg: 'audio/ogg',
    }
    const blob = new Blob([data.buffer as ArrayBuffer], { type: mimeTypes[outputFormat] })

    for (const file of [...inputFiles, concatFile, outputName]) {
      try {
        await ffmpeg.deleteFile(file)
      } catch (e) {
        // ignore
      }
    }

    return blob
  }

  async processLargeAudio(
    inputFile: File,
    effects: {
      volume?: number
      fadeIn?: number
      fadeOut?: number
      trimStart?: number
      trimEnd?: number
    },
    outputFormat: 'wav' | 'mp3' | 'ogg' = 'wav',
    progressCallback?: (progress: number, stage: 'splitting' | 'processing' | 'merging', segmentIndex: number, totalSegments: number) => void
  ): Promise<Blob> {
    const audio = new Audio()
    audio.src = URL.createObjectURL(inputFile)
    await new Promise<void>((resolve) => {
      audio.onloadedmetadata = () => resolve()
    })
    const duration = audio.duration
    URL.revokeObjectURL(audio.src)

    const adjustedDuration = effects.trimEnd
      ? effects.trimEnd - (effects.trimStart || 0)
      : duration - (effects.trimStart || 0)

    const segments = this.createSegments(adjustedDuration)
    const processedBlobs: Blob[] = []

    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i]
      const adjustedSegment = {
        ...segment,
        startTime: segment.startTime + (effects.trimStart || 0),
        endTime: segment.endTime + (effects.trimStart || 0),
      }

      progressCallback?.(
        i / segments.length * 0.8,
        'processing',
        i,
        segments.length
      )

      const isFirst = i === 0
      const isLast = i === segments.length - 1

      const blob = await this.processSegmentWithEffects(
        inputFile,
        adjustedSegment,
        {
          volume: effects.volume,
          fadeIn: isFirst ? effects.fadeIn : 0,
          fadeOut: isLast ? effects.fadeOut : 0,
        }
      )
      processedBlobs.push(blob)
    }

    progressCallback?.(0.9, 'merging', segments.length, segments.length)

    const result = await this.mergeSegments(processedBlobs, outputFormat, (p) => {
      progressCallback?.(0.9 + p * 0.1, 'merging', segments.length, segments.length)
    })

    return result
  }
}

export const segmentProcessor = new AudioSegmentProcessor()

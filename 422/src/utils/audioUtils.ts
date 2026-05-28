import { FFmpeg } from '@ffmpeg/ffmpeg'
import { fetchFile, toBlobURL } from '@ffmpeg/util'
import { segmentProcessor } from './AudioSegmentProcessor'
import { audioTimeSynchronizer } from './AudioTimeSynchronizer'

let ffmpegInstance: FFmpeg | null = null
let loadingPromise: Promise<void> | null = null

export async function loadFFmpeg(): Promise<FFmpeg> {
  if (ffmpegInstance) return ffmpegInstance
  if (loadingPromise) {
    await loadingPromise
    return ffmpegInstance!
  }

  loadingPromise = (async () => {
    const ffmpeg = new FFmpeg()
    const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/esm'

    await ffmpeg.load({
      coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
      wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
    })
    ffmpegInstance = ffmpeg
  })()

  await loadingPromise
  return ffmpegInstance!
}

export async function convertAudioFormat(
  inputFile: File,
  outputFormat: 'mp3' | 'wav' | 'ogg' | 'm4a',
  progressCallback?: (progress: number) => void,
  useSegmentedProcessing: boolean = true
): Promise<Blob> {
  const duration = await getAudioDuration(inputFile)

  if (useSegmentedProcessing && duration > 60) {
    return processLargeAudioWithEffects(
      inputFile,
      {},
      outputFormat as 'mp3' | 'wav' | 'ogg',
      (p) => progressCallback?.(p)
    )
  }

  const ffmpeg = await loadFFmpeg()

  const inputName = inputFile.name.replace(/[^a-zA-Z0-9._-]/g, '_')
  const outputName = `output.${outputFormat}`

  ffmpeg.on('progress', ({ progress }) => {
    progressCallback?.(progress)
  })

  await ffmpeg.writeFile(inputName, await fetchFile(inputFile))

  const codecMap: Record<string, string[]> = {
    mp3: ['-codec:a', 'libmp3lame', '-b:a', '320k'],
    wav: ['-codec:a', 'pcm_s16le'],
    ogg: ['-codec:a', 'libvorbis', '-b:a', '320k'],
    m4a: ['-codec:a', 'aac', '-b:a', '320k'],
  }

  const args = [
    '-i', inputName,
    ...codecMap[outputFormat],
    '-y',
    outputName,
  ]

  await ffmpeg.exec(args)

  const data = await ffmpeg.readFile(outputName)
  const mimeTypes: Record<string, string> = {
    mp3: 'audio/mpeg',
    wav: 'audio/wav',
    ogg: 'audio/ogg',
    m4a: 'audio/mp4',
  }

  await ffmpeg.deleteFile(inputName)
  await ffmpeg.deleteFile(outputName)

  return new Blob([data.buffer as ArrayBuffer], { type: mimeTypes[outputFormat] })
}

export async function applyAudioEffects(
  inputFile: File,
  effects: {
    volume?: number
    fadeIn?: number
    fadeOut?: number
    trimStart?: number
    trimEnd?: number
    duration?: number
  },
  outputFormat: 'mp3' | 'wav' = 'wav',
  useSegmentedProcessing: boolean = true
): Promise<Blob> {
  const duration = await getAudioDuration(inputFile)

  if (useSegmentedProcessing && duration > 60) {
    return processLargeAudioWithEffects(
      inputFile,
      effects,
      outputFormat
    )
  }

  const ffmpeg = await loadFFmpeg()

  const inputName = 'input_' + Date.now()
  const outputName = `output.${outputFormat}`

  await ffmpeg.writeFile(inputName, await fetchFile(inputFile))

  const filterParts: string[] = []

  if (effects.volume !== undefined && effects.volume !== 1) {
    filterParts.push(`volume=${effects.volume}`)
  }

  if (effects.fadeIn && effects.fadeIn > 0) {
    filterParts.push(`afade=t=in:st=0:d=${effects.fadeIn}`)
  }

  const effDuration = effects.duration || duration
  if (effects.fadeOut && effects.fadeOut > 0) {
    const fadeStart = Math.max(0, effDuration - effects.fadeOut)
    filterParts.push(`afade=t=out:st=${fadeStart}:d=${effects.fadeOut}`)
  }

  const args: string[] = ['-i', inputName]

  if (effects.trimStart !== undefined || effects.trimEnd !== undefined) {
    if (effects.trimStart !== undefined) {
      args.push('-ss', String(effects.trimStart))
    }
    if (effects.trimEnd !== undefined) {
      args.push('-to', String(effects.trimEnd))
    }
  }

  if (filterParts.length > 0) {
    args.push('-af', filterParts.join(','))
  }

  args.push('-y', outputName)

  await ffmpeg.exec(args)

  const data = await ffmpeg.readFile(outputName)
  const mimeTypes: Record<string, string> = {
    mp3: 'audio/mpeg',
    wav: 'audio/wav',
  }

  await ffmpeg.deleteFile(inputName)
  await ffmpeg.deleteFile(outputName)

  return new Blob([data.buffer as ArrayBuffer], { type: mimeTypes[outputFormat] })
}

export async function processLargeAudioWithEffects(
  inputFile: File,
  effects: {
    volume?: number
    fadeIn?: number
    fadeOut?: number
    trimStart?: number
    trimEnd?: number
  },
  outputFormat: 'wav' | 'mp3' | 'ogg' = 'wav',
  progressCallback?: (progress: number, stage?: 'splitting' | 'processing' | 'merging', segmentIndex?: number, totalSegments?: number) => void
): Promise<Blob> {
  return segmentProcessor.processLargeAudio(
    inputFile,
    effects,
    outputFormat,
    progressCallback
  )
}

export async function mergeMultipleTracks(
  tracks: Array<{
    file: File
    offset: number
    volume: number
    startTime: number
    endTime: number
  }>,
  outputFormat: 'wav' | 'mp3' | 'ogg' = 'wav',
  progressCallback?: (progress: number) => void
): Promise<Blob> {
  const ffmpeg = await loadFFmpeg()
  const inputFiles: string[] = []
  const filterComplex: string[] = []

  for (let i = 0; i < tracks.length; i++) {
    const track = tracks[i]
    const fileName = `track_${i}.wav`

    const processedBlob = await applyAudioEffects(
      track.file,
      {
        volume: track.volume,
        trimStart: track.startTime,
        trimEnd: track.endTime,
      },
      'wav'
    )

    await ffmpeg.writeFile(fileName, await fetchFile(new File([processedBlob], fileName)))
    inputFiles.push(fileName)

    const delaySamples = Math.round(track.offset * 44100)
    filterComplex.push(`[${i}:a]adelay=${delaySamples}S|${delaySamples}S,volume=${track.volume}[a${i}]`)
  }

  const mixInputs = tracks.map((_, i) => `[a${i}]`).join('')
  filterComplex.push(`${mixInputs}amix=inputs=${tracks.length}:duration=longest[aout]`)

  const outputName = `mixed.${outputFormat}`
  const codecMap: Record<string, string[]> = {
    wav: ['-codec:a', 'pcm_s16le'],
    mp3: ['-codec:a', 'libmp3lame', '-b:a', '320k'],
    ogg: ['-codec:a', 'libvorbis', '-b:a', '320k'],
  }

  const args = [
    ...inputFiles.flatMap(f => ['-i', f]),
    '-filter_complex', filterComplex.join(';'),
    '-map', '[aout]',
    ...codecMap[outputFormat],
    '-y',
    outputName,
  ]

  ffmpeg.on('progress', ({ progress }) => {
    progressCallback?.(progress)
  })

  await ffmpeg.exec(args)

  const data = await ffmpeg.readFile(outputName)
  const mimeTypes: Record<string, string> = {
    wav: 'audio/wav',
    mp3: 'audio/mpeg',
    ogg: 'audio/ogg',
  }

  for (const file of [...inputFiles, outputName]) {
    try {
      await ffmpeg.deleteFile(file)
    } catch (e) {
      // ignore
    }
  }

  return new Blob([data.buffer as ArrayBuffer], { type: mimeTypes[outputFormat] })
}

export function getAudioDuration(file: File): Promise<number> {
  return new Promise((resolve) => {
    const audio = new Audio()
    audio.preload = 'metadata'
    audio.onloadedmetadata = () => {
      resolve(audio.duration)
    }
    audio.onerror = () => {
      resolve(0)
    }
    audio.src = URL.createObjectURL(file)
  })
}

export async function getAudioSampleRate(file: File): Promise<number> {
  const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
  const ctx = new AudioContextClass()
  const arrayBuffer = await file.arrayBuffer()
  const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0))
  const sampleRate = audioBuffer.sampleRate
  ctx.close()
  return sampleRate
}

export function formatTime(seconds: number): string {
  if (!isFinite(seconds)) return '00:00.000'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`
}

export function formatTimeSamples(seconds: number, sampleRate: number = 44100): string {
  const samples = Math.round(seconds * sampleRate)
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 1000)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')} [${samples} samples]`
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export { audioTimeSynchronizer, segmentProcessor }

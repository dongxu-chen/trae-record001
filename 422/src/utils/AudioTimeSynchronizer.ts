export interface AudioTimeSyncConfig {
  targetSampleRate: number
  toleranceMs: number
  useCrossFading: boolean
  crossFadeDurationMs: number
}

export interface SyncedClip {
  id: string
  originalSampleRate: number
  originalDuration: number
  startTime: number
  endTime: number
  offset: number
  resampleRatio: number
  alignedStartTime: number
  alignedEndTime: number
  alignedOffset: number
  driftCorrection: number
}

const DEFAULT_CONFIG: AudioTimeSyncConfig = {
  targetSampleRate: 44100,
  toleranceMs: 1,
  useCrossFading: true,
  crossFadeDurationMs: 10,
}

export class AudioTimeSynchronizer {
  private config: AudioTimeSyncConfig
  private driftHistory: Map<string, number[]> = new Map()

  constructor(config?: Partial<AudioTimeSyncConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config }
  }

  alignSampleRate(
    sourceSampleRate: number,
    sourceDuration: number
  ): {
    alignedDuration: number
    resampleRatio: number
    sampleCount: number
    alignedSampleCount: number
  } {
    const resampleRatio = this.config.targetSampleRate / sourceSampleRate
    const originalSamples = Math.round(sourceSampleRate * sourceDuration)
    const alignedSamples = Math.round(originalSamples * resampleRatio)
    const alignedDuration = alignedSamples / this.config.targetSampleRate

    return {
      alignedDuration,
      resampleRatio,
      sampleCount: originalSamples,
      alignedSampleCount: alignedSamples,
    }
  }

  syncClipTiming(
    clip: {
      id: string
      startTime: number
      endTime: number
      offset: number
    },
    sourceSampleRate: number,
    sourceDuration: number
  ): SyncedClip {
    const alignment = this.alignSampleRate(sourceSampleRate, sourceDuration)

    const alignedOffset = this.snapToSampleBoundary(clip.offset)
    const alignedStartTime = this.snapToSampleBoundary(clip.startTime)
    const alignedEndTime = this.snapToSampleBoundary(clip.endTime)

    const originalDuration = clip.endTime - clip.startTime
    const alignedDuration = alignedEndTime - alignedStartTime
    const driftCorrection = alignedDuration - originalDuration * alignment.resampleRatio

    this.recordDrift(clip.id, driftCorrection)

    return {
      id: clip.id,
      originalSampleRate: sourceSampleRate,
      originalDuration: sourceDuration,
      startTime: clip.startTime,
      endTime: clip.endTime,
      offset: clip.offset,
      resampleRatio: alignment.resampleRatio,
      alignedStartTime,
      alignedEndTime,
      alignedOffset,
      driftCorrection,
    }
  }

  snapToSampleBoundary(timeSeconds: number): number {
    const sampleCount = Math.round(timeSeconds * this.config.targetSampleRate)
    return sampleCount / this.config.targetSampleRate
  }

  snapToMillisecond(timeSeconds: number): number {
    return Math.round(timeSeconds * 1000) / 1000
  }

  private recordDrift(clipId: string, drift: number) {
    if (!this.driftHistory.has(clipId)) {
      this.driftHistory.set(clipId, [])
    }
    const history = this.driftHistory.get(clipId)!
    history.push(drift)
    if (history.length > 100) {
      history.shift()
    }
  }

  getAverageDrift(clipId: string): number {
    const history = this.driftHistory.get(clipId)
    if (!history || history.length === 0) return 0
    return history.reduce((a, b) => a + b, 0) / history.length
  }

  calculatePlaybackTiming(
    syncedClip: SyncedClip,
    currentTime: number,
    playbackSpeed: number = 1
  ): {
    shouldPlay: boolean
    sourceSeekTime: number
    playbackDuration: number
    gainEnvelope: { startTime: number; fadeIn: number; fadeOut: number }
  } {
    const clipStart = syncedClip.alignedOffset
    const clipEnd = syncedClip.alignedOffset + (syncedClip.alignedEndTime - syncedClip.alignedStartTime)

    const shouldPlay = currentTime >= clipStart && currentTime < clipEnd

    if (!shouldPlay) {
      return {
        shouldPlay: false,
        sourceSeekTime: 0,
        playbackDuration: 0,
        gainEnvelope: { startTime: 0, fadeIn: 0, fadeOut: 0 },
      }
    }

    const relativeTime = (currentTime - clipStart) / playbackSpeed
    const sourceSeekTime = syncedClip.alignedStartTime + relativeTime
    const playbackDuration = syncedClip.alignedEndTime - syncedClip.alignedStartTime - relativeTime

    const clipDuration = clipEnd - clipStart
    const crossFadeMs = this.config.crossFadeDurationMs
    const crossFadeDuration = crossFadeMs / 1000

    const fadeIn = Math.min(crossFadeDuration, relativeTime)
    const fadeOut = Math.min(crossFadeDuration, clipDuration - relativeTime)

    return {
      shouldPlay: true,
      sourceSeekTime: this.snapToSampleBoundary(sourceSeekTime),
      playbackDuration: this.snapToSampleBoundary(playbackDuration),
      gainEnvelope: {
        startTime: this.snapToSampleBoundary(relativeTime),
        fadeIn,
        fadeOut,
      },
    }
  }

  syncMultipleClips(
    clips: Array<{
      id: string
      startTime: number
      endTime: number
      offset: number
      sampleRate: number
      duration: number
    }>
  ): {
    syncedClips: SyncedClip[]
    globalStart: number
    globalEnd: number
    totalDrift: number
  } {
    const syncedClips = clips.map((clip) =>
      this.syncClipTiming(clip, clip.sampleRate, clip.duration)
    )

    const globalStart = Math.min(...syncedClips.map((c) => c.alignedOffset))
    const globalEnd = Math.max(
      ...syncedClips.map((c) => c.alignedOffset + (c.alignedEndTime - c.alignedStartTime))
    )

    const totalDrift = syncedClips.reduce((sum, c) => sum + Math.abs(c.driftCorrection), 0)

    return {
      syncedClips,
      globalStart: this.snapToSampleBoundary(globalStart),
      globalEnd: this.snapToSampleBoundary(globalEnd),
      totalDrift: this.snapToSampleBoundary(totalDrift),
    }
  }

  generateCrossFadeBuffer(
    length: number,
    type: 'linear' | 'equal-power' = 'equal-power'
  ): Float32Array {
    const buffer = new Float32Array(length)

    for (let i = 0; i < length; i++) {
      const t = i / (length - 1)

      if (type === 'linear') {
        buffer[i] = t
      } else {
        buffer[i] = Math.sin(t * Math.PI / 2)
      }
    }

    return buffer
  }

  async applyTimeStretchCorrection(
    audioBuffer: AudioBuffer,
    targetDuration: number
  ): Promise<AudioBuffer> {
    const { sampleRate } = audioBuffer
    const targetLength = Math.round(targetDuration * sampleRate)

    if (Math.abs(audioBuffer.length - targetLength) <= 1) {
      return audioBuffer
    }

    const offlineCtx = new OfflineAudioContext(
      audioBuffer.numberOfChannels,
      targetLength,
      sampleRate
    )

    const source = offlineCtx.createBufferSource()
    source.buffer = audioBuffer
    source.playbackRate.value = audioBuffer.length / targetLength
    source.connect(offlineCtx.destination)
    source.start()

    return offlineCtx.startRendering()
  }

  alignAndMixTracks(
    tracks: Array<{
      id: string
      clips: Array<{
        id: string
        startTime: number
        endTime: number
        offset: number
        sampleRate: number
        duration: number
        volume: number
      }>
      volume: number
    }>,
    targetSampleRate: number = this.config.targetSampleRate
  ): Array<{
    trackId: string
    syncedClips: SyncedClip[]
    trackDrift: number
  }> {
    return tracks.map((track) => {
      const { syncedClips, totalDrift } = this.syncMultipleClips(track.clips)

      return {
        trackId: track.id,
        syncedClips,
        trackDrift: totalDrift,
      }
    })
  }

  getConfig(): AudioTimeSyncConfig {
    return { ...this.config }
  }

  setConfig(config: Partial<AudioTimeSyncConfig>) {
    this.config = { ...this.config, ...config }
  }

  clearDriftHistory() {
    this.driftHistory.clear()
  }
}

export const audioTimeSynchronizer = new AudioTimeSynchronizer()

export function formatDrift(driftMs: number): string {
  const absDrift = Math.abs(driftMs)
  if (absDrift < 1) return `±${(driftMs * 1000).toFixed(2)}µs`
  if (absDrift < 1000) return `${driftMs > 0 ? '+' : ''}${driftMs.toFixed(2)}ms`
  return `${driftMs > 0 ? '+' : ''}${(driftMs / 1000).toFixed(3)}s`
}

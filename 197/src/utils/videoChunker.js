import { fetchFile } from '@ffmpeg/util'

const DEFAULT_CHUNK_DURATION = 30
const MIN_CHUNK_DURATION = 10
const MAX_CHUNK_DURATION = 120
const LARGE_FILE_THRESHOLD = 500 * 1024 * 1024
const LARGE_DURATION_THRESHOLD = 30 * 60

export class VideoChunker {
  constructor(ffmpegService) {
    this.ffmpeg = ffmpegService
    this.activeChunks = new Map()
    this.processedChunks = new Map()
  }

  isLargeFile(file, duration = 0) {
    return file.size > LARGE_FILE_THRESHOLD || duration > LARGE_DURATION_THRESHOLD
  }

  calculateOptimalChunks(duration, fileSize, preferredChunkDuration = null) {
    let chunkDuration = preferredChunkDuration || DEFAULT_CHUNK_DURATION
    
    if (fileSize > 1024 * 1024 * 1024) {
      chunkDuration = Math.max(MIN_CHUNK_DURATION, chunkDuration * 0.5)
    } else if (fileSize > 2 * 1024 * 1024 * 1024) {
      chunkDuration = Math.max(MIN_CHUNK_DURATION, chunkDuration * 0.33)
    }
    
    chunkDuration = Math.max(MIN_CHUNK_DURATION, Math.min(MAX_CHUNK_DURATION, chunkDuration))
    
    const chunks = []
    let startTime = 0
    let chunkIndex = 0
    
    while (startTime < duration) {
      const endTime = Math.min(startTime + chunkDuration, duration)
      const actualDuration = endTime - startTime
      
      if (actualDuration < MIN_CHUNK_DURATION && chunks.length > 0) {
        chunks[chunks.length - 1].endTime = endTime
        chunks[chunks.length - 1].duration = endTime - chunks[chunks.length - 1].startTime
        break
      }
      
      chunks.push({
        index: chunkIndex,
        startTime,
        endTime,
        duration: actualDuration,
        file: null,
        processed: false,
        status: 'pending',
      })
      
      startTime = endTime
      chunkIndex++
    }
    
    return chunks
  }

  async splitVideo(inputFile, chunks, onProgress = null) {
    const results = []
    const ext = this.getExtension(inputFile.name)
    
    for (let i = 0; i < chunks.length; i++) {
      const chunk = chunks[i]
      const chunkId = `${inputFile.name}_chunk_${chunk.index}`
      
      try {
        chunk.status = 'processing'
        if (onProgress) {
          onProgress({
            type: 'chunk_start',
            chunkIndex: i,
            totalChunks: chunks.length,
            chunk,
          })
        }
        
        const inputName = `split_input_${Date.now()}${ext}`
        const outputName = `chunk_${chunk.index}_${Date.now()}.mp4`
        
        await this.ffmpeg.writeFile(inputName, await fetchFile(inputFile))
        
        await this.ffmpeg.exec(
          '-ss', chunk.startTime.toString(),
          '-i', inputName,
          '-t', chunk.duration.toString(),
          '-c:v', 'libx264',
          '-c:a', 'aac',
          '-preset', 'fast',
          '-movflags', '+faststart',
          '-y',
          outputName
        )
        
        const data = await this.ffmpeg.readFile(outputName)
        const blob = new Blob([data], { type: 'video/mp4' })
        const chunkFile = new File([blob], `chunk_${chunk.index}.mp4`, { type: 'video/mp4' })
        
        chunk.file = chunkFile
        chunk.url = URL.createObjectURL(chunkFile)
        chunk.processed = true
        chunk.status = 'completed'
        chunk.size = blob.size
        
        this.activeChunks.set(chunkId, chunk)
        results.push(chunk)
        
        await this.ffmpeg.deleteFile(inputName)
        await this.ffmpeg.deleteFile(outputName)
        
        if (onProgress) {
          onProgress({
            type: 'chunk_complete',
            chunkIndex: i,
            totalChunks: chunks.length,
            progress: (i + 1) / chunks.length,
            chunk,
          })
        }
        
      } catch (error) {
        chunk.status = 'error'
        chunk.error = error
        console.error(`Chunk ${chunk.index} processing failed:`, error)
        
        if (onProgress) {
          onProgress({
            type: 'chunk_error',
            chunkIndex: i,
            totalChunks: chunks.length,
            chunk,
            error,
          })
        }
        
        throw error
      }
    }
    
    return results
  }

  async processChunk(chunk, operation, params, onProgress = null) {
    const chunkId = `${chunk.file.name}_${operation}`
    
    try {
      if (onProgress) {
        onProgress({ type: 'operation_start', chunk, operation })
      }
      
      let resultBlob
      
      switch (operation) {
        case 'trim':
          resultBlob = await this.ffmpeg.trimVideo(
            chunk.file,
            params.trimStart,
            params.trimEnd,
            (p) => onProgress && onProgress({ ...p, chunk, operation })
          )
          break
          
        case 'addSubtitles':
          resultBlob = await this.ffmpeg.addSubtitles(
            chunk.file,
            params.subtitles,
            (p) => onProgress && onProgress({ ...p, chunk, operation })
          )
          break
          
        case 'addTransition':
          resultBlob = await this.ffmpeg.addTransition(
            chunk.file,
            params.nextFile,
            params.transitionType,
            params.duration,
            (p) => onProgress && onProgress({ ...p, chunk, operation })
          )
          break
          
        default:
          throw new Error(`Unknown operation: ${operation}`)
      }
      
      const resultFile = new File(
        [resultBlob], 
        `${operation}_${chunk.file.name}`, 
        { type: 'video/mp4' }
      )
      
      this.processedChunks.set(chunkId, {
        chunk,
        operation,
        params,
        resultFile,
        resultUrl: URL.createObjectURL(resultFile),
      })
      
      if (onProgress) {
        onProgress({ type: 'operation_complete', chunk, operation, resultFile })
      }
      
      return resultFile
      
    } catch (error) {
      console.error(`Chunk operation ${operation} failed:`, error)
      throw error
    }
  }

  async mergeChunks(chunks, outputFileName = 'merged_video.mp4', onProgress = null) {
    if (chunks.length === 0) {
      throw new Error('No chunks to merge')
    }
    
    if (chunks.length === 1) {
      return chunks[0].file
    }
    
    try {
      if (onProgress) {
        onProgress({ type: 'merge_start', totalChunks: chunks.length })
      }
      
      const files = chunks.map(c => c.file)
      const resultBlob = await this.ffmpeg.concatVideos(
        files,
        (p) => onProgress && onProgress({ ...p, type: 'merge_progress' })
      )
      
      const resultFile = new File([resultBlob], outputFileName, { type: 'video/mp4' })
      
      if (onProgress) {
        onProgress({ 
          type: 'merge_complete', 
          totalChunks: chunks.length,
          fileSize: resultFile.size,
        })
      }
      
      return resultFile
      
    } catch (error) {
      console.error('Merge chunks failed:', error)
      throw error
    }
  }

  async processLargeVideo(inputFile, duration, operation, params, onProgress = null) {
    const isLarge = this.isLargeFile(inputFile, duration)
    
    if (!isLarge) {
      if (onProgress) {
        onProgress({ type: 'skip_chunking', reason: 'file_not_large' })
      }
      
      switch (operation) {
        case 'trim':
          return await this.ffmpeg.trimVideo(inputFile, params.trimStart, params.trimEnd, onProgress)
        case 'addSubtitles':
          return await this.ffmpeg.addSubtitles(inputFile, params.subtitles, onProgress)
        case 'export':
          return await this.ffmpeg.exportProject(params.clips, params.totalDuration, onProgress)
        default:
          throw new Error(`Unknown operation: ${operation}`)
      }
    }
    
    if (onProgress) {
      onProgress({ type: 'chunking_start', fileSize: inputFile.size, duration })
    }
    
    const chunks = this.calculateOptimalChunks(duration, inputFile.size)
    
    if (onProgress) {
      onProgress({ type: 'chunking_plan', totalChunks: chunks.length, chunks })
    }
    
    await this.splitVideo(inputFile, chunks, (p) => {
      if (onProgress) {
        onProgress({ ...p, phase: 'splitting' })
      }
    })
    
    if (operation === 'trim') {
      const adjustedChunks = this.adjustChunksForTrim(chunks, params.trimStart, params.trimEnd)
      
      for (let i = 0; i < adjustedChunks.length; i++) {
        const chunk = adjustedChunks[i]
        if (chunk.needsProcessing) {
          await this.processChunk(
            chunk, 
            'trim', 
            { trimStart: chunk.localTrimStart, trimEnd: chunk.localTrimEnd },
            (p) => onProgress && onProgress({ ...p, phase: 'processing' })
          )
        }
      }
      
      const resultFile = await this.mergeChunks(
        adjustedChunks.filter(c => c.includeInOutput),
        'trimmed_video.mp4',
        (p) => onProgress && onProgress({ ...p, phase: 'merging' })
      )
      
      this.cleanup()
      return resultFile
      
    } else if (operation === 'export') {
      return await this.processChunksForExport(chunks, params, onProgress)
    }
    
    this.cleanup()
    return null
  }

  adjustChunksForTrim(chunks, globalTrimStart, globalTrimEnd) {
    return chunks.map(chunk => {
      const adjusted = { ...chunk }
      
      if (chunk.endTime <= globalTrimStart) {
        adjusted.includeInOutput = false
        adjusted.needsProcessing = false
        return adjusted
      }
      
      if (chunk.startTime >= globalTrimEnd) {
        adjusted.includeInOutput = false
        adjusted.needsProcessing = false
        return adjusted
      }
      
      adjusted.includeInOutput = true
      
      const localTrimStart = Math.max(0, globalTrimStart - chunk.startTime)
      const localTrimEnd = Math.min(chunk.duration, globalTrimEnd - chunk.startTime)
      
      adjusted.localTrimStart = localTrimStart
      adjusted.localTrimEnd = localTrimEnd
      adjusted.needsProcessing = localTrimStart > 0 || localTrimEnd < chunk.duration
      
      return adjusted
    })
  }

  async processChunksForExport(chunks, params, onProgress = null) {
    const { clips, subtitles, backgroundMusic } = params
    
    const processedClips = []
    
    for (let i = 0; i < clips.length; i++) {
      const clip = clips[i]
      
      if (this.isLargeFile(clip.file, clip.originalDuration)) {
        if (onProgress) {
          onProgress({ 
            type: 'clip_chunking', 
            clipIndex: i, 
            clipName: clip.name 
          })
        }
        
        const clipChunks = this.calculateOptimalChunks(
          clip.originalDuration, 
          clip.file.size
        )
        
        await this.splitVideo(clip.file, clipChunks, (p) => {
          if (onProgress) {
            onProgress({ ...p, phase: 'splitting_clip', clipIndex: i })
          }
        })
        
        const adjustedChunks = this.adjustChunksForTrim(
          clipChunks, 
          clip.trimStart, 
          clip.trimEnd
        )
        
        for (const chunk of adjustedChunks) {
          if (chunk.includeInOutput) {
            if (chunk.needsProcessing) {
              const processedFile = await this.processChunk(
                chunk,
                'trim',
                { trimStart: chunk.localTrimStart, trimEnd: chunk.localTrimEnd }
              )
              processedClips.push({
                ...clip,
                file: processedFile,
                url: URL.createObjectURL(processedFile),
                startTime: chunk.globalStartTime,
                duration: chunk.localTrimEnd - chunk.localTrimStart,
              })
            } else {
              processedClips.push({
                ...clip,
                file: chunk.file,
                url: chunk.url,
                startTime: chunk.startTime,
                duration: chunk.duration,
              })
            }
          }
        }
      } else {
        processedClips.push(clip)
      }
    }
    
    if (onProgress) {
      onProgress({ type: 'final_export', clipCount: processedClips.length })
    }
    
    const result = await this.ffmpeg.exportProject(
      processedClips,
      params.totalDuration,
      (p) => onProgress && onProgress({ ...p, phase: 'exporting' })
    )
    
    this.cleanup()
    return result
  }

  getExtension(filename) {
    const ext = filename.split('.').pop().toLowerCase()
    return '.' + ext
  }

  cleanup() {
    for (const chunk of this.activeChunks.values()) {
      if (chunk.url) {
        URL.revokeObjectURL(chunk.url)
      }
    }
    for (const processed of this.processedChunks.values()) {
      if (processed.resultUrl) {
        URL.revokeObjectURL(processed.resultUrl)
      }
    }
    this.activeChunks.clear()
    this.processedChunks.clear()
  }

  getMemoryUsage() {
    let totalSize = 0
    for (const chunk of this.activeChunks.values()) {
      totalSize += chunk.size || 0
    }
    for (const processed of this.processedChunks.values()) {
      totalSize += processed.resultFile?.size || 0
    }
    return {
      activeChunks: this.activeChunks.size,
      processedChunks: this.processedChunks.size,
      totalSize,
      formattedSize: this.formatBytes(totalSize),
    }
  }

  formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB'
  }
}

export default VideoChunker

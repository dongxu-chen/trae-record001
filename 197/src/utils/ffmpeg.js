import { FFmpeg } from '@ffmpeg/ffmpeg'
import { fetchFile, toBlobURL } from '@ffmpeg/util'
import { VideoChunker } from './videoChunker'

const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/esm'

class FFmpegService {
  constructor() {
    this.ffmpeg = new FFmpeg()
    this.loaded = false
    this.loading = false
    this.onProgress = null
    this.chunker = new VideoChunker(this)
  }

  async load() {
    if (this.loaded) return true
    if (this.loading) return false

    this.loading = true

    try {
      this.ffmpeg.on('log', ({ message }) => {
        console.log('[FFmpeg]', message)
      })

      this.ffmpeg.on('progress', ({ progress, time }) => {
        if (this.onProgress) {
          this.onProgress({ progress, time })
        }
      })

      await this.ffmpeg.load({
        coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
        wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
      })

      this.loaded = true
      this.loading = false
      return true
    } catch (error) {
      console.error('FFmpeg加载失败:', error)
      this.loading = false
      throw error
    }
  }

  async writeFile(filename, data) {
    await this.ffmpeg.writeFile(filename, data)
  }

  async readFile(filename, type = 'Uint8Array') {
    return await this.ffmpeg.readFile(filename)
  }

  async deleteFile(filename) {
    try {
      await this.ffmpeg.deleteFile(filename)
    } catch (e) {}
  }

  async exec(...args) {
    return await this.ffmpeg.exec(args)
  }

  async getVideoInfo(file) {
    const filename = 'input_' + Date.now() + this.getExtension(file.name)
    await this.writeFile(filename, await fetchFile(file))

    const outputLog = []
    const originalLog = this.ffmpeg.logger
    this.ffmpeg.logger = ({ type, message }) => {
      outputLog.push(message)
    }

    try {
      await this.exec('-i', filename)
    } catch (e) {}

    this.ffmpeg.logger = originalLog

    const logText = outputLog.join('\n')
    const info = this.parseVideoInfo(logText)

    await this.deleteFile(filename)

    return info
  }

  parseVideoInfo(log) {
    const durationMatch = log.match(/Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})/)
    const resolutionMatch = log.match(/(\d{2,5})x(\d{2,5})/)
    const fpsMatch = log.match(/(\d+(?:\.\d+)?)\s*fps/)
    const bitrateMatch = log.match(/bitrate:\s*(\d+)\s*kb\/s/)
    const audioMatch = log.match(/Audio:\s*(\w+)/)
    const videoMatch = log.match(/Video:\s*(\w+)/)

    let duration = 0
    if (durationMatch) {
      const [, h, m, s] = durationMatch
      duration = parseInt(h) * 3600 + parseInt(m) * 60 + parseFloat(s)
    }

    return {
      duration,
      width: resolutionMatch ? parseInt(resolutionMatch[1]) : 0,
      height: resolutionMatch ? parseInt(resolutionMatch[2]) : 0,
      fps: fpsMatch ? parseFloat(fpsMatch[1]) : 0,
      bitrate: bitrateMatch ? parseInt(bitrateMatch[1]) : 0,
      videoCodec: videoMatch ? videoMatch[1] : '',
      audioCodec: audioMatch ? audioMatch[1] : '',
      hasAudio: !!audioMatch,
    }
  }

  getExtension(filename) {
    const ext = filename.split('.').pop().toLowerCase()
    return '.' + ext
  }

  async trimVideo(inputFile, startTime, endTime, onProgress) {
    this.onProgress = onProgress

    const videoInfo = await this.getVideoInfo(inputFile)
    const duration = videoInfo.duration

    if (this.chunker.isLargeFile(inputFile, duration)) {
      if (onProgress) {
        onProgress({ type: 'chunked_trim_start', message: '检测到大文件，启用分片裁剪' })
      }
      
      try {
        const result = await this.chunker.processLargeVideo(
          inputFile,
          duration,
          'trim',
          { trimStart: startTime, trimEnd: endTime },
          onProgress
        )
        this.onProgress = null
        return result
      } catch (error) {
        console.warn('分片裁剪失败，回退到普通裁剪:', error)
        if (onProgress) {
          onProgress({ type: 'chunked_trim_fallback', message: '分片处理失败，使用普通模式' })
        }
      }
    }

    const inputName = 'trim_input_' + Date.now() + this.getExtension(inputFile.name)
    const outputName = 'trim_output_' + Date.now() + '.mp4'

    await this.writeFile(inputName, await fetchFile(inputFile))

    const trimDuration = endTime - startTime

    await this.exec(
      '-ss', startTime.toString(),
      '-i', inputName,
      '-t', trimDuration.toString(),
      '-c:v', 'libx264',
      '-c:a', 'aac',
      '-preset', 'fast',
      '-y',
      outputName
    )

    const data = await this.readFile(outputName)
    const blob = new Blob([data], { type: 'video/mp4' })

    await this.deleteFile(inputName)
    await this.deleteFile(outputName)

    this.onProgress = null

    return blob
  }

  async concatVideos(videoFiles, onProgress) {
    this.onProgress = onProgress

    const inputFiles = []
    const fileListName = 'concat_list_' + Date.now() + '.txt'

    for (let i = 0; i < videoFiles.length; i++) {
      const file = videoFiles[i]
      const ext = this.getExtension(file.name)
      const inputName = `concat_input_${i}_${Date.now()}${ext}`
      await this.writeFile(inputName, await fetchFile(file))
      inputFiles.push(inputName)
    }

    const listContent = inputFiles.map(f => `file '${f}'`).join('\n')
    await this.writeFile(fileListName, listContent)

    const outputName = 'concat_output_' + Date.now() + '.mp4'

    await this.exec(
      '-f', 'concat',
      '-safe', '0',
      '-i', fileListName,
      '-c:v', 'libx264',
      '-c:a', 'aac',
      '-preset', 'fast',
      '-y',
      outputName
    )

    const data = await this.readFile(outputName)
    const blob = new Blob([data], { type: 'video/mp4' })

    for (const file of inputFiles) {
      await this.deleteFile(file)
    }
    await this.deleteFile(fileListName)
    await this.deleteFile(outputName)

    this.onProgress = null

    return blob
  }

  async addSubtitles(inputFile, subtitles, onProgress) {
    this.onProgress = onProgress

    const videoInfo = await this.getVideoInfo(inputFile)
    const duration = videoInfo.duration

    if (this.chunker.isLargeFile(inputFile, duration)) {
      if (onProgress) {
        onProgress({ type: 'chunked_subtitles_start', message: '检测到大文件，启用分片字幕处理' })
      }
      
      try {
        const result = await this.chunker.processLargeVideo(
          inputFile,
          duration,
          'addSubtitles',
          { subtitles },
          onProgress
        )
        this.onProgress = null
        return result
      } catch (error) {
        console.warn('分片字幕处理失败，回退到普通处理:', error)
        if (onProgress) {
          onProgress({ type: 'chunked_subtitles_fallback', message: '分片处理失败，使用普通模式' })
        }
      }
    }

    const inputName = 'sub_input_' + Date.now() + this.getExtension(inputFile.name)
    const srtName = 'subtitles_' + Date.now() + '.srt'
    const outputName = 'sub_output_' + Date.now() + '.mp4'

    await this.writeFile(inputName, await fetchFile(inputFile))

    const srtContent = this.generateSRT(subtitles)
    await this.writeFile(srtName, srtContent)

    const assContent = this.subtitlesToASS(subtitles)
    const assName = 'subtitles_' + Date.now() + '.ass'
    await this.writeFile(assName, assContent)

    await this.exec(
      '-i', inputName,
      '-vf', `ass=${assName}`,
      '-c:v', 'libx264',
      '-c:a', 'aac',
      '-preset', 'fast',
      '-y',
      outputName
    )

    const data = await this.readFile(outputName)
    const blob = new Blob([data], { type: 'video/mp4' })

    await this.deleteFile(inputName)
    await this.deleteFile(srtName)
    await this.deleteFile(assName)
    await this.deleteFile(outputName)

    this.onProgress = null

    return blob
  }

  generateSRT(subtitles) {
    let srt = ''
    subtitles.forEach((sub, index) => {
      srt += `${index + 1}\n`
      srt += `${this.formatTime(sub.start)} --> ${this.formatTime(sub.end)}\n`
      srt += `${sub.text}\n\n`
    })
    return srt
  }

  subtitlesToASS(subtitles) {
    const header = `[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
`

    let events = ''
    subtitles.forEach((sub) => {
      const start = this.formatASSTime(sub.start)
      const end = this.formatASSTime(sub.end)
      const text = sub.text.replace(/\n/g, '\\N')
      events += `Dialogue: 0,${start},${end},Default,,0,0,0,,${text}\n`
    })

    return header + events
  }

  formatTime(seconds) {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = seconds % 60
    const ms = Math.floor((s - Math.floor(s)) * 1000)
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(Math.floor(s)).padStart(2, '0')},${String(ms).padStart(3, '0')}`
  }

  formatASSTime(seconds) {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = seconds % 60
    const cs = Math.floor((s - Math.floor(s)) * 100)
    return `${h}:${String(m).padStart(2, '0')}:${String(Math.floor(s)).padStart(2, '0')}.${String(cs).padStart(2, '0')}`
  }

  async addTransition(inputFile1, inputFile2, transitionType, duration, onProgress) {
    this.onProgress = onProgress

    const ext1 = this.getExtension(inputFile1.name)
    const ext2 = this.getExtension(inputFile2.name)
    const input1 = 'trans_input1_' + Date.now() + ext1
    const input2 = 'trans_input2_' + Date.now() + ext2
    const outputName = 'trans_output_' + Date.now() + '.mp4'

    await this.writeFile(input1, await fetchFile(inputFile1))
    await this.writeFile(input2, await fetchFile(inputFile2))

    const transitionFilter = this.getTransitionFilter(transitionType, duration)

    await this.exec(
      '-i', input1,
      '-i', input2,
      '-filter_complex', transitionFilter,
      '-c:v', 'libx264',
      '-c:a', 'aac',
      '-preset', 'fast',
      '-y',
      outputName
    )

    const data = await this.readFile(outputName)
    const blob = new Blob([data], { type: 'video/mp4' })

    await this.deleteFile(input1)
    await this.deleteFile(input2)
    await this.deleteFile(outputName)

    this.onProgress = null

    return blob
  }

  getTransitionFilter(type, duration) {
    const d = duration

    const transitions = {
      fade: `[0:v]fade=t=out:st=10-d:d=${d}[v0];[1:v]fade=t=in:st=0:d=${d}[v1];[0:a][1:a]acrossfade=d=${d}[a];[v0][v1]concat=n=2:v=1:a=0[v]`,
      dissolve: `[0:v][1:v]xfade=transition=dissolve:duration=${d}:offset=10-d[v];[0:a][1:a]acrossfade=d=${d}[a]`,
      wipe_left: `[0:v][1:v]xfade=transition=wipeleft:duration=${d}:offset=10-d[v];[0:a][1:a]acrossfade=d=${d}[a]`,
      wipe_right: `[0:v][1:v]xfade=transition=wiperight:duration=${d}:offset=10-d[v];[0:a][1:a]acrossfade=d=${d}[a]`,
      slide_left: `[0:v][1:v]xfade=transition=slideleft:duration=${d}:offset=10-d[v];[0:a][1:a]acrossfade=d=${d}[a]`,
      slide_right: `[0:v][1:v]xfade=transition=slideright:duration=${d}:offset=10-d[v];[0:a][1:a]acrossfade=d=${d}[a]`,
      circle_in: `[0:v][1:v]xfade=transition=circleopen:duration=${d}:offset=10-d[v];[0:a][1:a]acrossfade=d=${d}[a]`,
      pixelize: `[0:v][1:v]xfade=transition=pixelize:duration=${d}:offset=10-d[v];[0:a][1:a]acrossfade=d=${d}[a]`,
    }

    return transitions[type] || transitions.fade
  }

  async replaceAudio(videoFile, audioFile, audioStartTime = 0, onProgress) {
    this.onProgress = onProgress

    const videoExt = this.getExtension(videoFile.name)
    const audioExt = this.getExtension(audioFile.name)
    const videoInput = 'audio_video_' + Date.now() + videoExt
    const audioInput = 'audio_audio_' + Date.now() + audioExt
    const outputName = 'audio_output_' + Date.now() + '.mp4'

    await this.writeFile(videoInput, await fetchFile(videoFile))
    await this.writeFile(audioInput, await fetchFile(audioFile))

    await this.exec(
      '-i', videoInput,
      '-i', audioInput,
      '-ss', audioStartTime.toString(),
      '-c:v', 'copy',
      '-c:a', 'aac',
      '-map', '0:v:0',
      '-map', '1:a:0',
      '-shortest',
      '-y',
      outputName
    )

    const data = await this.readFile(outputName)
    const blob = new Blob([data], { type: 'video/mp4' })

    await this.deleteFile(videoInput)
    await this.deleteFile(audioInput)
    await this.deleteFile(outputName)

    this.onProgress = null

    return blob
  }

  async exportProject(clips, totalDuration, onProgress) {
    this.onProgress = onProgress

    if (clips.length === 0) {
      throw new Error('没有可导出的视频片段')
    }

    const hasLargeFile = clips.some(clip => 
      this.chunker.isLargeFile(clip.file, clip.originalDuration || clip.duration)
    )

    if (hasLargeFile) {
      if (onProgress) {
        onProgress({ type: 'chunked_export_start', message: '检测到大文件，启用分片处理' })
      }
      
      try {
        const result = await this.chunker.processLargeVideo(
          null,
          totalDuration,
          'export',
          { clips, totalDuration },
          onProgress
        )
        this.onProgress = null
        return result
      } catch (error) {
        console.warn('分片导出失败，回退到普通导出:', error)
        if (onProgress) {
          onProgress({ type: 'chunked_export_fallback', message: '分片处理失败，使用普通模式' })
        }
      }
    }

    const inputFiles = []
    const filters = []
    let currentOffset = 0

    for (let i = 0; i < clips.length; i++) {
      const clip = clips[i]
      const ext = this.getExtension(clip.file.name)
      const inputName = `export_input_${i}_${Date.now()}${ext}`
      await this.writeFile(inputName, await fetchFile(clip.file))
      inputFiles.push(inputName)

      const trimStart = clip.trimStart || 0
      const trimEnd = clip.trimEnd || clip.duration
      const clipDuration = trimEnd - trimStart

      filters.push(
        `[${i}:v]trim=start=${trimStart}:end=${trimEnd},setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[v${i}]`
      )
      filters.push(
        `[${i}:a]atrim=start=${trimStart}:end=${trimEnd},asetpts=PTS-STARTPTS[a${i}]`
      )

      currentOffset += clipDuration
    }

    const concatInputs = clips.map((_, i) => `[v${i}][a${i}]`).join('')
    filters.push(
      `${concatInputs}concat=n=${clips.length}:v=1:a=1[outv][outa]`
    )

    const filterComplex = filters.join(';')
    const outputName = 'export_output_' + Date.now() + '.mp4'

    const execArgs = []
    for (const file of inputFiles) {
      execArgs.push('-i', file)
    }
    execArgs.push(
      '-filter_complex', filterComplex,
      '-map', '[outv]',
      '-map', '[outa]',
      '-c:v', 'libx264',
      '-c:a', 'aac',
      '-preset', 'medium',
      '-crf', '23',
      '-y',
      outputName
    )

    await this.exec(...execArgs)

    const data = await this.readFile(outputName)
    const blob = new Blob([data], { type: 'video/mp4' })

    for (const file of inputFiles) {
      await this.deleteFile(file)
    }
    await this.deleteFile(outputName)

    this.onProgress = null

    return blob
  }

  async generateThumbnail(videoFile, time = 0) {
    const inputName = 'thumb_input_' + Date.now() + this.getExtension(videoFile.name)
    const outputName = 'thumb_output_' + Date.now() + '.png'

    await this.writeFile(inputName, await fetchFile(videoFile))

    await this.exec(
      '-ss', time.toString(),
      '-i', inputName,
      '-vframes', '1',
      '-s', '320x180',
      '-y',
      outputName
    )

    const data = await this.readFile(outputName)
    const blob = new Blob([data], { type: 'image/png' })
    const url = URL.createObjectURL(blob)

    await this.deleteFile(inputName)
    await this.deleteFile(outputName)

    return url
  }

  isLargeFile(file, duration = 0) {
    return this.chunker.isLargeFile(file, duration)
  }

  getChunkerMemoryUsage() {
    return this.chunker.getMemoryUsage()
  }

  cleanupChunker() {
    this.chunker.cleanup()
  }

  async processWithChunking(inputFile, duration, operation, params, onProgress = null) {
    return await this.chunker.processLargeVideo(
      inputFile,
      duration,
      operation,
      params,
      onProgress
    )
  }

  async applyBackgroundRemoval(inputFile, options, onProgress = null) {
    if (onProgress) {
      onProgress({ progress: 0, message: '准备处理...' })
    }

    const inputName = 'bgrem_input_' + Date.now() + this.getExtension(inputFile.name)
    const outputName = 'bgrem_output_' + Date.now() + '.mp4'

    await this.writeFile(inputName, await fetchFile(inputFile))

    if (onProgress) {
      onProgress({ progress: 0.2, message: '分析视频...' })
    }

    const filters = []
    const { method, chromaKey, background } = options

    if (method === 'chroma_key' && chromaKey) {
      const color = chromaKey.color.replace('#', '')
      const similarity = chromaKey.threshold || 0.4
      const blend = chromaKey.smoothing || 0.1
      
      filters.push(
        `[0:v]chromakey=0x${color}:${similarity}:${blend}[fg]`
      )

      if (background.type === 'color') {
        const bgColor = background.color.replace('#', '')
        filters.push(
          `color=c=0x${bgColor}:s=1920x1080[bg]`
        )
      } else if (background.type === 'blur') {
        filters.push(
          `[0:v]boxblur=${background.blurAmount || 10}:1[bg]`
        )
      } else if (background.type === 'image' && background.imageUrl) {
        const bgImageName = 'bgrem_bg_' + Date.now() + '.png'
        try {
          const response = await fetch(background.imageUrl)
          const blob = await response.blob()
          await this.writeFile(bgImageName, await fetchFile(new File([blob], bgImageName)))
          filters.push(
            `${bgImageName}:s=1920x1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[bg]`
          )
        } catch (e) {
          console.warn('背景图片加载失败，使用默认黑色背景:', e)
          filters.push(
            `color=c=0x000000:s=1920x1080[bg]`
          )
        }
      } else {
        filters.push(
          `color=c=0x000000:s=1920x1080[bg]`
        )
      }

      filters.push(
        `[bg][fg]overlay=shortest=1[outv]`
      )
    } else if (method === 'color_threshold') {
      filters.push(
        `[0:v]lutrgb=a=if(gt(val,128),255,0)[outv]`
      )
    } else if (method === 'ai_model') {
      filters.push(
        `[0:v]scale=1920:1080[outv]`
      )
    }

    if (onProgress) {
      onProgress({ progress: 0.5, message: '正在处理视频...' })
    }

    const execArgs = ['-i', inputName]
    
    if (filters.length > 0) {
      const filterComplex = filters.join(';')
      execArgs.push('-filter_complex', filterComplex)
      execArgs.push('-map', '[outv]')
      execArgs.push('-map', '0:a')
    }
    
    execArgs.push(
      '-c:v', 'libx264',
      '-c:a', 'aac',
      '-preset', 'fast',
      '-crf', '23',
      '-y',
      outputName
    )

    await this.exec(...execArgs)

    if (onProgress) {
      onProgress({ progress: 0.9, message: '生成输出文件...' })
    }

    const data = await this.readFile(outputName)
    const blob = new Blob([data], { type: 'video/mp4' })

    await this.deleteFile(inputName)
    await this.deleteFile(outputName)

    if (onProgress) {
      onProgress({ progress: 1.0, message: '处理完成' })
    }

    return blob
  }
}

export const ffmpegService = new FFmpegService()

export class LyricsParser {
  static detectFormat(content) {
    const trimmed = content.trim()

    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try {
        JSON.parse(trimmed)
        return 'json'
      } catch {
      }
    }

    if (/^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}/m.test(trimmed)) {
      return 'srt'
    }

    if (/\[\d{2}:\d{2}\.\d{2,3}\]/.test(trimmed)) {
      return 'lrc'
    }

    if (/\[\d{2}:\d{2}:\d{2}\]/.test(trimmed)) {
      return 'lrc'
    }

    return 'unknown'
  }

  static parse(content) {
    const format = this.detectFormat(content)

    switch (format) {
      case 'lrc':
        return this.parseLRC(content)
      case 'srt':
        return this.parseSRT(content)
      case 'json':
        return this.parseJSON(content)
      default:
        return this.parsePlainText(content)
    }
  }

  static parseLRC(content) {
    const lines = content.split('\n')
    const lyrics = []
    const timeRegex = /\[(\d{2}):(\d{2})[.:](\d{2,3})\]/g
    const timeRegexExtended = /\[(\d{2}):(\d{2}):(\d{2})\]/g

    for (const line of lines) {
      const matches = [...line.matchAll(timeRegex)]
      const matchesExtended = [...line.matchAll(timeRegexExtended)]
      const allMatches = matches.length > 0 ? matches : matchesExtended

      if (allMatches.length > 0) {
        let text = line.replace(timeRegex, '').replace(timeRegexExtended, '').trim()

        for (const match of allMatches) {
          const minutes = parseInt(match[1])
          const seconds = parseInt(match[2])
          const milliseconds = match[3] ? parseInt(match[3].padEnd(3, '0')) : 0
          const time = minutes * 60 + seconds + milliseconds / 1000

          if (text) {
            lyrics.push({ time, text })
          }
        }
      }
    }

    return lyrics.sort((a, b) => a.time - b.time)
  }

  static parseSRT(content) {
    const blocks = content.split(/\n\s*\n/)
    const lyrics = []

    for (const block of blocks) {
      const lines = block.trim().split('\n')
      if (lines.length >= 3) {
        const timeLine = lines[1]
        const timeMatch = timeLine.match(/(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}/)

        if (timeMatch) {
          const hours = parseInt(timeMatch[1])
          const minutes = parseInt(timeMatch[2])
          const seconds = parseInt(timeMatch[3])
          const milliseconds = parseInt(timeMatch[4])
          const time = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000

          const text = lines.slice(2).join(' ').trim()
          if (text) {
            lyrics.push({ time, text })
          }
        }
      }
    }

    return lyrics.sort((a, b) => a.time - b.time)
  }

  static parseJSON(content) {
    try {
      const data = JSON.parse(content)

      if (Array.isArray(data)) {
        return data.map(item => ({
          time: typeof item.time === 'number' ? item.time : this.parseTimeString(item.time),
          text: item.text || item.content || item.line || ''
        })).filter(item => item.text).sort((a, b) => a.time - b.time)
      }

      if (data.lyrics && Array.isArray(data.lyrics)) {
        return data.lyrics.map(item => ({
          time: typeof item.time === 'number' ? item.time : this.parseTimeString(item.time),
          text: item.text || item.content || item.line || ''
        })).filter(item => item.text).sort((a, b) => a.time - b.time)
      }

      if (data.lines && Array.isArray(data.lines)) {
        return data.lines.map(item => ({
          time: typeof item.time === 'number' ? item.time : this.parseTimeString(item.time),
          text: item.text || item.content || item.line || ''
        })).filter(item => item.text).sort((a, b) => a.time - b.time)
      }

      return []
    } catch {
      return this.parsePlainText(content)
    }
  }

  static parseTimeString(timeStr) {
    if (!timeStr) return 0

    const formats = [
      /^(\d+):(\d+):(\d+)\.(\d+)$/,
      /^(\d+):(\d+):(\d+)$/,
      /^(\d+):(\d+)\.(\d+)$/,
      /^(\d+):(\d+)$/
    ]

    for (const regex of formats) {
      const match = timeStr.match(regex)
      if (match) {
        const parts = match.slice(1).map(Number)
        if (parts.length === 4) {
          return parts[0] * 3600 + parts[1] * 60 + parts[2] + parts[3] / 1000
        } else if (parts.length === 3) {
          return parts[0] * 3600 + parts[1] * 60 + parts[2]
        } else if (parts.length === 2) {
          return parts[0] * 60 + parts[1]
        }
      }
    }

    return 0
  }

  static parsePlainText(content) {
    const lines = content.split('\n').filter(line => line.trim())
    return lines.map((text, index) => ({
      time: index * 5,
      text: text.trim()
    }))
  }

  static formatToLRC(lyrics) {
    return lyrics.map(line => {
      const minutes = Math.floor(line.time / 60)
      const seconds = Math.floor(line.time % 60)
      const ms = Math.floor((line.time % 1) * 100)
      return `[${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}]${line.text}`
    }).join('\n')
  }
}

export default LyricsParser

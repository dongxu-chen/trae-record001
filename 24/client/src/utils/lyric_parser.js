export function parseLRC(lrcContent) {
  if (!lrcContent || typeof lrcContent !== 'string') {
    return []
  }

  const lines = lrcContent.split('\n')
  const lyrics = []

  const timeTagRegex = /\[(\d{1,2}):(\d{1,2})(?:\.(\d{1,3}))?\]/g

  for (const line of lines) {
    const trimmedLine = line.trim()
    if (!trimmedLine) continue

    const timeTags = []
    let match
    let lastIndex = 0

    while ((match = timeTagRegex.exec(trimmedLine)) !== null) {
      const minutes = parseInt(match[1], 10)
      const seconds = parseInt(match[2], 10)
      const milliseconds = match[3] ? parseInt(match[3].padEnd(3, '0'), 10) : 0

      const time = minutes * 60 + seconds + milliseconds / 1000
      timeTags.push(time)
      lastIndex = match.index + match[0].length
    }

    const text = trimmedLine.substring(lastIndex).trim()

    if (text && timeTags.length > 0) {
      for (const time of timeTags) {
        lyrics.push({ time, text })
      }
    }
  }

  lyrics.sort((a, b) => a.time - b.time)

  return lyrics
}

export function findCurrentLyricIndex(lyrics, currentTime) {
  if (!lyrics || lyrics.length === 0) {
    return -1
  }

  let left = 0
  let right = lyrics.length - 1
  let result = -1

  while (left <= right) {
    const mid = Math.floor((left + right) / 2)

    if (lyrics[mid].time <= currentTime) {
      result = mid
      left = mid + 1
    } else {
      right = mid - 1
    }
  }

  return result
}

export function formatLRC(lyrics) {
  if (!lyrics || lyrics.length === 0) {
    return ''
  }

  return lyrics
    .map(lyric => {
      const minutes = Math.floor(lyric.time / 60)
      const seconds = Math.floor(lyric.time % 60)
      const milliseconds = Math.floor((lyric.time % 1) * 1000)

      const timeStr = `[${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}.${String(milliseconds).padStart(3, '0')}]`

      return `${timeStr}${lyric.text}`
    })
    .join('\n')
}

export default {
  parseLRC,
  findCurrentLyricIndex,
  formatLRC
}

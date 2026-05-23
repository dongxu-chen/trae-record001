export function parseLRC(lrcText) {
  const lines = lrcText.split('\n')
  const lyrics = []
  
  const timeRegex = /\[(\d{2}):(\d{2})\.(\d{2,3})\]/g
  
  lines.forEach(line => {
    const matches = [...line.matchAll(timeRegex)]
    if (matches.length > 0) {
      const text = line.replace(timeRegex, '').trim()
      if (text) {
        matches.forEach(match => {
          const minutes = parseInt(match[1])
          const seconds = parseInt(match[2])
          const milliseconds = parseInt(match[3].padEnd(3, '0'))
          const time = minutes * 60 + seconds + milliseconds / 1000
          
          lyrics.push({ time, text })
        })
      }
    }
  })
  
  return lyrics.sort((a, b) => a.time - b.time)
}

export function findCurrentLyricIndex(lyrics, currentTime) {
  for (let i = lyrics.length - 1; i >= 0; i--) {
    if (currentTime >= lyrics[i].time) {
      return i
    }
  }
  return -1
}

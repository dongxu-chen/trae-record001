export function exportPlaylist(playlist, name = '我的歌单') {
  const exportData = {
    name,
    version: '1.0',
    exportedAt: new Date().toISOString(),
    songs: playlist.map(song => ({
      name: song.name,
      duration: song.duration,
      hasLyrics: song.lyrics && song.lyrics.length > 0
    }))
  }
  
  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${name}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function importPlaylist(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result)
        if (!data.songs || !Array.isArray(data.songs)) {
          reject(new Error('无效的歌单文件格式'))
          return
        }
        resolve(data)
      } catch (err) {
        reject(new Error('歌单文件解析失败'))
      }
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsText(file)
  })
}

export function parseNeteasePlaylist(html) {
  const songs = []
  const nameMatch = html.match(/<title>([^<]+)<\/title>/)
  const name = nameMatch ? nameMatch[1].replace(/ - 网易云音乐/g, '') : '网易云歌单'
  
  const songMatches = html.matchAll(/<li class="f-cb".*?data-singer="([^"]*)".*?data-song="([^"]*)"/g)
  for (const match of songMatches) {
    songs.push({
      name: match[2],
      artist: match[1],
      source: 'netease'
    })
  }
  
  if (songs.length === 0) {
    const altMatch = html.matchAll(/href="\/song\?id=\d+">([^<]+)<\/a>.*?<div class="text"><a href="\/artist\?id=\d+"[^>]*>([^<]+)<\/a>/g)
    for (const match of altMatch) {
      songs.push({
        name: match[1].trim(),
        artist: match[2].trim(),
        source: 'netease'
      })
    }
  }
  
  return { name, songs, source: 'netease' }
}

export function parseQQMusicPlaylist(html) {
  const songs = []
  const nameMatch = html.match(/<div class="data__name"[^>]*>([^<]+)<\/div>/)
  const name = nameMatch ? nameMatch[1].trim() : 'QQ音乐歌单'
  
  const songMatches = html.matchAll(/data-name="([^"]*)".*?data-singer="([^"]*)"/g)
  for (const match of songMatches) {
    songs.push({
      name: match[1],
      artist: match[2],
      source: 'qqmusic'
    })
  }
  
  if (songs.length === 0) {
    const altMatch = html.matchAll(/song__name"[^>]*>([^<]+)<\/a>.*?singer_name[^>]*>([^<]+)<\/a>/g)
    for (const match of altMatch) {
      songs.push({
        name: match[1].trim(),
        artist: match[2].trim(),
        source: 'qqmusic'
      })
    }
  }
  
  return { name, songs, source: 'qqmusic' }
}

export function parsePlaylistUrl(url) {
  if (url.includes('music.163.com')) {
    return { type: 'netease', url }
  }
  if (url.includes('y.qq.com') || url.includes('qq.com')) {
    return { type: 'qqmusic', url }
  }
  return { type: 'unknown', url }
}

export function formatTime(seconds) {
  if (isNaN(seconds) || !isFinite(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export function getAudioDuration(file) {
  return new Promise((resolve) => {
    const audio = new Audio()
    audio.onloadedmetadata = () => {
      resolve(audio.duration)
      URL.revokeObjectURL(audio.src)
    }
    audio.onerror = () => {
      resolve(0)
      URL.revokeObjectURL(audio.src)
    }
    audio.src = URL.createObjectURL(file)
  })
}

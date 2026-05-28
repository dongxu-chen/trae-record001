let cachedVoice: SpeechSynthesisVoice | null = null

export function isSpeechSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

export function pickChineseVoice(): SpeechSynthesisVoice | null {
  if (!isSpeechSupported()) return null
  const voices = window.speechSynthesis.getVoices()
  if (!voices || voices.length === 0) return null
  const zh = voices.find((v) => v.lang.includes('zh') || v.lang.includes('cmn'))
  if (zh) return zh
  return voices[0] ?? null
}

export function speak(text: string, rate = 1.0, pitch = 1.0) {
  if (!isSpeechSupported()) return
  try {
    window.speechSynthesis.cancel()
    if (!cachedVoice) cachedVoice = pickChineseVoice()
    const utter = new SpeechSynthesisUtterance(text)
    if (cachedVoice) utter.voice = cachedVoice
    utter.rate = rate
    utter.pitch = pitch
    utter.lang = 'zh-CN'
    window.speechSynthesis.speak(utter)
  } catch {
    /* ignore */
  }
}

export function stopSpeak() {
  if (!isSpeechSupported()) return
  try {
    window.speechSynthesis.cancel()
  } catch {
    /* ignore */
  }
}

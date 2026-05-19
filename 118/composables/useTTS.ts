export interface TTSOptions {
  rate?: number
  pitch?: number
  volume?: number
  lang?: string
}

export function useTTS() {
  const isSpeaking = ref(false)
  const isPaused = ref(false)
  const currentText = ref('')
  const voices = ref<SpeechSynthesisVoice[]>([])
  const selectedVoice = ref<SpeechSynthesisVoice | null>(null)

  const options = ref<TTSOptions>({
    rate: 1,
    pitch: 1,
    volume: 1,
    lang: 'zh-CN'
  })

  const loadVoices = () => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      voices.value = window.speechSynthesis.getVoices()
      const chineseVoice = voices.value.find(v => v.lang.includes('zh'))
      if (chineseVoice) {
        selectedVoice.value = chineseVoice
      }
    }
  }

  const speak = (text: string) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return

    stop()
    currentText.value = text

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = options.value.rate || 1
    utterance.pitch = options.value.pitch || 1
    utterance.volume = options.value.volume || 1
    utterance.lang = options.value.lang || 'zh-CN'
    
    if (selectedVoice.value) {
      utterance.voice = selectedVoice.value
    }

    utterance.onstart = () => {
      isSpeaking.value = true
      isPaused.value = false
    }

    utterance.onend = () => {
      isSpeaking.value = false
      isPaused.value = false
    }

    utterance.onerror = (event) => {
      console.error('TTS error:', event)
      isSpeaking.value = false
      isPaused.value = false
    }

    window.speechSynthesis.speak(utterance)
  }

  const pause = () => {
    if (window.speechSynthesis) {
      window.speechSynthesis.pause()
      isPaused.value = true
    }
  }

  const resume = () => {
    if (window.speechSynthesis) {
      window.speechSynthesis.resume()
      isPaused.value = false
    }
  }

  const stop = () => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel()
      isSpeaking.value = false
      isPaused.value = false
    }
  }

  const setRate = (rate: number) => {
    options.value.rate = Math.max(0.5, Math.min(2, rate))
  }

  const setPitch = (pitch: number) => {
    options.value.pitch = Math.max(0.5, Math.min(2, pitch))
  }

  const setVolume = (volume: number) => {
    options.value.volume = Math.max(0, Math.min(1, volume))
  }

  const setVoice = (voice: SpeechSynthesisVoice) => {
    selectedVoice.value = voice
    options.value.lang = voice.lang
  }

  onMounted(() => {
    loadVoices()
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = loadVoices
    }
  })

  onUnmounted(() => {
    stop()
  })

  return {
    isSpeaking,
    isPaused,
    currentText,
    voices,
    selectedVoice,
    options,
    speak,
    pause,
    resume,
    stop,
    setRate,
    setPitch,
    setVolume,
    setVoice
  }
}

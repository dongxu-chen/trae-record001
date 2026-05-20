class VisemeMapper {
    constructor() {
        this.visemes = {
            0: { name: 'sil', mouthOpen: 0, mouthWidth: 0.5 },
            1: { name: 'PP', mouthOpen: 0.1, mouthWidth: 0.3 },
            2: { name: 'FF', mouthOpen: 0.15, mouthWidth: 0.4 },
            3: { name: 'TH', mouthOpen: 0.2, mouthWidth: 0.45 },
            4: { name: 'DD', mouthOpen: 0.3, mouthWidth: 0.5 },
            5: { name: 'kk', mouthOpen: 0.25, mouthWidth: 0.48 },
            6: { name: 'CH', mouthOpen: 0.35, mouthWidth: 0.52 },
            7: { name: 'SS', mouthOpen: 0.2, mouthWidth: 0.55 },
            8: { name: 'nn', mouthOpen: 0.3, mouthWidth: 0.5 },
            9: { name: 'RR', mouthOpen: 0.35, mouthWidth: 0.48 },
            10: { name: 'aa', mouthOpen: 0.8, mouthWidth: 0.5 },
            11: { name: 'E', mouthOpen: 0.6, mouthWidth: 0.55 },
            12: { name: 'I', mouthOpen: 0.4, mouthWidth: 0.6 },
            13: { name: 'O', mouthOpen: 0.7, mouthWidth: 0.4 },
            14: { name: 'U', mouthOpen: 0.5, mouthWidth: 0.35 }
        };
        
        this.phonemeToViseme = {
            'a': 10, 'ā': 10, 'ă': 10, 'ä': 10,
            'b': 1, 'p': 1, 'm': 1,
            'f': 2, 'v': 2,
            'th': 3, 'dh': 3,
            'd': 4, 't': 4, 'l': 4,
            'k': 5, 'g': 5, 'ng': 5,
            'ch': 6, 'j': 6, 'sh': 6, 'zh': 6,
            's': 7, 'z': 7,
            'n': 8,
            'r': 9,
            'e': 11, 'ē': 11, 'ĕ': 11,
            'i': 12, 'ī': 12, 'ĭ': 12,
            'o': 13, 'ō': 13, 'ŏ': 13,
            'u': 14, 'ū': 14, 'ŭ': 14, 'w': 14
        };
    }

    getVisemeForPhoneme(phoneme) {
        const lower = phoneme.toLowerCase();
        return this.phonemeToViseme[lower] || 0;
    }

    getMouthShapeFromViseme(visemeId) {
        return this.visemes[visemeId] || this.visemes[0];
    }

    interpolateVisemes(fromViseme, toViseme, progress) {
        const from = this.visemes[fromViseme] || this.visemes[0];
        const to = this.visemes[toViseme] || this.visemes[0];
        
        return {
            mouthOpen: from.mouthOpen + (to.mouthOpen - from.mouthOpen) * progress,
            mouthWidth: from.mouthWidth + (to.mouthWidth - from.mouthWidth) * progress
        };
    }
}

class AudioTimeAligner {
    constructor() {
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        this.scriptProcessor = null;
        this.isInitialized = false;
        
        this.visemeMapper = new VisemeMapper();
        this.currentViseme = 0;
        this.targetViseme = 0;
        this.visemeTransitionStart = 0;
        this.visemeTransitionDuration = 0.1;
        
        this.onMouthShapeUpdate = null;
        this.onAudioLevelUpdate = null;
        
        this.audioQueue = [];
        this.isPlaying = false;
        this.startTime = 0;
        this.phonemeTimings = [];
        this.currentPhonemeIndex = 0;
    }

    init() {
        if (this.isInitialized) return;
        
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            
            this.scriptProcessor = this.audioContext.createScriptProcessor(1024, 1, 1);
            this.scriptProcessor.onaudioprocess = (event) => this.onAudioProcess(event);
            
            this.analyser.connect(this.scriptProcessor);
            this.scriptProcessor.connect(this.audioContext.destination);
            
            this.isInitialized = true;
        } catch (e) {
            console.warn('Web Audio API not fully available:', e);
        }
    }

    onAudioProcess(event) {
        if (!this.isPlaying) return;
        
        this.analyser.getByteFrequencyData(this.dataArray);
        
        const average = this.dataArray.reduce((a, b) => a + b, 0) / this.dataArray.length;
        const normalizedLevel = average / 255;
        
        const currentTime = this.audioContext.currentTime - this.startTime;
        this.updateVisemeTiming(currentTime);
        
        const smoothedLevel = this.calculateSmoothedAudioLevel(normalizedLevel);
        
        if (this.onAudioLevelUpdate) {
            this.onAudioLevelUpdate(smoothedLevel);
        }
        
        if (this.onMouthShapeUpdate) {
            const mouthShape = this.calculateCurrentMouthShape();
            this.onMouthShapeUpdate(mouthShape, currentTime);
        }
    }

    updateVisemeTiming(currentTime) {
        if (this.phonemeTimings.length === 0) return;
        
        while (this.currentPhonemeIndex < this.phonemeTimings.length - 1) {
            const nextPhoneme = this.phonemeTimings[this.currentPhonemeIndex + 1];
            if (currentTime >= nextPhoneme.time) {
                this.currentPhonemeIndex++;
                this.currentViseme = this.targetViseme;
                this.targetViseme = this.visemeMapper.getVisemeForPhoneme(nextPhoneme.phoneme);
                this.visemeTransitionStart = currentTime;
                this.visemeTransitionDuration = Math.min(
                    nextPhoneme.time - this.phonemeTimings[this.currentPhonemeIndex].time,
                    0.15
                );
            } else {
                break;
            }
        }
    }

    calculateCurrentMouthShape() {
        if (this.phonemeTimings.length === 0) {
            return { mouthOpen: 0, mouthWidth: 0.5 };
        }
        
        const currentTime = this.audioContext ? 
            this.audioContext.currentTime - this.startTime : 0;
        const transitionProgress = Math.min(1, 
            (currentTime - this.visemeTransitionStart) / this.visemeTransitionDuration
        );
        
        return this.visemeMapper.interpolateVisemes(
            this.currentViseme, 
            this.targetViseme, 
            transitionProgress
        );
    }

    calculateSmoothedAudioLevel(rawLevel) {
        const attack = 0.3;
        const release = 0.1;
        
        if (!this.smoothedLevel) {
            this.smoothedLevel = 0;
        }
        
        if (rawLevel > this.smoothedLevel) {
            this.smoothedLevel += (rawLevel - this.smoothedLevel) * attack;
        } else {
            this.smoothedLevel -= (this.smoothedLevel - rawLevel) * release;
        }
        
        return this.smoothedLevel;
    }

    setPhonemeTimings(phonemeTimings) {
        this.phonemeTimings = phonemeTimings;
        this.currentPhonemeIndex = 0;
        if (phonemeTimings.length > 0) {
            this.currentViseme = 0;
            this.targetViseme = this.visemeMapper.getVisemeForPhoneme(phonemeTimings[0].phoneme);
        }
    }

    startPlayback() {
        if (!this.isInitialized) {
            this.init();
        }
        if (this.audioContext && this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
        this.isPlaying = true;
        this.startTime = this.audioContext ? this.audioContext.currentTime : Date.now() / 1000;
        this.currentPhonemeIndex = 0;
    }

    stopPlayback() {
        this.isPlaying = false;
        this.currentPhonemeIndex = 0;
    }

    getCurrentTime() {
        if (!this.audioContext) return 0;
        return this.audioContext.currentTime - this.startTime;
    }
}

class TTSPreloader {
    constructor() {
        this.chunkCache = new Map();
        this.maxCacheSize = 50;
        this.isPreloading = false;
    }

    splitTextIntoChunks(text, maxChunkLength = 50) {
        const sentences = text.split(/[。，,！？!?；;]/);
        const chunks = [];
        let currentChunk = '';
        
        for (const sentence of sentences) {
            const trimmed = sentence.trim();
            if (!trimmed) continue;
            
            if (currentChunk.length + trimmed.length > maxChunkLength) {
                if (currentChunk) {
                    chunks.push(currentChunk);
                }
                currentChunk = trimmed;
            } else {
                currentChunk += (currentChunk ? '，' : '') + trimmed;
            }
        }
        
        if (currentChunk) {
            chunks.push(currentChunk);
        }
        
        return chunks.length > 0 ? chunks : [text];
    }

    async preloadChunks(chunks, rate = 1, pitch = 1, voice = null) {
        this.isPreloading = true;
        
        for (let i = 0; i < chunks.length; i++) {
            const chunk = chunks[i];
            const cacheKey = this.getCacheKey(chunk, rate, pitch, voice);
            
            if (!this.chunkCache.has(cacheKey)) {
                const estimatedDuration = this.estimateDuration(chunk, rate);
                const phonemes = this.generatePhonemeTimings(chunk, estimatedDuration);
                
                this.chunkCache.set(cacheKey, {
                    text: chunk,
                    estimatedDuration,
                    phonemes,
                    timestamp: Date.now()
                });
                
                this.cleanupCache();
            }
            
            await new Promise(resolve => setTimeout(resolve, 10));
        }
        
        this.isPreloading = false;
    }

    getCacheKey(text, rate, pitch, voice) {
        const voiceName = voice ? voice.name : 'default';
        return `${text}_${rate}_${pitch}_${voiceName}`;
    }

    getCachedChunk(text, rate = 1, pitch = 1, voice = null) {
        const cacheKey = this.getCacheKey(text, rate, pitch, voice);
        return this.chunkCache.get(cacheKey);
    }

    estimateDuration(text, rate) {
        const charsPerSecond = 5 * rate;
        return text.length / charsPerSecond;
    }

    generatePhonemeTimings(text, totalDuration) {
        const phonemes = [];
        const chars = text.split('');
        const charDuration = totalDuration / chars.length;
        
        let currentTime = 0;
        
        for (const char of chars) {
            const phoneme = this.charToPhoneme(char);
            if (phoneme) {
                phonemes.push({
                    phoneme,
                    time: currentTime,
                    duration: charDuration
                });
            }
            currentTime += charDuration;
        }
        
        return phonemes;
    }

    charToPhoneme(char) {
        const charMap = {
            '啊': 'a', '阿': 'a',
            '波': 'b', '不': 'b',
            '的': 'd', '大': 'd',
            '发': 'f', '非': 'f',
            '个': 'g', '高': 'g',
            '好': 'h', '和': 'h',
            '可': 'k', '看': 'k',
            '了': 'l', '来': 'l',
            '吗': 'm', '没': 'm',
            '你': 'n', '那': 'n',
            '平': 'p', '跑': 'p',
            '人': 'r', '日': 'r',
            '是': 's', '三': 's',
            '他': 't', '她': 't',
            '我': 'w', '五': 'w',
            '小': 'x', '想': 'x',
            '一': 'i', '有': 'i',
            '在': 'z', '做': 'z',
            '出': 'ch', '吃': 'ch',
            '是': 'sh', '十': 'sh',
            '中': 'zh', '这': 'zh'
        };
        
        return charMap[char] || 'a';
    }

    cleanupCache() {
        if (this.chunkCache.size > this.maxCacheSize) {
            const entries = Array.from(this.chunkCache.entries())
                .sort((a, b) => a[1].timestamp - b[1].timestamp);
            
            for (let i = 0; i < entries.length - this.maxCacheSize; i++) {
                this.chunkCache.delete(entries[i][0]);
            }
        }
    }

    clearCache() {
        this.chunkCache.clear();
    }
}

class TTSManager {
    constructor() {
        this.synth = window.speechSynthesis;
        this.isSpeaking = false;
        this.onStart = null;
        this.onEnd = null;
        this.onBoundary = null;
        this.onMouthShapeUpdate = null;
        
        this.audioAligner = new AudioTimeAligner();
        this.preloader = new TTSPreloader();
        
        this.chunkQueue = [];
        this.currentChunkIndex = 0;
        this.rate = 1;
        this.pitch = 1;
        this.voice = null;
        
        this.audioAligner.onMouthShapeUpdate = (shape, time) => {
            if (this.onMouthShapeUpdate) {
                this.onMouthShapeUpdate(shape, time);
            }
        };
        
        this.audioAligner.onAudioLevelUpdate = (level) => {
            if (this.onAudioLevelUpdate) {
                this.onAudioLevelUpdate(level);
            }
        };
    }

    getVoices() {
        return this.synth.getVoices().filter(voice => 
            voice.lang.includes('zh') || voice.lang.includes('en')
        );
    }

    async speak(text, rate = 1, pitch = 1) {
        this.rate = rate;
        this.pitch = pitch;
        
        const voices = this.getVoices();
        this.voice = voices.find(v => v.lang.includes('zh')) || voices[0];
        
        const chunks = this.preloader.splitTextIntoChunks(text);
        
        await this.preloader.preloadChunks(chunks, rate, pitch, this.voice);
        
        this.chunkQueue = chunks;
        this.currentChunkIndex = 0;
        
        return this.playNextChunk();
    }

    async playNextChunk() {
        if (this.currentChunkIndex >= this.chunkQueue.length) {
            this.stop();
            if (this.onEnd) this.onEnd();
            return Promise.resolve();
        }
        
        const chunk = this.chunkQueue[this.currentChunkIndex];
        const cached = this.preloader.getCachedChunk(
            chunk, this.rate, this.pitch, this.voice
        );
        
        if (cached && cached.phonemes) {
            this.audioAligner.setPhonemeTimings(cached.phonemes);
        }
        
        return new Promise((resolve, reject) => {
            const utterance = new SpeechSynthesisUtterance(chunk);
            utterance.rate = this.rate;
            utterance.pitch = this.pitch;
            if (this.voice) {
                utterance.voice = this.voice;
            }
            
            utterance.onstart = (event) => {
                this.isSpeaking = true;
                this.audioAligner.startPlayback();
                if (this.onStart) this.onStart(event);
            };
            
            utterance.onend = (event) => {
                this.currentChunkIndex++;
                if (this.currentChunkIndex < this.chunkQueue.length) {
                    this.playNextChunk().then(resolve).catch(reject);
                } else {
                    this.isSpeaking = false;
                    this.audioAligner.stopPlayback();
                    resolve(event);
                }
            };
            
            utterance.onerror = (event) => {
                this.isSpeaking = false;
                this.audioAligner.stopPlayback();
                reject(event);
            };
            
            utterance.onboundary = (event) => {
                if (this.onBoundary) this.onBoundary(event);
            };
            
            this.synth.speak(utterance);
        });
    }

    stop() {
        this.synth.cancel();
        this.isSpeaking = false;
        this.audioAligner.stopPlayback();
        this.chunkQueue = [];
        this.currentChunkIndex = 0;
    }

    pause() {
        this.synth.pause();
    }

    resume() {
        this.synth.resume();
    }

    isSpeakingNow() {
        return this.isSpeaking;
    }

    getCurrentMouthShape() {
        return this.audioAligner.calculateCurrentMouthShape();
    }

    getCurrentPlaybackTime() {
        return this.audioAligner.getCurrentTime();
    }

    async preloadText(text, rate = 1, pitch = 1) {
        const chunks = this.preloader.splitTextIntoChunks(text);
        await this.preloader.preloadChunks(chunks, rate, pitch);
    }

    clearCache() {
        this.preloader.clearCache();
    }
}
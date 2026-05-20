<template>
  <div class="tool-panel">
    <div class="panel-tabs">
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'clip' }"
        @click="activeTab = 'clip'"
      >
        ✂️ 片段
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'subtitle' }"
        @click="activeTab = 'subtitle'"
      >
        📝 字幕
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'transition' }"
        @click="activeTab = 'transition'"
      >
        ✨ 转场
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'audio' }"
        @click="activeTab = 'audio'"
      >
        🎵 音频
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'ai' }"
        @click="activeTab = 'ai'"
      >
        🤖 AI
      </button>
    </div>

    <div class="panel-content">
      <div v-if="activeTab === 'clip'" class="tab-content">
        <div v-if="store.selectedClip" class="clip-editor">
          <h3 class="section-title">片段编辑</h3>
          
          <div class="form-group">
            <label>片段名称</label>
            <input 
              type="text" 
              class="form-input"
              :value="store.selectedClip.name"
              @input="updateClipName($event.target.value)"
            />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>入点 (秒)</label>
              <input 
                type="number" 
                class="form-input"
                :value="store.selectedClip.trimStart.toFixed(2)"
                @input="updateTrimStart($event.target.value)"
                step="0.1"
                min="0"
                :max="(store.selectedClip.originalDuration - 0.1).toFixed(2)"
              />
            </div>
            <div class="form-group">
              <label>出点 (秒)</label>
              <input 
                type="number" 
                class="form-input"
                :value="store.selectedClip.trimEnd.toFixed(2)"
                @input="updateTrimEnd($event.target.value)"
                step="0.1"
                :min="(store.selectedClip.trimStart + 0.1).toFixed(2)"
                :max="store.selectedClip.originalDuration.toFixed(2)"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>开始时间</label>
              <input 
                type="number" 
                class="form-input"
                :value="store.selectedClip.startTime.toFixed(2)"
                @input="updateStartTime($event.target.value)"
                step="0.1"
                min="0"
              />
            </div>
            <div class="form-group">
              <label>持续时间</label>
              <input 
                type="text" 
                class="form-input"
                :value="formatTimeShort(store.selectedClip.duration)"
                readonly
              />
            </div>
          </div>

          <div class="trim-visualizer">
            <div class="trim-track">
              <div 
                class="trim-range"
                :style="{
                  left: (store.selectedClip.trimStart / store.selectedClip.originalDuration * 100) + '%',
                  width: ((store.selectedClip.trimEnd - store.selectedClip.trimStart) / store.selectedClip.originalDuration * 100) + '%'
                }"
              ></div>
              <div 
                class="trim-handle left"
                :style="{ left: (store.selectedClip.trimStart / store.selectedClip.originalDuration * 100) + '%' }"
                @mousedown="startVisualTrim('left', $event)"
              ></div>
              <div 
                class="trim-handle right"
                :style="{ left: (store.selectedClip.trimEnd / store.selectedClip.originalDuration * 100) + '%' }"
                @mousedown="startVisualTrim('right', $event)"
              ></div>
            </div>
            <div class="trim-labels">
              <span>{{ formatTimeShort(store.selectedClip.trimStart) }}</span>
              <span>{{ formatTimeShort(store.selectedClip.originalDuration) }}</span>
            </div>
          </div>

          <div class="action-buttons">
            <button class="btn btn-primary" @click="applyTrim">
              ✂️ 应用裁剪
            </button>
            <button class="btn" @click="resetTrim">
              🔄 重置
            </button>
            <button class="btn danger" @click="deleteClip">
              🗑️ 删除
            </button>
          </div>

          <div class="quick-tools">
            <h4 class="section-subtitle">快捷工具</h4>
            <div class="tool-buttons">
              <button class="tool-btn" @click="cutAtPlayhead">
                ⚔️ 在播放头分割
              </button>
              <button class="tool-btn" @click="jumpToClipStart">
                ⏮️ 跳转到开始
              </button>
              <button class="tool-btn" @click="jumpToClipEnd">
                ⏭️ 跳转到结束
              </button>
            </div>
          </div>
        </div>

        <div v-else class="empty-panel">
          <span>👆</span>
          <p>选择时间轴上的片段进行编辑</p>
        </div>
      </div>

      <div v-if="activeTab === 'subtitle'" class="tab-content">
        <div class="subtitle-editor">
          <h3 class="section-title">字幕管理</h3>
          
          <button class="btn btn-primary full-width" @click="addNewSubtitle">
            ➕ 添加字幕
          </button>

          <div class="subtitle-list" v-if="store.subtitleTrack.length > 0">
            <div 
              v-for="sub in sortedSubtitles" 
              :key="sub.id" 
              class="subtitle-item"
              :class="{ selected: editingSubtitleId === sub.id }"
              @click="selectSubtitle(sub)"
            >
              <div class="subtitle-timing">
                <span>{{ formatTimeShort(sub.startTime) }}</span>
                <span class="timing-arrow">→</span>
                <span>{{ formatTimeShort(sub.endTime) }}</span>
              </div>
              <div class="subtitle-text">{{ sub.text }}</div>
              <button class="delete-btn" @click.stop="removeSubtitle(sub.id)">
                🗑️
              </button>
            </div>
          </div>

          <div class="subtitle-form" v-if="editingSubtitle">
            <h4 class="section-subtitle">编辑字幕</h4>
            
            <div class="form-group">
              <label>字幕内容</label>
              <textarea 
                class="form-input textarea"
                rows="3"
                v-model="editingSubtitle.text"
                placeholder="输入字幕内容..."
              ></textarea>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>开始时间 (秒)</label>
                <input 
                  type="number" 
                  class="form-input"
                  v-model.number="editingSubtitle.startTime"
                  step="0.1"
                  min="0"
                />
              </div>
              <div class="form-group">
                <label>结束时间 (秒)</label>
                <input 
                  type="number" 
                  class="form-input"
                  v-model.number="editingSubtitle.endTime"
                  step="0.1"
                  min="0"
                />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>字体大小</label>
                <input 
                  type="number" 
                  class="form-input"
                  v-model.number="editingSubtitle.style.fontSize"
                  min="12"
                  max="96"
                />
              </div>
              <div class="form-group">
                <label>字体颜色</label>
                <input 
                  type="color" 
                  class="form-input color-input"
                  v-model="editingSubtitle.style.color"
                />
              </div>
            </div>

            <div class="action-buttons">
              <button class="btn btn-success" @click="saveSubtitle">
                💾 保存
              </button>
              <button class="btn" @click="cancelEdit">
                ❌ 取消
              </button>
            </div>
          </div>

          <div v-else-if="store.subtitleTrack.length === 0" class="empty-panel">
            <span>📝</span>
            <p>还没有字幕，点击上方按钮添加</p>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'transition'" class="tab-content">
        <div class="transition-editor">
          <h3 class="section-title">转场特效</h3>
          
          <div v-if="store.selectedClip" class="transition-setup">
            <p class="hint">为当前片段的结尾添加转场效果</p>
            
            <div class="transition-list">
              <div 
                v-for="trans in store.transitions" 
                :key="trans.id"
                class="transition-item"
                :class="{ active: store.selectedClip.transition === trans.id }"
                @click="selectTransition(trans.id)"
              >
                <span class="transition-icon">{{ getTransitionIcon(trans.id) }}</span>
                <span class="transition-name">{{ trans.name }}</span>
              </div>
            </div>

            <div class="form-group" v-if="store.selectedClip.transition">
              <label>转场时长: {{ transitionDuration }} 秒</label>
              <input 
                type="range" 
                class="range-input"
                v-model.number="transitionDuration"
                min="0.5"
                max="3"
                step="0.1"
              />
            </div>

            <div class="action-buttons">
              <button class="btn btn-primary" @click="applyTransition" v-if="store.selectedClip.transition">
                ✨ 应用转场
              </button>
              <button class="btn" @click="removeTransition" v-if="store.selectedClip.transition">
                ❌ 移除转场
              </button>
            </div>
          </div>

          <div v-else class="empty-panel">
            <span>✨</span>
            <p>选择一个视频片段添加转场特效</p>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'audio'" class="tab-content">
        <div class="audio-editor">
          <h3 class="section-title">背景音乐</h3>
          
          <div class="audio-upload">
            <div 
              class="drop-zone small"
              @click="triggerAudioInput"
              @drop.prevent="handleAudioDrop"
              @dragover.prevent
            >
              <input 
                ref="audioInput"
                type="file" 
                accept="audio/*" 
                hidden
                @change="handleAudioSelect"
              />
              <span class="upload-icon">🎵</span>
              <p>点击或拖拽音频文件</p>
              <p class="hint">支持 MP3, WAV, AAC 等格式</p>
            </div>
          </div>

          <div class="current-audio" v-if="store.backgroundMusic">
            <div class="audio-info">
              <span class="audio-name">{{ store.backgroundMusic.name }}</span>
              <span class="audio-duration">{{ formatTimeShort(store.backgroundMusic.duration) }}</span>
            </div>
            <div class="audio-controls">
              <div class="form-group">
                <label>开始时间 (秒)</label>
                <input 
                  type="number" 
                  class="form-input"
                  v-model.number="audioStartTime"
                  step="0.1"
                  min="0"
                />
              </div>
              <div class="form-group">
                <label>音量</label>
                <input 
                  type="range" 
                  class="range-input"
                  v-model.number="audioVolume"
                  min="0"
                  max="1"
                  step="0.1"
                />
                <span class="volume-value">{{ Math.round(audioVolume * 100) }}%</span>
              </div>
            </div>
            <div class="action-buttons">
              <button class="btn btn-primary" @click="applyAudio">
                🎵 应用背景音乐
              </button>
              <button class="btn danger" @click="removeAudio">
                🗑️ 移除
              </button>
            </div>
          </div>

          <div class="audio-tools">
            <h4 class="section-subtitle">音频工具</h4>
            <div class="tool-buttons">
              <button class="tool-btn" @click="extractAudio">
                📤 从视频提取音频
              </button>
              <button class="tool-btn" @click="muteOriginal" :disabled="!store.selectedClip">
                🔇 静音原视频音频
              </button>
            </div>
          </div>

          <div v-if="!store.backgroundMusic && store.audioTrack.length === 0" class="empty-panel">
            <span>🎵</span>
            <p>添加背景音乐或从媒体库拖入音频</p>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'ai'" class="tab-content">
        <div class="ai-tools">
          <div class="ai-section">
            <h3 class="section-title">🎨 AI抠图</h3>
            
            <div class="form-group">
              <label>抠图方式</label>
              <select class="form-input" v-model="bgRemovalMethod">
                <option value="chroma_key">色度键（绿幕）</option>
                <option value="color_threshold">颜色阈值</option>
                <option value="ai_model">AI模型（Beta）</option>
              </select>
            </div>

            <div v-if="bgRemovalMethod === 'chroma_key'" class="chroma-key-settings">
              <div class="form-group">
                <label>键控颜色</label>
                <div class="color-picker-row">
                  <input 
                    type="color" 
                    class="form-input color-input"
                    v-model="chromaKeyColor"
                  />
                  <input 
                    type="text" 
                    class="form-input"
                    v-model="chromaKeyColor"
                  />
                </div>
              </div>
              
              <div class="form-group">
                <label>相似度: {{ (chromaThreshold * 100).toFixed(0) }}%</label>
                <input 
                  type="range" 
                  class="range-input"
                  v-model.number="chromaThreshold"
                  min="0.1"
                  max="0.9"
                  step="0.05"
                />
              </div>
              
              <div class="form-group">
                <label>平滑度: {{ (chromaSmoothing * 100).toFixed(0) }}%</label>
                <input 
                  type="range" 
                  class="range-input"
                  v-model.number="chromaSmoothing"
                  min="0"
                  max="0.5"
                  step="0.05"
                />
              </div>
            </div>

            <div v-if="bgRemovalMethod === 'color_threshold'" class="color-threshold-settings">
              <div class="form-row">
                <div class="form-group">
                  <label>最低颜色 (RGB)</label>
                  <div class="color-inputs">
                    <input type="number" class="form-input" v-model.number="colorLower[0]" min="0" max="255" placeholder="R" />
                    <input type="number" class="form-input" v-model.number="colorLower[1]" min="0" max="255" placeholder="G" />
                    <input type="number" class="form-input" v-model.number="colorLower[2]" min="0" max="255" placeholder="B" />
                  </div>
                </div>
                <div class="form-group">
                  <label>最高颜色 (RGB)</label>
                  <div class="color-inputs">
                    <input type="number" class="form-input" v-model.number="colorUpper[0]" min="0" max="255" placeholder="R" />
                    <input type="number" class="form-input" v-model.number="colorUpper[1]" min="0" max="255" placeholder="G" />
                    <input type="number" class="form-input" v-model.number="colorUpper[2]" min="0" max="255" placeholder="B" />
                  </div>
                </div>
              </div>
            </div>

            <div class="form-group">
              <label>背景替换</label>
              <div class="bg-type-buttons">
                <button 
                  class="bg-type-btn" 
                  :class="{ active: bgType === 'transparent' }"
                  @click="bgType = 'transparent'"
                >
                  🔲 透明
                </button>
                <button 
                  class="bg-type-btn" 
                  :class="{ active: bgType === 'color' }"
                  @click="bgType = 'color'"
                >
                  🎨 纯色
                </button>
                <button 
                  class="bg-type-btn" 
                  :class="{ active: bgType === 'blur' }"
                  @click="bgType = 'blur'"
                >
                  🔍 模糊
                </button>
                <button 
                  class="bg-type-btn" 
                  :class="{ active: bgType === 'image' }"
                  @click="bgType = 'image'"
                >
                  🖼️ 图片
                </button>
              </div>
            </div>

            <div v-if="bgType === 'color'" class="form-group">
              <label>背景颜色</label>
              <input 
                type="color" 
                class="form-input color-input"
                v-model="bgColor"
              />
            </div>

            <div v-if="bgType === 'blur'" class="form-group">
              <label>模糊程度: {{ blurAmount }}px</label>
              <input 
                type="range" 
                class="range-input"
                v-model.number="blurAmount"
                min="1"
                max="30"
                step="1"
              />
            </div>

            <div v-if="bgType === 'image'" class="form-group">
              <label>背景图片</label>
              <input 
                type="file" 
                accept="image/*"
                class="form-input"
                @change="handleBgImageSelect"
              />
            </div>

            <div class="action-buttons">
              <button 
                class="btn btn-primary full-width" 
                @click="applyBackgroundRemoval"
                :disabled="!store.selectedClip || bgRemovalProcessing"
              >
                {{ bgRemovalProcessing ? '⏳ 处理中...' : '🎨 应用抠图效果' }}
              </button>
              <button 
                class="btn" 
                @click="previewBackgroundRemoval"
                :disabled="!store.selectedClip"
              >
                👁️ 预览效果
              </button>
            </div>
          </div>

          <div class="ai-section">
            <h3 class="section-title">🎤 语音转字幕</h3>
            
            <div class="form-group">
              <label>识别方式</label>
              <select class="form-input" v-model="speechProvider">
                <option value="web_speech_api">浏览器实时识别</option>
                <option value="whisper_api">Whisper API</option>
                <option value="custom_api">自定义API</option>
              </select>
            </div>

            <div v-if="speechProvider === 'web_speech_api'" class="realtime-recognition">
              <div class="recording-status" :class="{ recording: isRecording }">
                <span class="recording-dot"></span>
                <span>{{ isRecording ? '正在录音...' : '准备就绪' }}</span>
              </div>
              
              <div v-if="interimTranscript" class="interim-text">
                {{ interimTranscript }}
              </div>
              
              <div v-if="currentTranscript" class="final-text">
                {{ currentTranscript }}
              </div>
              
              <div class="action-buttons">
                <button 
                  class="btn btn-primary full-width" 
                  @click="toggleRecording"
                  :class="{ recording: isRecording }"
                >
                  {{ isRecording ? '⏹️ 停止录音' : '🎤 开始录音' }}
                </button>
              </div>
            </div>

            <div v-if="speechProvider === 'whisper_api'" class="api-settings">
              <div class="form-group">
                <label>OpenAI API Key</label>
                <input 
                  type="password" 
                  class="form-input"
                  v-model="apiKey"
                  placeholder="sk-..."
                />
              </div>
            </div>

            <div v-if="speechProvider === 'custom_api'" class="api-settings">
              <div class="form-group">
                <label>API端点</label>
                <input 
                  type="text" 
                  class="form-input"
                  v-model="apiEndpoint"
                  placeholder="https://your-api.com/transcribe"
                />
              </div>
            </div>

            <div class="form-group">
              <label>语言</label>
              <select class="form-input" v-model="speechLanguage">
                <option value="zh-CN">中文（普通话）</option>
                <option value="en-US">英语（美国）</option>
                <option value="ja-JP">日语</option>
                <option value="ko-KR">韩语</option>
              </select>
            </div>

            <div class="audio-tools">
              <h4 class="section-subtitle">音频处理</h4>
              <div class="tool-buttons">
                <button 
                  class="tool-btn" 
                  @click="extractAndTranscribe"
                  :disabled="!store.selectedClip || speechProcessing"
                >
                  📤 从视频提取音频并转字幕
                </button>
                <button 
                  class="tool-btn" 
                  @click="transcribeAudioFile"
                  :disabled="speechProcessing"
                >
                  🎵 上传音频文件转字幕
                </button>
              </div>
            </div>

            <div v-if="speechProcessing" class="progress-bar-container">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: speechProgress * 100 + '%' }"></div>
              </div>
              <span class="progress-text">{{ (speechProgress * 100).toFixed(0) }}%</span>
            </div>

            <div v-if="generatedSubtitles.length > 0" class="generated-subtitles">
              <h4 class="section-subtitle">已生成 {{ generatedSubtitles.length }} 条字幕</h4>
              <div class="subtitle-preview-list">
                <div 
                  v-for="sub in generatedSubtitles.slice(0, 3)" 
                  :key="sub.id"
                  class="subtitle-preview-item"
                >
                  <span class="subtitle-time">
                    {{ formatTimeShort(sub.startTime) }} - {{ formatTimeShort(sub.endTime) }}
                  </span>
                  <span class="subtitle-text-preview">{{ sub.text }}</span>
                </div>
              </div>
              <div class="action-buttons">
                <button class="btn btn-success" @click="applyGeneratedSubtitles">
                  ✅ 应用到时间轴
                </button>
                <button class="btn" @click="clearGeneratedSubtitles">
                  ❌ 清除
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useEditorStore } from '../stores/editor'
import { ffmpegService } from '../utils/ffmpeg'
import { formatTimeShort } from '../utils/format'

const store = useEditorStore()

const activeTab = ref('clip')
const audioInput = ref(null)
const editingSubtitleId = ref(null)
const editingSubtitle = ref(null)
const transitionDuration = ref(1)
const audioStartTime = ref(0)
const audioVolume = ref(0.8)

const sortedSubtitles = computed(() => {
  return [...store.subtitleTrack].sort((a, b) => a.startTime - b.startTime)
})

watch(() => store.selectedClip, (clip) => {
  if (clip) {
    transitionDuration.value = clip.transitionDuration || 1
  }
})

function updateClipName(name) {
  if (store.selectedClip) {
    store.updateClip(store.selectedClip.id, { name })
  }
}

function updateTrimStart(value) {
  if (store.selectedClip) {
    const trimStart = parseFloat(value) || 0
    store.trimClip(store.selectedClip.id, trimStart, store.selectedClip.trimEnd)
  }
}

function updateTrimEnd(value) {
  if (store.selectedClip) {
    const trimEnd = parseFloat(value) || store.selectedClip.originalDuration
    store.trimClip(store.selectedClip.id, store.selectedClip.trimStart, trimEnd)
  }
}

function updateStartTime(value) {
  if (store.selectedClip) {
    const startTime = parseFloat(value) || 0
    store.moveClip(store.selectedClip.id, startTime)
  }
}

function startVisualTrim(side, e) {
  if (!store.selectedClip) return
  
  const track = e.target.closest('.trim-track')
  const rect = track.getBoundingClientRect()
  const clip = store.selectedClip
  
  function handleMouseMove(moveEvent) {
    const x = moveEvent.clientX - rect.left
    const ratio = Math.max(0, Math.min(1, x / rect.width))
    const time = ratio * clip.originalDuration
    
    if (side === 'left') {
      store.trimClip(clip.id, time, clip.trimEnd)
    } else {
      store.trimClip(clip.id, clip.trimStart, time)
    }
  }
  
  function handleMouseUp() {
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }
  
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

async function applyTrim() {
  if (!store.selectedClip) return
  
  try {
    store.setProcessing(true, '正在裁剪视频...')
    
    const blob = await ffmpegService.trimVideo(
      store.selectedClip.file,
      store.selectedClip.trimStart,
      store.selectedClip.trimEnd,
      (p) => store.setProcessing(true, '正在裁剪视频...', p.progress || 0)
    )
    
    const newFile = new File([blob], `trimmed_${store.selectedClip.name}`, { type: 'video/mp4' })
    const mediaItem = await store.addMediaFile(newFile)
    const clip = store.addToVideoTrack(mediaItem, store.selectedClip.startTime)
    
    store.removeClip(store.selectedClip.id)
    store.selectClip(clip.id)
    
    store.setProcessing(false)
  } catch (error) {
    console.error('裁剪失败:', error)
    alert('裁剪失败: ' + error.message)
    store.setProcessing(false)
  }
}

function resetTrim() {
  if (store.selectedClip) {
    store.trimClip(store.selectedClip.id, 0, store.selectedClip.originalDuration)
  }
}

function deleteClip() {
  if (store.selectedClip && confirm('确定要删除这个片段吗？')) {
    store.removeClip(store.selectedClip.id)
  }
}

function cutAtPlayhead() {
  if (!store.selectedClip) return
  
  const clip = store.selectedClip
  const cutTime = store.currentTime - clip.startTime + clip.trimStart
  
  if (cutTime <= clip.trimStart || cutTime >= clip.trimEnd) {
    alert('请在片段范围内设置播放头')
    return
  }
  
  const originalTrimEnd = clip.trimEnd
  store.trimClip(clip.id, clip.trimStart, cutTime)
  
  const newClip = {
    ...clip,
    id: Date.now().toString(36) + Math.random().toString(36).substr(2),
    startTime: clip.startTime + (cutTime - clip.trimStart),
    trimStart: cutTime,
    trimEnd: originalTrimEnd,
    duration: originalTrimEnd - cutTime,
    endTime: clip.startTime + (cutTime - clip.trimStart) + (originalTrimEnd - cutTime),
  }
  
  store.videoTrack.push(newClip)
  store.updateTotalDuration()
}

function jumpToClipStart() {
  if (store.selectedClip) {
    store.setCurrentTime(store.selectedClip.startTime)
  }
}

function jumpToClipEnd() {
  if (store.selectedClip) {
    store.setCurrentTime(store.selectedClip.endTime)
  }
}

function addNewSubtitle() {
  const startTime = store.currentTime
  const endTime = Math.min(startTime + 3, store.totalDuration || startTime + 3)
  const sub = store.addSubtitle('请输入字幕内容', startTime, endTime)
  selectSubtitle(sub)
}

function selectSubtitle(sub) {
  editingSubtitleId.value = sub.id
  editingSubtitle.value = {
    ...sub,
    style: { ...sub.style }
  }
}

function saveSubtitle() {
  if (editingSubtitle.value) {
    store.updateSubtitle(editingSubtitle.value.id, editingSubtitle.value)
    cancelEdit()
  }
}

function cancelEdit() {
  editingSubtitleId.value = null
  editingSubtitle.value = null
}

function removeSubtitle(id) {
  if (confirm('确定要删除这个字幕吗？')) {
    store.removeSubtitle(id)
    if (editingSubtitleId.value === id) {
      cancelEdit()
    }
  }
}

function selectTransition(id) {
  if (store.selectedClip) {
    store.updateClip(store.selectedClip.id, { transition: id })
  }
}

async function applyTransition() {
  if (!store.selectedClip || !store.selectedClip.transition) return
  
  const clips = store.sortedVideoClips
  const currentIndex = clips.findIndex(c => c.id === store.selectedClip.id)
  
  if (currentIndex >= clips.length - 1) {
    alert('转场需要应用在两个片段之间，请确保当前片段后面还有其他片段')
    return
  }
  
  const nextClip = clips[currentIndex + 1]
  
  try {
    store.setProcessing(true, '正在应用转场效果...')
    
    const blob = await ffmpegService.addTransition(
      store.selectedClip.file,
      nextClip.file,
      store.selectedClip.transition,
      transitionDuration.value,
      (p) => store.setProcessing(true, '正在应用转场效果...', p.progress || 0)
    )
    
    const newFile = new File([blob], `transition_${Date.now()}.mp4`, { type: 'video/mp4' })
    const mediaItem = await store.addMediaFile(newFile)
    
    const newStartTime = store.selectedClip.startTime
    store.removeClip(nextClip.id)
    store.removeClip(store.selectedClip.id)
    
    const clip = store.addToVideoTrack(mediaItem, newStartTime)
    store.selectClip(clip.id)
    
    store.setProcessing(false)
  } catch (error) {
    console.error('转场应用失败:', error)
    alert('转场应用失败: ' + error.message)
    store.setProcessing(false)
  }
}

function removeTransition() {
  if (store.selectedClip) {
    store.updateClip(store.selectedClip.id, { transition: null })
  }
}

function getTransitionIcon(id) {
  const icons = {
    fade: '🌅',
    dissolve: '💫',
    wipe_left: '⬅️',
    wipe_right: '➡️',
    slide_left: '👈',
    slide_right: '👉',
    circle_in: '⭕',
    pixelize: '🔲',
  }
  return icons[id] || '✨'
}

function triggerAudioInput() {
  audioInput.value?.click()
}

async function handleAudioSelect(e) {
  const file = e.target.files?.[0]
  if (file) {
    await processAudioFile(file)
  }
  e.target.value = ''
}

async function handleAudioDrop(e) {
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('audio/')) {
    await processAudioFile(file)
  }
}

async function processAudioFile(file) {
  const mediaItem = await store.addMediaFile(file)
  store.setBackgroundMusic(mediaItem)
}

async function applyAudio() {
  if (!store.backgroundMusic || store.videoTrack.length === 0) {
    alert('请先添加背景音乐和视频片段')
    return
  }
  
  const mainClip = store.sortedVideoClips[0]
  if (!mainClip) return
  
  try {
    store.setProcessing(true, '正在替换背景音乐...')
    
    const blob = await ffmpegService.replaceAudio(
      mainClip.file,
      store.backgroundMusic.file,
      audioStartTime.value,
      (p) => store.setProcessing(true, '正在替换背景音乐...', p.progress || 0)
    )
    
    const newFile = new File([blob], `with_audio_${mainClip.name}`, { type: 'video/mp4' })
    const mediaItem = await store.addMediaFile(newFile)
    
    const newStartTime = mainClip.startTime
    store.removeClip(mainClip.id)
    
    const clip = store.addToVideoTrack(mediaItem, newStartTime)
    store.selectClip(clip.id)
    
    store.setProcessing(false)
  } catch (error) {
    console.error('音频替换失败:', error)
    alert('音频替换失败: ' + error.message)
    store.setProcessing(false)
  }
}

function removeAudio() {
  store.removeBackgroundMusic()
}

async function extractAudio() {
  alert('此功能需要先选择一个视频片段，然后使用FFmpeg提取音频')
}

async function muteOriginal() {
  alert('静音功能将在导出时应用，或使用裁剪功能重新生成无声视频')
}

import BackgroundRemover from '../utils/backgroundRemover'
import SpeechToSubtitle from '../utils/speechToSubtitle'

let backgroundRemover = null
let speechToSubtitle = null
const audioFileInput = ref(null)

const bgRemovalMethod = ref('chroma_key')
const chromaKeyColor = ref('#00ff00')
const chromaThreshold = ref(0.4)
const chromaSmoothing = ref(0.1)
const colorLower = ref([0, 0, 0])
const colorUpper = ref([50, 50, 50])
const bgType = ref('color')
const bgColor = ref('#ffffff')
const blurAmount = ref(10)
const bgImageUrl = ref(null)
const bgRemovalProcessing = ref(false)

const speechProvider = ref('web_speech_api')
const apiKey = ref('')
const apiEndpoint = ref('')
const speechLanguage = ref('zh-CN')
const isRecording = ref(false)
const interimTranscript = ref('')
const currentTranscript = ref('')
const speechProcessing = ref(false)
const speechProgress = ref(0)
const generatedSubtitles = ref([])

function initBackgroundRemover() {
  if (!backgroundRemover) {
    backgroundRemover = new BackgroundRemover()
  }
}

function initSpeechToSubtitle() {
  if (!speechToSubtitle) {
    speechToSubtitle = new SpeechToSubtitle({
      language: speechLanguage.value,
      onResult: (result) => {
        interimTranscript.value = result.interim
        if (result.final) {
          currentTranscript.value += result.final + ' '
        }
      },
      onProgress: (progress) => {
        speechProgress.value = progress
      },
      onError: (error) => {
        alert('语音识别错误: ' + error)
      },
    })
  }
}

async function applyBackgroundRemoval() {
  if (!store.selectedClip) return
  
  initBackgroundRemover()
  bgRemovalProcessing.value = true
  
  try {
    store.setProcessing(true, '正在应用抠图效果...')
    
    backgroundRemover.setMethod(bgRemovalMethod.value)
    backgroundRemover.setChromaKeyParams({
      color: chromaKeyColor.value,
      threshold: chromaThreshold.value,
      smoothing: chromaSmoothing.value,
    })
    backgroundRemover.setColorThresholdParams({
      lower: colorLower.value,
      upper: colorUpper.value,
      invert: false,
    })
    backgroundRemover.setBackground({
      type: bgType.value,
      color: bgColor.value,
      imageUrl: bgImageUrl.value,
      blurAmount: blurAmount.value,
    })
    
    store.setBackgroundRemoval({
      enabled: true,
      method: bgRemovalMethod.value,
      chromaKey: {
        color: chromaKeyColor.value,
        threshold: chromaThreshold.value,
        smoothing: chromaSmoothing.value,
        spillSuppression: 0.2,
      },
      colorThreshold: {
        lower: colorLower.value,
        upper: colorUpper.value,
        invert: false,
      },
      background: {
        type: bgType.value,
        color: bgColor.value,
        imageUrl: bgImageUrl.value,
        blurAmount: blurAmount.value,
      },
      isProcessing: false,
    })
    
    const result = await ffmpegService.applyBackgroundRemoval(
      store.selectedClip.file,
      {
        method: bgRemovalMethod.value,
        chromaKey: {
          color: chromaKeyColor.value,
          threshold: chromaThreshold.value,
          smoothing: chromaSmoothing.value,
        },
        background: {
          type: bgType.value,
          color: bgColor.value,
          imageUrl: bgImageUrl.value,
          blurAmount: blurAmount.value,
        },
      },
      (p) => store.setProcessing(true, '正在应用抠图效果...', p.progress || 0)
    )
    
    const newFile = new File([result], `bg_removed_${store.selectedClip.name}`, { type: 'video/mp4' })
    const mediaItem = await store.addMediaFile(newFile)
    const newStartTime = store.selectedClip.startTime
    
    store.removeClip(store.selectedClip.id)
    const clip = store.addToVideoTrack(mediaItem, newStartTime)
    store.selectClip(clip.id)
    
    store.setProcessing(false)
    alert('抠图效果已应用！')
  } catch (error) {
    console.error('抠图处理失败:', error)
    alert('抠图处理失败: ' + error.message)
    store.setProcessing(false)
  } finally {
    bgRemovalProcessing.value = false
  }
}

function previewBackgroundRemoval() {
  if (!store.selectedClip) return
  
  initBackgroundRemover()
  alert('预览功能将在视频预览区实时显示抠图效果')
}

function handleBgImageSelect(e) {
  const file = e.target.files?.[0]
  if (file) {
    bgImageUrl.value = URL.createObjectURL(file)
  }
}

function toggleRecording() {
  initSpeechToSubtitle()
  
  speechToSubtitle.setProvider(speechProvider.value, {
    apiKey: apiKey.value,
    apiEndpoint: apiEndpoint.value,
  })
  speechToSubtitle.setLanguage(speechLanguage.value)
  
  if (isRecording.value) {
    speechToSubtitle.stopRecording()
    isRecording.value = false
    
    const subtitles = speechToSubtitle.generateSubtitles()
    if (subtitles.length > 0) {
      generatedSubtitles.value = subtitles
    }
  } else {
    currentTranscript.value = ''
    interimTranscript.value = ''
    speechToSubtitle.startRecording()
    isRecording.value = true
  }
}

async function extractAndTranscribe() {
  if (!store.selectedClip) return
  
  initSpeechToSubtitle()
  speechProcessing.value = true
  speechProgress.value = 0
  
  try {
    store.setProcessing(true, '正在提取音频并识别...')
    
    speechToSubtitle.setProvider(speechProvider.value, {
      apiKey: apiKey.value,
      apiEndpoint: apiEndpoint.value,
    })
    speechToSubtitle.setLanguage(speechLanguage.value)
    
    const subtitles = await speechToSubtitle.processAudioFile(
      store.selectedClip.file,
      (progress, current, total) => {
        speechProgress.value = progress
        store.setProcessing(true, `正在识别... ${current}/${total}`, progress)
      }
    )
    
    generatedSubtitles.value = subtitles
    store.setProcessing(false)
    
    if (subtitles.length > 0) {
      alert(`成功生成 ${subtitles.length} 条字幕！点击"应用到时间轴"确认添加。`)
    } else {
      alert('未能识别到有效语音内容')
    }
  } catch (error) {
    console.error('语音识别失败:', error)
    alert('语音识别失败: ' + error.message)
    store.setProcessing(false)
  } finally {
    speechProcessing.value = false
  }
}

async function transcribeAudioFile() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'audio/*'
  
  input.onchange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    initSpeechToSubtitle()
    speechProcessing.value = true
    speechProgress.value = 0
    
    try {
      store.setProcessing(true, '正在识别音频...')
      
      speechToSubtitle.setProvider(speechProvider.value, {
        apiKey: apiKey.value,
        apiEndpoint: apiEndpoint.value,
      })
      speechToSubtitle.setLanguage(speechLanguage.value)
      
      const subtitles = await speechToSubtitle.processAudioFile(
        file,
        (progress) => {
          speechProgress.value = progress
          store.setProcessing(true, '正在识别...', progress)
        }
      )
      
      generatedSubtitles.value = subtitles
      store.setProcessing(false)
      
      if (subtitles.length > 0) {
        alert(`成功生成 ${subtitles.length} 条字幕！点击"应用到时间轴"确认添加。`)
      }
    } catch (error) {
      console.error('语音识别失败:', error)
      alert('语音识别失败: ' + error.message)
      store.setProcessing(false)
    } finally {
      speechProcessing.value = false
    }
  }
  
  input.click()
}

function applyGeneratedSubtitles() {
  if (generatedSubtitles.value.length === 0) return
  
  for (const sub of generatedSubtitles.value) {
    store.addSubtitle(sub.text, sub.startTime, sub.endTime)
  }
  
  alert(`已添加 ${generatedSubtitles.value.length} 条字幕到时间轴！`)
  clearGeneratedSubtitles()
}

function clearGeneratedSubtitles() {
  generatedSubtitles.value = []
  currentTranscript.value = ''
  interimTranscript.value = ''
}
</script>

<style scoped>
.tool-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-tertiary);
}

.tab-btn {
  flex: 1;
  padding: 12px 8px;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 2px solid transparent;
}

.tab-btn:hover {
  color: var(--text-primary);
}

.tab-btn.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
  background: rgba(233, 69, 96, 0.1);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.section-subtitle {
  font-size: 13px;
  font-weight: 500;
  margin: 16px 0 8px;
  color: var(--text-secondary);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  color: var(--text-secondary);
}

.form-input {
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  transition: border-color 0.2s;
}

.form-input:focus {
  border-color: var(--accent-primary);
  outline: none;
}

.form-input.textarea {
  resize: vertical;
  min-height: 60px;
}

.form-input.color-input {
  height: 36px;
  padding: 2px;
  cursor: pointer;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-row .form-group {
  flex: 1;
}

.range-input {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: var(--bg-track);
  border-radius: 3px;
  outline: none;
}

.range-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  background: var(--accent-primary);
  border-radius: 50%;
  cursor: pointer;
}

.range-input::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: var(--accent-primary);
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.volume-value {
  font-size: 11px;
  color: var(--text-muted);
  text-align: right;
}

.trim-visualizer {
  margin: 16px 0;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.trim-track {
  position: relative;
  height: 24px;
  background: var(--bg-track);
  border-radius: 4px;
  margin-bottom: 8px;
}

.trim-range {
  position: absolute;
  top: 0;
  bottom: 0;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
  border-radius: 4px;
  opacity: 0.6;
}

.trim-handle {
  position: absolute;
  top: -4px;
  bottom: -4px;
  width: 8px;
  background: var(--accent-primary);
  border-radius: 4px;
  cursor: ew-resize;
  transform: translateX(-50%);
  z-index: 2;
}

.trim-handle:hover {
  background: var(--accent-secondary);
}

.trim-labels {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-muted);
  font-family: 'Courier New', monospace;
}

.action-buttons {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.action-buttons .btn {
  flex: 1;
  min-width: 100px;
}

.btn.danger {
  background: rgba(233, 69, 96, 0.2);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.btn.danger:hover {
  background: var(--accent-primary);
  color: white;
}

.btn.full-width {
  width: 100%;
  justify-content: center;
}

.quick-tools, .audio-tools {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.tool-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tool-btn {
  padding: 10px 12px;
  background: var(--bg-track);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 12px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.tool-btn:hover:not(:disabled) {
  background: var(--bg-clip);
  border-color: var(--accent-secondary);
}

.tool-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-panel {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}

.empty-panel span {
  font-size: 36px;
  display: block;
  margin-bottom: 8px;
}

.empty-panel p {
  font-size: 13px;
}

.subtitle-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
  max-height: 200px;
  overflow-y: auto;
}

.subtitle-item {
  padding: 10px 12px;
  background: var(--bg-track);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.subtitle-item:hover {
  border-color: var(--accent-secondary);
}

.subtitle-item.selected {
  border-color: var(--accent-primary);
  background: rgba(233, 69, 96, 0.1);
}

.subtitle-timing {
  font-size: 11px;
  color: var(--accent-secondary);
  font-family: 'Courier New', monospace;
  margin-bottom: 4px;
}

.timing-arrow {
  margin: 0 6px;
}

.subtitle-text {
  font-size: 12px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 30px;
}

.delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  opacity: 0;
  transition: all 0.2s;
}

.subtitle-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: var(--accent-primary);
}

.subtitle-form {
  margin-top: 16px;
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.transition-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin: 16px 0;
}

.transition-item {
  padding: 12px 8px;
  background: var(--bg-track);
  border: 2px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  text-align: center;
  transition: all 0.2s;
}

.transition-item:hover {
  border-color: var(--accent-secondary);
}

.transition-item.active {
  border-color: var(--accent-primary);
  background: rgba(233, 69, 96, 0.1);
}

.transition-icon {
  font-size: 24px;
  display: block;
  margin-bottom: 4px;
}

.transition-name {
  font-size: 11px;
  color: var(--text-secondary);
}

.hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.drop-zone.small {
  padding: 24px 16px;
}

.upload-icon {
  font-size: 32px;
  display: block;
  margin-bottom: 8px;
}

.drop-zone p {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.drop-zone .hint {
  font-size: 11px;
  color: var(--text-muted);
  margin: 0;
}

.current-audio {
  margin-top: 16px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.audio-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.audio-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.audio-duration {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'Courier New', monospace;
}

.audio-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-tools {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.ai-section {
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.ai-section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.color-picker-row {
  display: flex;
  gap: 8px;
}

.color-picker-row .color-input {
  width: 60px;
  padding: 2px;
  height: 36px;
  flex-shrink: 0;
}

.color-picker-row .form-input:last-child {
  flex: 1;
}

.color-inputs {
  display: flex;
  gap: 4px;
}

.color-inputs .form-input {
  flex: 1;
  text-align: center;
}

.bg-type-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}

.bg-type-btn {
  padding: 8px 4px;
  background: var(--bg-track);
  border: 2px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.bg-type-btn:hover {
  border-color: var(--accent-secondary);
}

.bg-type-btn.active {
  border-color: var(--accent-primary);
  background: rgba(233, 69, 96, 0.1);
  color: var(--accent-primary);
}

.recording-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.recording-status.recording {
  background: rgba(233, 69, 96, 0.1);
  color: var(--accent-primary);
}

.recording-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--text-muted);
}

.recording-status.recording .recording-dot {
  background: var(--accent-primary);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
}

.interim-text {
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-muted);
  font-style: italic;
  margin-bottom: 8px;
  min-height: 40px;
}

.final-text {
  padding: 12px;
  background: rgba(16, 185, 129, 0.1);
  border-radius: 8px;
  font-size: 13px;
  color: var(--accent-success);
  margin-bottom: 12px;
  min-height: 40px;
}

.btn.recording {
  background: var(--accent-primary);
  animation: pulse 1.5s infinite;
}

.api-settings {
  margin-bottom: 12px;
}

.progress-bar-container {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background: var(--bg-track);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
  border-radius: 4px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: 'Courier New', monospace;
  min-width: 45px;
  text-align: right;
}

.generated-subtitles {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.subtitle-preview-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 12px 0;
  max-height: 120px;
  overflow-y: auto;
}

.subtitle-preview-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  background: var(--bg-track);
  border-radius: 4px;
  font-size: 11px;
}

.subtitle-time {
  color: var(--accent-secondary);
  font-family: 'Courier New', monospace;
}

.subtitle-text-preview {
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn.btn-success {
  background: var(--accent-success);
  border-color: var(--accent-success);
  color: white;
}

.btn.btn-success:hover {
  background: #059669;
  border-color: #059669;
}

.chroma-key-settings,
.color-threshold-settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
}

.realtime-recognition {
  margin-bottom: 12px;
}
</style>

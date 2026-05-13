<template>
  <div class="console">
    <div class="console-header">
      <div class="history-list">
        <span class="hint">历史:</span>
        <span
          v-for="(item, idx) in commandHistory.slice(-10)"
          :key="idx"
          class="history-item"
          @click="insertFromHistory(item)"
          :title="item"
        >{{ item.split(' ')[0] }}</span>
      </div>
    </div>

    <div class="console-body" ref="bodyRef">
      <div
        v-for="(entry, idx) in output"
        :key="idx"
        class="console-entry"
        :class="entry.type"
      >
        <div class="entry-prompt">{{ entry.type === 'input' ? '>' : '' }}</div>
        <div class="entry-content">
          <pre v-if="entry.type === 'input'" class="cmd-input">{{ entry.content }}</pre>
          <pre v-else-if="entry.type === 'error'" class="cmd-error">{{ entry.content }}</pre>
          <pre v-else class="cmd-output">{{ formatOutput(entry.content) }}</pre>
        </div>
      </div>
    </div>

    <div class="console-input-wrap">
      <div class="input-prompt">></div>
      <div class="input-area" ref="inputWrapRef">
        <textarea
          ref="inputRef"
          v-model="inputValue"
          @keydown="handleKeyDown"
          @input="handleInput"
          @blur="hideSuggestions"
          placeholder="输入 Redis 命令，如: GET mykey"
          rows="1"
          autocomplete="off"
          spellcheck="false"
        ></textarea>

        <div v-if="showSuggestions && suggestions.length > 0" class="suggestions">
          <div
            v-for="(s, idx) in suggestions"
            :key="idx"
            class="suggestion-item"
            :class="{ active: idx === selectedIdx }"
            @mousedown.prevent="applySuggestion(s)"
          >
            <span class="suggestion-cmd">{{ s.cmd }}</span>
            <span class="suggestion-desc">{{ s.desc }}</span>
          </div>
        </div>
      </div>
      <button @click="executeCommand" class="btn-execute" :disabled="!inputValue.trim() || executing">
        {{ executing ? '...' : '执行' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, computed } from 'vue'
import { redisClient } from './RedisClient.js'

const props = defineProps({
  connectionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['error', 'dataChanged'])

const inputRef = ref(null)
const bodyRef = ref(null)
const inputWrapRef = ref(null)
const inputValue = ref('')
const output = ref([])
const commandHistory = ref([])
const historyIndex = ref(-1)
const executing = ref(false)

const showSuggestions = ref(false)
const selectedIdx = ref(0)
const suggestions = ref([])

const REDIS_COMMANDS = [
  { cmd: 'GET', desc: '获取键的值' },
  { cmd: 'SET', desc: '设置键的值' },
  { cmd: 'DEL', desc: '删除键' },
  { cmd: 'EXISTS', desc: '检查键是否存在' },
  { cmd: 'EXPIRE', desc: '设置过期时间(秒)' },
  { cmd: 'TTL', desc: '获取剩余时间' },
  { cmd: 'KEYS', desc: '查找键(支持*)' },
  { cmd: 'SCAN', desc: '增量迭代键' },
  { cmd: 'TYPE', desc: '获取键类型' },
  { cmd: 'RENAME', desc: '重命名键' },
  { cmd: 'INCR', desc: '递增' },
  { cmd: 'DECR', desc: '递减' },
  { cmd: 'INCRBY', desc: '按指定量递增' },
  { cmd: 'DECRBY', desc: '按指定量递减' },
  { cmd: 'APPEND', desc: '追加字符串' },
  { cmd: 'STRLEN', desc: '获取字符串长度' },
  { cmd: 'HGET', desc: '获取哈希字段' },
  { cmd: 'HSET', desc: '设置哈希字段' },
  { cmd: 'HGETALL', desc: '获取所有哈希字段' },
  { cmd: 'HDEL', desc: '删除哈希字段' },
  { cmd: 'HEXISTS', desc: '检查哈希字段' },
  { cmd: 'HKEYS', desc: '获取所有哈希键' },
  { cmd: 'HVALS', desc: '获取所有哈希值' },
  { cmd: 'HLEN', desc: '哈希字段数量' },
  { cmd: 'LPUSH', desc: '列表左侧推入' },
  { cmd: 'RPUSH', desc: '列表右侧推入' },
  { cmd: 'LPOP', desc: '列表左侧弹出' },
  { cmd: 'RPOP', desc: '列表右侧弹出' },
  { cmd: 'LRANGE', desc: '获取列表范围' },
  { cmd: 'LLEN', desc: '列表长度' },
  { cmd: 'SADD', desc: '集合添加成员' },
  { cmd: 'SREM', desc: '集合移除成员' },
  { cmd: 'SMEMBERS', desc: '获取所有集合成员' },
  { cmd: 'SISMEMBER', desc: '检查成员是否存在' },
  { cmd: 'SCARD', desc: '集合大小' },
  { cmd: 'ZADD', desc: '有序集合添加' },
  { cmd: 'ZRANGE', desc: '有序集合范围' },
  { cmd: 'ZREM', desc: '有序集合移除' },
  { cmd: 'ZCARD', desc: '有序集合大小' },
  { cmd: 'ZSCORE', desc: '获取成员分数' },
  { cmd: 'INFO', desc: '服务器信息' },
  { cmd: 'PING', desc: '测试连接' },
  { cmd: 'DBSIZE', desc: '键的数量' },
  { cmd: 'FLUSHDB', desc: '清空当前数据库' },
  { cmd: 'FLUSHALL', desc: '清空所有数据库' },
  { cmd: 'SELECT', desc: '切换数据库' },
  { cmd: 'SLOWLOG', desc: '慢查询日志' },
  { cmd: 'CONFIG', desc: '配置管理' },
  { cmd: 'CLIENT', desc: '客户端管理' },
  { cmd: 'MONITOR', desc: '实时监控' }
]

const filterSuggestions = (text) => {
  if (!text.trim()) return []
  const firstWord = text.trim().split(/\s+/)[0].toUpperCase()
  return REDIS_COMMANDS.filter((c) =>
    c.cmd.startsWith(firstWord)
  ).slice(0, 8)
}

function formatOutput(value) {
  if (value === null || value === undefined) return '(nil)'
  if (typeof value === 'object') {
    if (Array.isArray(value)) {
      if (value.length === 0) return '(empty list or set)'
      return value.map((v, i) => `${i + 1}) ${formatOutput(v)}`).join('\n')
    }
    const entries = Object.entries(value)
    if (entries.length === 0) return '(empty hash)'
    return entries
      .map(([k, v], i) => `${i * 2 + 1}) "${k}"\n${i * 2 + 2}) "${v}"`)
      .join('\n')
  }
  return String(value)
}

function handleInput() {
  const text = inputValue.value
  suggestions.value = filterSuggestions(text)
  showSuggestions.value = suggestions.value.length > 0 && !text.includes(' ')
  selectedIdx.value = 0
  autoResize()
}

function autoResize() {
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
    inputRef.value.style.height = Math.min(inputRef.value.scrollHeight, 120) + 'px'
  }
}

function hideSuggestions() {
  setTimeout(() => {
    showSuggestions.value = false
  }, 150)
}

function applySuggestion(s) {
  const parts = inputValue.value.split(/\s+/)
  parts[0] = s.cmd
  inputValue.value = parts.join(' ')
  showSuggestions.value = false
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.focus()
    }
  })
}

function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (showSuggestions.value && suggestions.value.length > 0) {
      applySuggestion(suggestions.value[selectedIdx.value])
    } else {
      executeCommand()
    }
    return
  }

  if (showSuggestions.value) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      selectedIdx.value = (selectedIdx.value + 1) % suggestions.value.length
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      selectedIdx.value = selectedIdx.value === 0 ? suggestions.value.length - 1 : selectedIdx.value - 1
      return
    }
    if (e.key === 'Tab') {
      e.preventDefault()
      if (suggestions.value.length > 0) {
        applySuggestion(suggestions.value[selectedIdx.value])
      }
      return
    }
    if (e.key === 'Escape') {
      showSuggestions.value = false
      return
    }
  }

  if (e.key === 'ArrowUp') {
    if (commandHistory.value.length > 0 && !inputValue.value.includes('\n')) {
      e.preventDefault()
      if (historyIndex.value === -1) {
        historyIndex.value = commandHistory.value.length - 1
      } else if (historyIndex.value > 0) {
        historyIndex.value--
      }
      inputValue.value = commandHistory.value[historyIndex.value]
      autoResize()
    }
  }

  if (e.key === 'ArrowDown') {
    if (historyIndex.value !== -1 && !inputValue.value.includes('\n')) {
      e.preventDefault()
      if (historyIndex.value < commandHistory.value.length - 1) {
        historyIndex.value++
        inputValue.value = commandHistory.value[historyIndex.value]
      } else {
        historyIndex.value = -1
        inputValue.value = ''
      }
      autoResize()
    }
  }
}

function insertFromHistory(cmd) {
  inputValue.value = cmd
  autoResize()
  nextTick(() => {
    if (inputRef.value) inputRef.value.focus()
  })
}

async function executeCommand() {
  const raw = inputValue.value.trim()
  if (!raw || executing.value) return

  output.value.push({ type: 'input', content: raw })
  commandHistory.value.push(raw)
  historyIndex.value = -1
  inputValue.value = ''
  autoResize()
  scrollToBottom()

  executing.value = true

  try {
    const parts = parseCommand(raw)
    const command = parts[0].toLowerCase()
    const args = parts.slice(1)

    const result = await redisClient.execute(props.connectionId, command, args)
    output.value.push({ type: 'output', content: result })

    const writeCmds = ['set', 'del', 'hset', 'hdel', 'lpush', 'rpush', 'lpop', 'rpop',
      'sadd', 'srem', 'zadd', 'zrem', 'incr', 'decr', 'incrby', 'decrby',
      'append', 'rename', 'expire', 'flushdb', 'flushall', 'select']
    if (writeCmds.includes(command)) {
      emit('dataChanged')
    }
  } catch (error) {
    output.value.push({ type: 'error', content: `(error) ${error.message}` })
  } finally {
    executing.value = false
    scrollToBottom()
  }
}

function parseCommand(str) {
  const result = []
  let current = ''
  let inQuote = false
  let quoteChar = ''

  for (let i = 0; i < str.length; i++) {
    const ch = str[i]

    if (!inQuote && (ch === '"' || ch === "'")) {
      inQuote = true
      quoteChar = ch
    } else if (inQuote && ch === quoteChar) {
      inQuote = false
      quoteChar = ''
    } else if (!inQuote && /\s/.test(ch)) {
      if (current) {
        result.push(current)
        current = ''
      }
    } else {
      current += ch
    }
  }

  if (current) result.push(current)

  return result
}

function scrollToBottom() {
  nextTick(() => {
    if (bodyRef.value) {
      bodyRef.value.scrollTop = bodyRef.value.scrollHeight
    }
  })
}

watch(() => props.connectionId, () => {
  output.value = []
  commandHistory.value = []
})
</script>

<style scoped>
.console {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e1e1e;
  color: #ddd;
  font-family: 'Consolas', 'Monaco', monospace;
}

.console-header {
  padding: 8px 12px;
  border-bottom: 1px solid #333;
  background: #252526;
}

.history-list {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.hint {
  font-size: 11px;
  color: #666;
}

.history-item {
  padding: 3px 8px;
  background: #2d2d2d;
  border-radius: 3px;
  font-size: 11px;
  cursor: pointer;
  color: #4ec9b0;
}

.history-item:hover {
  background: #3a3a3a;
}

.console-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  font-size: 13px;
}

.console-entry {
  display: flex;
  margin-bottom: 8px;
}

.entry-prompt {
  width: 20px;
  color: #4ec9b0;
  flex-shrink: 0;
}

.entry-content {
  flex: 1;
  overflow-x: auto;
}

.entry-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: inherit;
  font-size: 13px;
}

.cmd-input {
  color: #dcdcaa;
}

.cmd-error {
  color: #f48771;
}

.cmd-output {
  color: #ce9178;
}

.console-input-wrap {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #333;
  background: #252526;
}

.input-prompt {
  color: #4ec9b0;
  font-size: 13px;
  padding-top: 8px;
  flex-shrink: 0;
}

.input-area {
  flex: 1;
  position: relative;
}

.input-area textarea {
  width: 100%;
  min-height: 32px;
  max-height: 120px;
  padding: 6px 10px;
  background: #1e1e1e;
  border: 1px solid #3c3c3c;
  border-radius: 4px;
  color: #ddd;
  font-family: inherit;
  font-size: 13px;
  resize: none;
  line-height: 1.5;
}

.input-area textarea:focus {
  outline: none;
  border-color: #007acc;
}

.suggestions {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  margin-bottom: 4px;
  background: #252526;
  border: 1px solid #3c3c3c;
  border-radius: 4px;
  max-height: 240px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.4);
}

.suggestion-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 10px;
  cursor: pointer;
  font-size: 12px;
}

.suggestion-item:hover,
.suggestion-item.active {
  background: #094771;
}

.suggestion-cmd {
  color: #4ec9b0;
  font-weight: 500;
}

.suggestion-desc {
  color: #858585;
  font-size: 11px;
}

.btn-execute {
  padding: 6px 16px;
  background: #007acc;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  flex-shrink: 0;
  margin-top: 4px;
}

.btn-execute:hover:not(:disabled) {
  background: #005a9e;
}

.btn-execute:disabled {
  background: #3c3c3c;
  cursor: not-allowed;
  color: #858585;
}
</style>

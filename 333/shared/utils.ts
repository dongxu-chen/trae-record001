import * as CryptoJS from 'crypto-js'
import { v4 as uuidv4 } from 'uuid'
import type { 
  ClipboardContent, 
  EncryptedData, 
  ChunkData, 
  PasswordDerivedKey, 
  FileData,
  FilterRule,
  FilterResult,
  SensitivePattern,
  SensitivePatternType,
  PairingSession,
  TransferSpeedStats,
  NetworkStats,
  FilterAction,
  FilterType
} from './types'
import { 
  ClipboardDataType, 
  DEFAULT_KDF_ITERATIONS, 
  DEFAULT_CHUNK_SIZE,
  PairingStatus
} from './types'

export function generateId(): string {
  return uuidv4()
}

export function generateDeviceId(): string {
  const random = CryptoJS.lib.WordArray.random(8).toString()
  const timestamp = Date.now().toString(36)
  return `${timestamp}-${random}`
}

export function generateEncryptionKey(): string {
  return CryptoJS.lib.WordArray.random(32).toString()
}

export function generateSalt(): string {
  return CryptoJS.lib.WordArray.random(16).toString()
}

export function hashData(data: string): string {
  return CryptoJS.SHA256(data).toString()
}

export function calculateChecksum(data: string): string {
  return CryptoJS.MD5(data).toString()
}

export function verifyChecksum(data: string, expectedChecksum: string): boolean {
  const actualChecksum = calculateChecksum(data)
  return actualChecksum === expectedChecksum
}

export async function deriveKeyFromPassword(
  password: string,
  salt?: string,
  iterations: number = DEFAULT_KDF_ITERATIONS
): Promise<PasswordDerivedKey> {
  const actualSalt = salt || generateSalt()
  
  const key = CryptoJS.PBKDF2(password, actualSalt, {
    keySize: 256 / 32,
    iterations: iterations,
    hasher: CryptoJS.algo.SHA256
  })
  
  const passwordHash = CryptoJS.SHA256(password + actualSalt).toString()
  
  return {
    key: key.toString(),
    salt: actualSalt,
    iterations: iterations,
    hash: passwordHash
  }
}

export async function verifyPassword(
  password: string,
  storedHash: string,
  storedSalt: string,
  iterations: number = DEFAULT_KDF_ITERATIONS
): Promise<boolean> {
  const derived = await deriveKeyFromPassword(password, storedSalt, iterations)
  return derived.hash === storedHash
}

export function encryptData(data: string, key: string): EncryptedData {
  const iv = CryptoJS.lib.WordArray.random(16)
  const encrypted = CryptoJS.AES.encrypt(data, key, {
    iv: iv,
    mode: CryptoJS.mode.GCM,
    padding: CryptoJS.pad.NoPadding
  })
  
  return {
    iv: iv.toString(),
    encrypted: encrypted.toString()
  }
}

export function decryptData(encryptedData: EncryptedData, key: string): string {
  const decrypted = CryptoJS.AES.decrypt(encryptedData.encrypted, key, {
    iv: CryptoJS.enc.Hex.parse(encryptedData.iv),
    mode: CryptoJS.mode.GCM,
    padding: CryptoJS.pad.NoPadding
  })
  
  return decrypted.toString(CryptoJS.enc.Utf8)
}

export function encryptClipboardContent(content: ClipboardContent, key: string): EncryptedData {
  const contentWithChecksum = addChecksumsToContent(content)
  const dataStr = JSON.stringify(contentWithChecksum)
  return encryptData(dataStr, key)
}

export function decryptClipboardContent(encryptedData: EncryptedData, key: string): ClipboardContent {
  const dataStr = decryptData(encryptedData, key)
  const content = JSON.parse(dataStr) as ClipboardContent
  const isValid = verifyContentChecksums(content)
  
  if (!isValid) {
    throw new Error('内容校验和验证失败，数据可能已损坏')
  }
  
  return content
}

export function addChecksumsToContent(content: ClipboardContent): ClipboardContent {
  const contentCopy = JSON.parse(JSON.stringify(content)) as ClipboardContent
  
  switch (contentCopy.type) {
    case ClipboardDataType.TEXT:
      contentCopy.checksum = calculateChecksum(contentCopy.data as string)
      break
      
    case ClipboardDataType.IMAGE: {
      const imageData = contentCopy.data as FileData
      imageData.checksum = calculateChecksum(imageData.data)
      contentCopy.checksum = imageData.checksum
      break
    }
      
    case ClipboardDataType.FILE:
    case ClipboardDataType.FILES: {
      const files = Array.isArray(contentCopy.data) 
        ? contentCopy.data as FileData[] 
        : [contentCopy.data as FileData]
      
      let combinedData = ''
      for (const file of files) {
        file.checksum = calculateChecksum(file.data)
        combinedData += file.checksum
      }
      
      contentCopy.checksum = calculateChecksum(combinedData)
      break
    }
  }
  
  return contentCopy
}

export function verifyContentChecksums(content: ClipboardContent): boolean {
  if (!content.checksum) {
    return true
  }
  
  switch (content.type) {
    case ClipboardDataType.TEXT:
      return verifyChecksum(content.data as string, content.checksum)
      
    case ClipboardDataType.IMAGE: {
      const imageData = content.data as FileData
      if (imageData.checksum && !verifyChecksum(imageData.data, imageData.checksum)) {
        return false
      }
      return verifyChecksum(imageData.data, content.checksum)
    }
      
    case ClipboardDataType.FILE:
    case ClipboardDataType.FILES: {
      const files = Array.isArray(content.data) 
        ? content.data as FileData[] 
        : [content.data as FileData]
      
      let combinedData = ''
      for (const file of files) {
        if (file.checksum && !verifyChecksum(file.data, file.checksum)) {
          return false
        }
        combinedData += file.checksum || calculateChecksum(file.data)
      }
      
      return verifyChecksum(combinedData, content.checksum)
    }
      
    default:
      return true
  }
}

export function createChunks(
  data: string,
  contentId: string,
  chunkSize: number = DEFAULT_CHUNK_SIZE
): ChunkData[] {
  const chunks: ChunkData[] = []
  const totalChunks = Math.ceil(data.length / chunkSize)
  
  for (let i = 0; i < totalChunks; i++) {
    const start = i * chunkSize
    const end = start + chunkSize
    const chunkData = data.slice(start, end)
    
    chunks.push({
      transferId: `${contentId}-${Date.now()}`,
      chunkIndex: i,
      totalChunks,
      data: chunkData,
      checksum: calculateChecksum(chunkData),
      timestamp: Date.now()
    })
  }
  
  return chunks
}

export function verifyChunk(chunk: ChunkData): boolean {
  return verifyChecksum(chunk.data, chunk.checksum)
}

export function assembleChunks(chunks: ChunkData[]): string {
  const sorted = [...chunks].sort((a, b) => a.chunkIndex - b.chunkIndex)
  
  for (let i = 0; i < sorted.length; i++) {
    if (sorted[i].chunkIndex !== i) {
      throw new Error(`分片不完整，缺少索引 ${i}`)
    }
    if (!verifyChunk(sorted[i])) {
      throw new Error(`分片 ${i} 校验和验证失败`)
    }
  }
  
  return sorted.map(c => c.data).join('')
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins} 分钟前`
  if (diffHours < 24) return `${diffHours} 小时前`
  if (diffDays < 7) return `${diffDays} 天前`
  
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function isPrivateIP(ip: string): boolean {
  const privateRanges = [
    /^10\./,
    /^172\.(1[6-9]|2[0-9]|3[0-1])\./,
    /^192\.168\./,
    /^127\./,
    /^localhost$/,
    /^::1$/,
    /^fc00:/,
    /^fe80:/
  ]
  return privateRanges.some(range => range.test(ip))
}

export function chunkArray<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = []
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size))
  }
  return chunks
}

export function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binaryString = atob(base64)
  const bytes = new Uint8Array(binaryString.length)
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i)
  }
  return bytes.buffer
}

export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 3,
  initialDelay: number = 1000,
  backoffFactor: number = 2
): Promise<T> {
  return new Promise((resolve, reject) => {
    let attempts = 0
    
    const attempt = async () => {
      try {
        attempts++
        const result = await fn()
        resolve(result)
      } catch (error) {
        if (attempts >= maxAttempts) {
          reject(error)
          return
        }
        
        const delayMs = initialDelay * Math.pow(backoffFactor, attempts - 1)
        setTimeout(attempt, delayMs)
      }
    }
    
    attempt()
  })
}

export function generateVerificationCode(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  let code = ''
  for (let i = 0; i < 6; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return code
}

export function generateQRCodeData(deviceId: string, deviceName: string, verificationCode: string): string {
  const payload = {
    t: 'clipboard-sync',
    d: deviceId,
    n: deviceName,
    c: verificationCode,
    ts: Date.now()
  }
  return btoa(JSON.stringify(payload))
}

export function parseQRCodeData(qrCodeData: string): {
  deviceId: string
  deviceName: string
  verificationCode: string
  timestamp: number
} | null {
  try {
    const decoded = atob(qrCodeData)
    const payload = JSON.parse(decoded)
    if (payload.t !== 'clipboard-sync') {
      return null
    }
    return {
      deviceId: payload.d,
      deviceName: payload.n,
      verificationCode: payload.c,
      timestamp: payload.ts
    }
  } catch {
    return null
  }
}

export function createPairingSession(
  deviceId: string,
  deviceName: string,
  deviceType: string = 'desktop'
): PairingSession {
  const verificationCode = generateVerificationCode()
  const qrCodeData = generateQRCodeData(deviceId, deviceName, verificationCode)
  
  return {
    sessionId: generateId(),
    verificationCode,
    qrCodeData,
    status: PairingStatus.WAITING,
    expiresAt: Date.now() + 5 * 60 * 1000,
    deviceInfo: {
      deviceId,
      deviceName,
      deviceType
    }
  }
}

export function isPairingExpired(session: PairingSession): boolean {
  return Date.now() > session.expiresAt
}

export function validatePairingCode(session: PairingSession, inputCode: string): boolean {
  if (isPairingExpired(session)) {
    return false
  }
  return session.verificationCode.toUpperCase() === inputCode.toUpperCase()
}

const SENSITIVE_PATTERNS: Record<SensitivePatternType, SensitivePattern> = {
  [SensitivePatternType.EMAIL]: {
    type: SensitivePatternType.EMAIL,
    name: '邮箱地址',
    pattern: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
    description: '检测文本中的邮箱地址',
    enabled: true
  },
  [SensitivePatternType.PHONE]: {
    type: SensitivePatternType.PHONE,
    name: '手机号码',
    pattern: '1[3-9]\\d{9}',
    description: '检测中国大陆手机号码',
    enabled: true
  },
  [SensitivePatternType.ID_CARD]: {
    type: SensitivePatternType.ID_CARD,
    name: '身份证号',
    pattern: '[1-9]\\d{5}(18|19|20)\\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx]',
    description: '检测中国大陆18位身份证号码',
    enabled: true
  },
  [SensitivePatternType.BANK_CARD]: {
    type: SensitivePatternType.BANK_CARD,
    name: '银行卡号',
    pattern: '[1-9]\\d{14,18}',
    description: '检测银行卡号（15-19位数字）',
    enabled: true
  },
  [SensitivePatternType.PASSWORD]: {
    type: SensitivePatternType.PASSWORD,
    name: '密码字段',
    pattern: '(password|passwd|pwd|secret|token)\\s*[:=]\\s*\\S+',
    description: '检测可能的密码或密钥字段',
    enabled: true
  },
  [SensitivePatternType.URL]: {
    type: SensitivePatternType.URL,
    name: 'URL链接',
    pattern: 'https?://[^\\s]+',
    description: '检测文本中的URL链接',
    enabled: true
  },
  [SensitivePatternType.IP_ADDRESS]: {
    type: SensitivePatternType.IP_ADDRESS,
    name: 'IP地址',
    pattern: '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}',
    description: '检测IPv4地址',
    enabled: true
  },
  [SensitivePatternType.CUSTOM]: {
    type: SensitivePatternType.CUSTOM,
    name: '自定义',
    pattern: '',
    description: '自定义敏感内容模式',
    enabled: false
  }
}

export function getSensitivePatterns(): SensitivePattern[] {
  return Object.values(SENSITIVE_PATTERNS)
}

export function getSensitivePattern(type: SensitivePatternType): SensitivePattern | undefined {
  return SENSITIVE_PATTERNS[type]
}

export function detectSensitiveContent(
  text: string,
  enabledPatterns: SensitivePatternType[] = []
): { pattern: SensitivePatternType; matched: string; index: number }[] {
  const results: { pattern: SensitivePatternType; matched: string; index: number }[] = []
  
  for (const patternType of enabledPatterns) {
    const patternConfig = SENSITIVE_PATTERNS[patternType]
    if (!patternConfig || !patternConfig.enabled || !patternConfig.pattern) {
      continue
    }
    
    try {
      const regex = new RegExp(patternConfig.pattern, 'gi')
      let match: RegExpExecArray | null
      while ((match = regex.exec(text)) !== null) {
        results.push({
          pattern: patternType,
          matched: match[0],
          index: match.index
        })
      }
    } catch {
      continue
    }
  }
  
  return results
}

export function maskSensitiveContent(
  text: string,
  matchedContents: { pattern: SensitivePatternType; matched: string; index: number }[]
): string {
  let result = text
  
  const sorted = [...matchedContents].sort((a, b) => b.index - a.index)
  
  for (const item of sorted) {
    const maskLength = Math.max(3, Math.floor(item.matched.length * 0.5))
    const mask = '*'.repeat(maskLength)
    const visibleStart = Math.floor((item.matched.length - maskLength) / 2)
    const visibleEnd = visibleStart + maskLength
    const masked = item.matched.slice(0, visibleStart) + mask + item.matched.slice(visibleEnd)
    result = result.slice(0, item.index) + masked + result.slice(item.index + item.matched.length)
  }
  
  return result
}

export function applyFilterRule(text: string, rule: FilterRule): FilterResult {
  if (!rule.enabled) {
    return { matched: false, action: 'allow' as FilterAction }
  }
  
  try {
    let regex: RegExp
    const flags = rule.caseSensitive ? 'g' : 'gi'
    
    if (rule.type === FilterType.REGEX) {
      regex = new RegExp(rule.pattern, flags)
    } else if (rule.type === FilterType.KEYWORD) {
      const escaped = rule.pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      regex = new RegExp(escaped, flags)
    } else {
      return { matched: false, action: 'allow' as FilterAction }
    }
    
    const match = regex.exec(text)
    if (match) {
      return {
        matched: true,
        ruleId: rule.id,
        ruleName: rule.name,
        action: rule.action,
        matchedContent: match[0]
      }
    }
    
    return { matched: false, action: 'allow' as FilterAction }
  } catch {
    return { matched: false, action: 'allow' as FilterAction }
  }
}

export function applyAllFilterRules(
  content: ClipboardContent,
  rules: FilterRule[],
  enabledSensitivePatterns: SensitivePatternType[] = [],
  enableSensitiveDetection: boolean = false
): FilterResult {
  if (content.type !== ClipboardDataType.TEXT) {
    if (content.type === ClipboardDataType.FILE || content.type === ClipboardDataType.FILES) {
      const files = Array.isArray(content.data) ? content.data as FileData[] : [content.data as FileData]
      for (const file of files) {
        for (const rule of rules) {
          if (rule.type === FilterType.FILE_TYPE) {
            const fileTypes = rule.pattern.split(',').map(t => t.trim().toLowerCase())
            if (fileTypes.some(ft => file.name.toLowerCase().endsWith(ft))) {
              return {
                matched: true,
                ruleId: rule.id,
                ruleName: rule.name,
                action: rule.action,
                matchedContent: file.name
              }
            }
          }
          if (rule.type === FilterType.FILE_SIZE) {
            const maxSize = parseInt(rule.pattern) * 1024 * 1024
            if (file.size > maxSize) {
              return {
                matched: true,
                ruleId: rule.id,
                ruleName: rule.name,
                action: rule.action,
                matchedContent: `${file.name} (${formatFileSize(file.size)})`
              }
            }
          }
        }
      }
    }
    return { matched: false, action: 'allow' as FilterAction }
  }
  
  const text = content.data as string
  
  for (const rule of rules) {
    const result = applyFilterRule(text, rule)
    if (result.matched && result.action !== 'allow') {
      return result
    }
  }
  
  if (enableSensitiveDetection && enabledSensitivePatterns.length > 0) {
    const detections = detectSensitiveContent(text, enabledSensitivePatterns)
    if (detections.length > 0) {
      return {
        matched: true,
        action: 'ask' as FilterAction,
        matchedContent: `检测到 ${detections.length} 个敏感内容`
      }
    }
  }
  
  return { matched: false, action: 'allow' as FilterAction }
}

export function formatSpeed(bytesPerSecond: number): string {
  if (bytesPerSecond === 0) return '0 B/s'
  const units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
  const unitIndex = Math.floor(Math.log(bytesPerSecond) / Math.log(1024))
  const value = bytesPerSecond / Math.pow(1024, unitIndex)
  return `${value.toFixed(2)} ${units[Math.min(unitIndex, units.length - 1)]}`
}

export function formatLatency(ms: number): string {
  if (ms < 1) return '<1ms'
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

export function createTransferStats(
  transferId: string,
  peerId: string,
  peerName: string,
  totalBytes: number,
  connectionMode: string
): TransferSpeedStats {
  return {
    transferId,
    peerId,
    peerName,
    startTime: Date.now(),
    totalBytes,
    transferredBytes: 0,
    currentSpeed: 0,
    averageSpeed: 0,
    peakSpeed: 0,
    latency: 0,
    chunkSize: DEFAULT_CHUNK_SIZE,
    totalChunks: Math.ceil(totalBytes / DEFAULT_CHUNK_SIZE),
    transferredChunks: 0,
    failedChunks: 0,
    retriedChunks: 0,
    connectionMode: connectionMode as any,
    status: 'pending' as any
  }
}

export function updateTransferStats(
  stats: TransferSpeedStats,
  transferredBytes: number,
  latency: number
): TransferSpeedStats {
  const now = Date.now()
  const elapsed = (now - stats.startTime) / 1000
  const newTransferred = stats.transferredBytes + transferredBytes
  
  const currentSpeed = elapsed > 0 ? newTransferred / elapsed : 0
  
  return {
    ...stats,
    transferredBytes: newTransferred,
    transferredChunks: Math.ceil(newTransferred / stats.chunkSize),
    currentSpeed,
    averageSpeed: currentSpeed,
    peakSpeed: Math.max(stats.peakSpeed, currentSpeed),
    latency
  }
}

export function createNetworkStats(): NetworkStats {
  return {
    timestamp: Date.now(),
    uploadSpeed: 0,
    downloadSpeed: 0,
    totalUploaded: 0,
    totalDownloaded: 0,
    activeTransfers: 0,
    connectedPeers: 0,
    averageLatency: 0
  }
}

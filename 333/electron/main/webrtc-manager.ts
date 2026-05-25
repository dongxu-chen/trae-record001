import { WebSocket } from 'ws'
import SimplePeer from 'simple-peer'
import * as os from 'os'
import { EventEmitter } from 'events'
import type { 
  AppSettings, ClipboardContent, Device, EncryptedData, SignalingMessage,
  ChunkData, ChunkAck, TransferSession, TransferStatus, ConnectionMode,
  TurnServerConfig
} from '@shared/types'
import { ConnectionMode as CM, TransferStatus as TS, DEFAULT_CHUNK_SIZE, DEFAULT_MAX_RETRY_DELAY } from '@shared/types'
import { 
  encryptClipboardContent, decryptClipboardContent, isPrivateIP, 
  createChunks, verifyChunk, assembleChunks, verifyContentChecksums,
  delay, calculateChecksum, verifyChecksum
} from '@shared/utils'

interface WebRTCManagerOptions {
  deviceId: string
  deviceName: string
  signalingServer: string
  encryptionKey: string
  lanOnly: boolean
  useRelayOnFailure: boolean
  maxRetryAttempts: number
  turnServers: TurnServerConfig[]
  onMessage: (content: ClipboardContent) => void
  onDeviceListChange: (devices: Device[]) => void
  onConnectionChange: (isConnected: boolean) => void
  onTransferStatus?: (transferId: string, status: TransferStatus, progress: number) => void
}

interface PeerConnection {
  peerId: string
  peer: SimplePeer.Instance
  isConnected: boolean
  isLocal: boolean
  connectionMode: ConnectionMode
  lastSeen: number
  deviceName: string
  lastConnectionAttempt: number
  relayFallbackAttempted: boolean
  iceGatheringComplete: boolean
  iceCandidateCount: number
  outgoingTransfers: Map<string, TransferSession>
  incomingTransfers: Map<string, TransferSession>
  pendingChunks: Map<string, { data: string; retryCount: number }>
}

interface ProtocolMessage {
  type: 'chunk' | 'chunk_ack' | 'chunk_request' | 'transfer_complete' | 'transfer_error'
  payload: any
}

export class WebRTCManager {
  private options: WebRTCManagerOptions
  private ws: WebSocket | null = null
  private peers: Map<string, PeerConnection> = new Map()
  private devices: Device[] = []
  private reconnectTimer: NodeJS.Timeout | null = null
  private pingTimer: NodeJS.Timeout | null = null
  private cleanupTimer: NodeJS.Timeout | null = null
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 10
  private eventEmitter: EventEmitter = new EventEmitter()

  constructor(options: WebRTCManagerOptions) {
    this.options = options
  }

  async connect(): Promise<void> {
    try {
      this.ws = new WebSocket(this.options.signalingServer)
      
      this.ws.on('open', () => {
        console.log('已连接到信令服务器')
        this.reconnectAttempts = 0
        this.sendSignalingMessage({
          type: 'join',
          from: this.options.deviceId,
          payload: {
            deviceName: this.options.deviceName,
            deviceType: 'desktop',
            supportsRelay: this.options.useRelayOnFailure
          },
          timestamp: Date.now()
        })
        this.startPing()
        this.startCleanup()
        this.options.onConnectionChange(true)
      })

      this.ws.on('message', (data) => {
        try {
          const message: SignalingMessage = JSON.parse(data.toString())
          this.handleSignalingMessage(message)
        } catch (e) {
          console.error('解析信令消息失败:', e)
        }
      })

      this.ws.on('close', () => {
        console.log('信令服务器连接断开')
        this.stopPing()
        this.stopCleanup()
        this.options.onConnectionChange(false)
        this.attemptReconnect()
      })

      this.ws.on('error', (error) => {
        console.error('WebSocket 错误:', error)
      })

    } catch (e) {
      console.error('连接信令服务器失败:', e)
      this.attemptReconnect()
      throw e
    }
  }

  disconnect(): void {
    this.stopPing()
    this.stopCleanup()
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    
    for (const [peerId, conn] of this.peers) {
      try {
        conn.peer.destroy()
      } catch (e) {
        console.error(`销毁连接 ${peerId} 失败:`, e)
      }
    }
    this.peers.clear()
    
    if (this.ws) {
      try {
        this.ws.close()
      } catch (e) {
        console.error('关闭 WebSocket 失败:', e)
      }
      this.ws = null
    }
    
    this.devices = []
    this.options.onDeviceListChange([])
    this.options.onConnectionChange(false)
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('达到最大重连次数，停止重连')
      return
    }
    
    this.reconnectAttempts++
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 30000)
    
    console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})，延迟 ${delay}ms`)
    
    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(e => {
        console.error('重连失败:', e)
      })
    }, delay)
  }

  private startPing(): void {
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.sendSignalingMessage({
          type: 'ping',
          from: this.options.deviceId,
          timestamp: Date.now()
        })
      }
    }, 30000)
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
  }

  private startCleanup(): void {
    this.cleanupTimer = setInterval(() => {
      this.cleanupStaleTransfers()
    }, 60000)
  }

  private stopCleanup(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer)
      this.cleanupTimer = null
    }
  }

  private cleanupStaleTransfers(): void {
    const now = Date.now()
    const timeout = 5 * 60 * 1000

    for (const conn of this.peers.values()) {
      for (const [transferId, transfer] of conn.outgoingTransfers) {
        if (now - transfer.lastActivity > timeout) {
          console.log(`清理超时的传出传输: ${transferId}`)
          conn.outgoingTransfers.delete(transferId)
        }
      }
      
      for (const [transferId, transfer] of conn.incomingTransfers) {
        if (now - transfer.lastActivity > timeout) {
          console.log(`清理超时的传入传输: ${transferId}`)
          conn.incomingTransfers.delete(transferId)
        }
      }
    }
  }

  private sendSignalingMessage(message: SignalingMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    }
  }

  private handleSignalingMessage(message: SignalingMessage): void {
    switch (message.type) {
      case 'devices':
        this.handleDeviceList(message.payload.devices)
        break
      case 'offer':
        this.handleOffer(message)
        break
      case 'answer':
        this.handleAnswer(message)
        break
      case 'candidate':
        this.handleCandidate(message)
        break
      case 'leave':
        this.handlePeerLeave(message.from)
        break
      case 'relay-config':
        this.handleRelayConfig(message)
        break
    }
  }

  private handleDeviceList(devices: Device[]): void {
    this.devices = devices.filter(d => d.id !== this.options.deviceId)
    
    if (this.options.lanOnly) {
      this.devices = this.devices.filter(d => d.isLocal)
    }
    
    for (const device of this.devices) {
      if (!this.peers.has(device.id) && device.isOnline) {
        this.connectToPeer(device.id, device.name)
      }
    }
    
    this.updateDeviceConnectionModes()
    this.options.onDeviceListChange([...this.devices])
  }

  private updateDeviceConnectionModes(): void {
    for (const device of this.devices) {
      const conn = this.peers.get(device.id)
      if (conn) {
        device.connectionMode = conn.connectionMode
      }
    }
  }

  private getIceServers(useRelay: boolean = false): RTCIceServer[] {
    const servers: RTCIceServer[] = [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' }
    ]

    if (useRelay && this.options.useRelayOnFailure) {
      for (const turnServer of this.options.turnServers) {
        const server: RTCIceServer = {
          urls: turnServer.urls
        }
        if (turnServer.username) {
          server.username = turnServer.username
        }
        if (turnServer.credential) {
          server.credential = turnServer.credential
        }
        servers.push(server)
      }
    }

    return servers
  }

  private connectToPeer(peerId: string, peerName: string, initiator: boolean = true, useRelay: boolean = false): void {
    if (this.peers.has(peerId)) return

    const localIPs = this.getLocalIPs()
    
    const peer = new SimplePeer({
      initiator,
      trickle: true,
      config: {
        iceServers: this.getIceServers(useRelay)
      }
    })

    const connection: PeerConnection = {
      peerId,
      peer,
      isConnected: false,
      isLocal: false,
      connectionMode: useRelay ? CM.RELAY : CM.DIRECT,
      lastSeen: Date.now(),
      deviceName: peerName,
      lastConnectionAttempt: Date.now(),
      relayFallbackAttempted: useRelay,
      iceGatheringComplete: false,
      iceCandidateCount: 0,
      outgoingTransfers: new Map(),
      incomingTransfers: new Map(),
      pendingChunks: new Map()
    }

    this.peers.set(peerId, connection)

    peer.on('signal', (data) => {
      if (data.type === 'offer') {
        this.sendSignalingMessage({
          type: 'offer',
          from: this.options.deviceId,
          to: peerId,
          payload: {
            signal: data,
            deviceName: this.options.deviceName,
            localIPs,
            useRelay
          },
          timestamp: Date.now()
        })
      } else if (data.type === 'answer') {
        this.sendSignalingMessage({
          type: 'answer',
          from: this.options.deviceId,
          to: peerId,
          payload: {
            signal: data,
            localIPs,
            useRelay
          },
          timestamp: Date.now()
        })
      } else if (data.candidate) {
        connection.iceCandidateCount++
        this.sendSignalingMessage({
          type: 'candidate',
          from: this.options.deviceId,
          to: peerId,
          payload: data,
          timestamp: Date.now()
        })
      }
    })

    peer.on('connect', () => {
      console.log(`已连接到对等方: ${peerName} (模式: ${connection.connectionMode})`)
      connection.isConnected = true
      connection.lastSeen = Date.now()
      
      if (connection.isLocal) {
        connection.connectionMode = CM.LAN
      }
      
      this.updateDeviceOnlineStatus(peerId, true)
      this.eventEmitter.emit('peer:connected', peerId, connection.connectionMode)
    })

    peer.on('data', (data) => {
      try {
        connection.lastSeen = Date.now()
        this.handlePeerData(connection, data.toString())
      } catch (e) {
        console.error('处理接收数据失败:', e)
      }
    })

    peer.on('close', () => {
      console.log(`与对等方 ${peerName} 的连接已关闭`)
      connection.isConnected = false
      this.peers.delete(peerId)
      this.updateDeviceOnlineStatus(peerId, false)
    })

    peer.on('error', (err) => {
      console.error(`与对等方 ${peerName} 的连接错误:`, err)
      
      if (!connection.relayFallbackAttempted && this.options.useRelayOnFailure) {
        console.log(`尝试使用 TURN 中继重新连接到 ${peerName}`)
        this.attemptRelayFallback(peerId, peerName, initiator)
      } else {
        connection.isConnected = false
        this.peers.delete(peerId)
        this.updateDeviceOnlineStatus(peerId, false)
      }
    })

    setTimeout(() => {
      if (!connection.isConnected && !connection.relayFallbackAttempted && this.options.useRelayOnFailure) {
        console.log(`连接超时，尝试使用 TURN 中继重新连接到 ${peerName}`)
        try {
          peer.destroy()
        } catch (e) {}
        this.peers.delete(peerId)
        this.attemptRelayFallback(peerId, peerName, initiator)
      }
    }, 15000)
  }

  private attemptRelayFallback(peerId: string, peerName: string, initiator: boolean): void {
    this.sendSignalingMessage({
      type: 'relay-config',
      from: this.options.deviceId,
      to: peerId,
      payload: {
        action: 'relay_fallback',
        initiator
      },
      timestamp: Date.now()
    })

    this.connectToPeer(peerId, peerName, initiator, true)
  }

  private handleRelayConfig(message: SignalingMessage): void {
    if (message.to !== this.options.deviceId) return
    
    const { action, initiator } = message.payload
    
    if (action === 'relay_fallback' && this.options.useRelayOnFailure) {
      const existingConn = this.peers.get(message.from)
      if (existingConn) {
        try {
          existingConn.peer.destroy()
        } catch (e) {}
        this.peers.delete(message.from)
      }
      
      setTimeout(() => {
        this.connectToPeer(message.from, message.payload.deviceName || '未知设备', !initiator, true)
      }, 500)
    }
  }

  private handleOffer(message: SignalingMessage): void {
    if (message.to !== this.options.deviceId) return
    
    const { signal, deviceName, localIPs, useRelay } = message.payload
    
    const peerIsLocal = this.checkIsLocalConnection(localIPs)
    
    if (this.options.lanOnly && !peerIsLocal) {
      console.log('拒绝非局域网连接')
      return
    }
    
    this.connectToPeer(message.from, deviceName, false, useRelay || false)
    
    const connection = this.peers.get(message.from)
    if (connection) {
      connection.isLocal = peerIsLocal
      if (peerIsLocal) {
        connection.connectionMode = CM.LAN
      } else if (useRelay) {
        connection.connectionMode = CM.RELAY
      }
      connection.peer.signal(signal)
    }
  }

  private handleAnswer(message: SignalingMessage): void {
    if (message.to !== this.options.deviceId) return
    
    const { signal, localIPs, useRelay } = message.payload
    const connection = this.peers.get(message.from)
    
    if (connection) {
      connection.isLocal = this.checkIsLocalConnection(localIPs)
      if (connection.isLocal) {
        connection.connectionMode = CM.LAN
      } else if (useRelay) {
        connection.connectionMode = CM.RELAY
      }
      connection.peer.signal(signal)
    }
  }

  private handleCandidate(message: SignalingMessage): void {
    if (message.to !== this.options.deviceId) return
    
    const connection = this.peers.get(message.from)
    if (connection && message.payload) {
      connection.peer.signal(message.payload)
    }
  }

  private handlePeerLeave(peerId: string): void {
    const connection = this.peers.get(peerId)
    if (connection) {
      try {
        connection.peer.destroy()
      } catch (e) {
        console.error('销毁连接失败:', e)
      }
      this.peers.delete(peerId)
    }
    this.updateDeviceOnlineStatus(peerId, false)
  }

  private updateDeviceOnlineStatus(peerId: string, isOnline: boolean): void {
    const device = this.devices.find(d => d.id === peerId)
    if (device) {
      device.isOnline = isOnline
      device.lastSeen = Date.now()
      const conn = this.peers.get(peerId)
      if (conn) {
        device.connectionMode = conn.connectionMode
      }
    }
    this.options.onDeviceListChange([...this.devices])
  }

  private handlePeerData(connection: PeerConnection, dataStr: string): void {
    try {
      const message: ProtocolMessage = JSON.parse(dataStr)
      
      switch (message.type) {
        case 'chunk':
          this.handleChunk(connection, message.payload as ChunkData)
          break
        case 'chunk_ack':
          this.handleChunkAck(connection, message.payload as ChunkAck)
          break
        case 'chunk_request':
          this.handleChunkRequest(connection, message.payload)
          break
        case 'transfer_complete':
          this.handleTransferComplete(connection, message.payload)
          break
        case 'transfer_error':
          this.handleTransferError(connection, message.payload)
          break
        default:
          this.handleDirectMessage(connection, dataStr)
      }
    } catch {
      this.handleDirectMessage(connection, dataStr)
    }
  }

  private handleChunk(connection: PeerConnection, chunk: ChunkData): void {
    const transfer = connection.incomingTransfers.get(chunk.transferId)
    
    if (!transfer) {
      const newTransfer: TransferSession = {
        id: chunk.transferId,
        contentId: chunk.transferId.split('-')[0],
        peerId: connection.peerId,
        status: TS.TRANSFERRING,
        totalChunks: chunk.totalChunks,
        receivedChunks: new Map(),
        failedChunks: new Set(),
        retryCount: 0,
        startTime: Date.now(),
        lastActivity: Date.now()
      }
      connection.incomingTransfers.set(chunk.transferId, newTransfer)
      
      if (this.options.onTransferStatus) {
        this.options.onTransferStatus(chunk.transferId, TS.TRANSFERRING, 0)
      }
    }

    const currentTransfer = connection.incomingTransfers.get(chunk.transferId)!
    
    if (!verifyChunk(chunk)) {
      console.warn(`分片 ${chunk.chunkIndex} 校验和验证失败，请求重传`)
      currentTransfer.failedChunks.add(chunk.chunkIndex)
      
      this.sendProtocolMessage(connection, {
        type: 'chunk_request',
        payload: {
          transferId: chunk.transferId,
          chunkIndex: chunk.chunkIndex
        }
      })
      
      if (this.options.onTransferStatus) {
        const progress = currentTransfer.receivedChunks.size / currentTransfer.totalChunks
        this.options.onTransferStatus(chunk.transferId, TS.RETRYING, progress)
      }
      return
    }

    currentTransfer.receivedChunks.set(chunk.chunkIndex, chunk)
    currentTransfer.failedChunks.delete(chunk.chunkIndex)
    currentTransfer.lastActivity = Date.now()

    const ack: ChunkAck = {
      transferId: chunk.transferId,
      chunkIndex: chunk.chunkIndex,
      success: true,
      receivedChecksum: chunk.checksum
    }
    
    this.sendProtocolMessage(connection, {
      type: 'chunk_ack',
      payload: ack
    })

    const progress = currentTransfer.receivedChunks.size / currentTransfer.totalChunks
    
    if (this.options.onTransferStatus) {
      this.options.onTransferStatus(chunk.transferId, TS.TRANSFERRING, progress)
    }

    if (currentTransfer.receivedChunks.size === currentTransfer.totalChunks) {
      this.completeIncomingTransfer(connection, currentTransfer)
    }
  }

  private handleChunkAck(connection: PeerConnection, ack: ChunkAck): void {
    const transfer = connection.outgoingTransfers.get(ack.transferId)
    if (!transfer) return

    transfer.lastActivity = Date.now()
    
    const pendingKey = `${ack.transferId}-${ack.chunkIndex}`
    connection.pendingChunks.delete(pendingKey)

    if (this.options.onTransferStatus) {
      const progress = (transfer.totalChunks - connection.pendingChunks.size) / transfer.totalChunks
      this.options.onTransferStatus(ack.transferId, TS.TRANSFERRING, progress)
    }

    if (connection.pendingChunks.size === 0) {
      transfer.status = TS.COMPLETED
      
      this.sendProtocolMessage(connection, {
        type: 'transfer_complete',
        payload: {
          transferId: ack.transferId,
          totalChunks: transfer.totalChunks
        }
      })

      if (this.options.onTransferStatus) {
        this.options.onTransferStatus(ack.transferId, TS.COMPLETED, 1)
      }

      setTimeout(() => {
        connection.outgoingTransfers.delete(ack.transferId)
      }, 5000)
    }
  }

  private handleChunkRequest(connection: PeerConnection, payload: { transferId: string; chunkIndex: number }): void {
    const { transferId, chunkIndex } = payload
    const transfer = connection.outgoingTransfers.get(transferId)
    
    if (!transfer) {
      console.warn(`收到未知传输的分片请求: ${transferId}`)
      return
    }

    const pendingKey = `${transferId}-${chunkIndex}`
    const pending = connection.pendingChunks.get(pendingKey)
    
    if (!pending) {
      console.warn(`找不到请求的分片: ${transferId}-${chunkIndex}`)
      return
    }

    if (pending.retryCount >= this.options.maxRetryAttempts) {
      console.error(`分片 ${chunkIndex} 重传次数超过限制`)
      
      this.sendProtocolMessage(connection, {
        type: 'transfer_error',
        payload: {
          transferId,
          chunkIndex,
          error: 'max_retry_exceeded'
        }
      })
      
      transfer.status = TS.FAILED
      connection.outgoingTransfers.delete(transferId)
      connection.pendingChunks.delete(pendingKey)
      
      if (this.options.onTransferStatus) {
        this.options.onTransferStatus(transferId, TS.FAILED, 0)
      }
      return
    }

    pending.retryCount++
    transfer.retryCount = Math.max(transfer.retryCount, pending.retryCount)
    
    const chunkData = JSON.parse(pending.data) as ChunkData
    chunkData.timestamp = Date.now()
    
    setTimeout(() => {
      this.sendProtocolMessage(connection, {
        type: 'chunk',
        payload: chunkData
      })
    }, Math.min(1000 * Math.pow(2, pending.retryCount - 1), DEFAULT_MAX_RETRY_DELAY))

    if (this.options.onTransferStatus) {
      const progress = (transfer.totalChunks - connection.pendingChunks.size) / transfer.totalChunks
      this.options.onTransferStatus(transferId, TS.RETRYING, progress)
    }
  }

  private handleTransferComplete(connection: PeerConnection, payload: { transferId: string; totalChunks: number }): void {
    const transfer = connection.incomingTransfers.get(payload.transferId)
    if (transfer) {
      transfer.status = TS.COMPLETED
      if (this.options.onTransferStatus) {
        this.options.onTransferStatus(payload.transferId, TS.COMPLETED, 1)
      }
      setTimeout(() => {
        connection.incomingTransfers.delete(payload.transferId)
      }, 5000)
    }
  }

  private handleTransferError(connection: PeerConnection, payload: { transferId: string; error: string }): void {
    const transfer = connection.incomingTransfers.get(payload.transferId)
    if (transfer) {
      transfer.status = TS.FAILED
      connection.incomingTransfers.delete(payload.transferId)
      
      if (this.options.onTransferStatus) {
        this.options.onTransferStatus(payload.transferId, TS.FAILED, 0)
      }
      
      console.error(`传输失败: ${payload.transferId}, 错误: ${payload.error}`)
    }
  }

  private async completeIncomingTransfer(connection: PeerConnection, transfer: TransferSession): Promise<void> {
    try {
      transfer.status = TS.VERIFYING
      
      if (this.options.onTransferStatus) {
        this.options.onTransferStatus(transfer.id, TS.VERIFYING, 0.95)
      }

      const chunks = Array.from(transfer.receivedChunks.values())
      const assembledData = assembleChunks(chunks)
      
      const encrypted: EncryptedData = JSON.parse(assembledData)
      const content = decryptClipboardContent(encrypted, this.options.encryptionKey)
      
      if (!verifyContentChecksums(content)) {
        throw new Error('内容校验和验证失败')
      }

      transfer.status = TS.COMPLETED
      
      this.sendProtocolMessage(connection, {
        type: 'transfer_complete',
        payload: {
          transferId: transfer.id,
          totalChunks: transfer.totalChunks
        }
      })

      if (this.options.onTransferStatus) {
        this.options.onTransferStatus(transfer.id, TS.COMPLETED, 1)
      }

      this.options.onMessage(content)

    } catch (e) {
      console.error('完成传入传输失败:', e)
      transfer.status = TS.FAILED
      
      this.sendProtocolMessage(connection, {
        type: 'transfer_error',
        payload: {
          transferId: transfer.id,
          error: (e as Error).message
        }
      })

      if (this.options.onTransferStatus) {
        this.options.onTransferStatus(transfer.id, TS.FAILED, 0)
      }
    } finally {
      setTimeout(() => {
        connection.incomingTransfers.delete(transfer.id)
      }, 5000)
    }
  }

  private handleDirectMessage(connection: PeerConnection, dataStr: string): void {
    try {
      const encrypted: EncryptedData = JSON.parse(dataStr)
      const content = decryptClipboardContent(encrypted, this.options.encryptionKey)
      
      if (!verifyContentChecksums(content)) {
        console.warn('直接消息内容校验和验证失败，数据可能已损坏')
        return
      }
      
      this.options.onMessage(content)
    } catch (e) {
      console.error('处理直接消息失败:', e)
    }
  }

  private sendProtocolMessage(connection: PeerConnection, message: ProtocolMessage): void {
    const dataStr = JSON.stringify(message)
    connection.peer.send(dataStr)
  }

  private getLocalIPs(): string[] {
    const ifaces = os.networkInterfaces()
    const ips: string[] = []
    
    for (const name of Object.keys(ifaces)) {
      for (const iface of ifaces[name]!) {
        if (iface.family === 'IPv4' && !iface.internal) {
          ips.push(iface.address)
        }
      }
    }
    
    return ips
  }

  private checkIsLocalConnection(peerIPs: string[]): boolean {
    if (!peerIPs || peerIPs.length === 0) return false
    
    const localIPs = this.getLocalIPs()
    
    for (const localIP of localIPs) {
      const localSubnet = this.getSubnet(localIP)
      for (const peerIP of peerIPs) {
        if (this.getSubnet(peerIP) === localSubnet) {
          return true
        }
        if (isPrivateIP(peerIP)) {
          return true
        }
      }
    }
    
    return false
  }

  private getSubnet(ip: string): string {
    const parts = ip.split('.')
    return parts.slice(0, 3).join('.')
  }

  broadcast(content: ClipboardContent): void {
    const encrypted = encryptClipboardContent(content, this.options.encryptionKey)
    const dataStr = JSON.stringify(encrypted)
    
    const sortedPeers = Array.from(this.peers.values())
      .filter(p => p.isConnected)
      .sort((a, b) => {
        const priority = { [CM.LAN]: 2, [CM.DIRECT]: 1, [CM.RELAY]: 0 }
        return priority[b.connectionMode] - priority[a.connectionMode]
      })
    
    for (const connection of sortedPeers) {
      try {
        this.sendToPeerWithRetry(connection, dataStr, content.id)
      } catch (e) {
        console.error(`发送数据到 ${connection.deviceName} 失败:`, e)
      }
    }
  }

  sendTo(peerId: string, content: ClipboardContent): boolean {
    const connection = this.peers.get(peerId)
    if (!connection || !connection.isConnected) return false
    
    try {
      const encrypted = encryptClipboardContent(content, this.options.encryptionKey)
      const dataStr = JSON.stringify(encrypted)
      this.sendToPeerWithRetry(connection, dataStr, content.id)
      return true
    } catch (e) {
      console.error(`发送数据到 ${peerId} 失败:`, e)
      return false
    }
  }

  private sendToPeerWithRetry(connection: PeerConnection, data: string, contentId: string): void {
    if (data.length <= DEFAULT_CHUNK_SIZE) {
      connection.peer.send(data)
      return
    }

    const transferId = `${contentId}-${Date.now()}`
    const chunks = createChunks(data, contentId, DEFAULT_CHUNK_SIZE)
    
    const transfer: TransferSession = {
      id: transferId,
      contentId,
      peerId: connection.peerId,
      status: TS.PENDING,
      totalChunks: chunks.length,
      receivedChunks: new Map(),
      failedChunks: new Set(),
      retryCount: 0,
      startTime: Date.now(),
      lastActivity: Date.now()
    }
    
    connection.outgoingTransfers.set(transferId, transfer)
    
    if (this.options.onTransferStatus) {
      this.options.onTransferStatus(transferId, TS.PENDING, 0)
    }

    transfer.status = TS.TRANSFERRING
    
    for (const chunk of chunks) {
      const pendingKey = `${transferId}-${chunk.chunkIndex}`
      connection.pendingChunks.set(pendingKey, {
        data: JSON.stringify(chunk),
        retryCount: 0
      })
      
      this.sendProtocolMessage(connection, {
        type: 'chunk',
        payload: chunk
      })
    }

    if (this.options.onTransferStatus) {
      this.options.onTransferStatus(transferId, TS.TRANSFERRING, 0)
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  getConnectedCount(): number {
    return Array.from(this.peers.values()).filter(p => p.isConnected).length
  }

  getDevices(): Device[] {
    return [...this.devices]
  }

  getConnectionMode(peerId: string): ConnectionMode | undefined {
    return this.peers.get(peerId)?.connectionMode
  }

  getTransferStatus(transferId: string): TransferStatus | undefined {
    for (const conn of this.peers.values()) {
      const outgoing = conn.outgoingTransfers.get(transferId)
      if (outgoing) return outgoing.status
      
      const incoming = conn.incomingTransfers.get(transferId)
      if (incoming) return incoming.status
    }
    return undefined
  }

  on(event: string, listener: (...args: any[]) => void): void {
    this.eventEmitter.on(event, listener)
  }

  off(event: string, listener: (...args: any[]) => void): void {
    this.eventEmitter.off(event, listener)
  }

  updateSettings(settings: Partial<AppSettings>): void {
    if (settings.encryptionKey) {
      this.options.encryptionKey = settings.encryptionKey
    }
    if (settings.deviceName) {
      this.options.deviceName = settings.deviceName
    }
    if (settings.lanOnly !== undefined) {
      this.options.lanOnly = settings.lanOnly
      if (settings.lanOnly) {
        for (const [peerId, conn] of this.peers) {
          if (!conn.isLocal) {
            conn.peer.destroy()
            this.peers.delete(peerId)
          }
        }
      }
    }
    if (settings.useRelayOnFailure !== undefined) {
      this.options.useRelayOnFailure = settings.useRelayOnFailure
    }
    if (settings.maxRetryAttempts !== undefined) {
      this.options.maxRetryAttempts = settings.maxRetryAttempts
    }
    if (settings.turnServers !== undefined) {
      this.options.turnServers = settings.turnServers
    }
    if (settings.signalingServer && settings.signalingServer !== this.options.signalingServer) {
      this.options.signalingServer = settings.signalingServer
      if (this.isConnected()) {
        this.disconnect()
        this.connect().catch(e => console.error('重连失败:', e))
      }
    }
  }
}

import { EventEmitter } from 'events'
import type { 
  TransferSpeedStats, 
  NetworkStats, 
  DashboardData,
  TransferStatus,
  ConnectionMode
} from '@shared/types'
import { 
  createTransferStats, 
  updateTransferStats, 
  createNetworkStats,
  formatSpeed,
  formatLatency
} from '@shared/utils'

export class TransferStatsManager {
  private activeTransfers: Map<string, TransferSpeedStats> = new Map()
  private transferHistory: TransferSpeedStats[] = []
  private networkStats: NetworkStats
  private eventEmitter: EventEmitter = new EventEmitter()
  private maxHistorySize: number = 100
  private totalUploaded: number = 0
  private totalDownloaded: number = 0
  private lastUpdateTime: number = Date.now()
  private lastUploadedBytes: number = 0
  private lastDownloadedBytes: number = 0

  constructor() {
    this.networkStats = createNetworkStats()
  }

  startTransfer(
    transferId: string,
    peerId: string,
    peerName: string,
    totalBytes: number,
    connectionMode: ConnectionMode,
    direction: 'upload' | 'download'
  ): TransferSpeedStats {
    const stats = createTransferStats(
      transferId,
      peerId,
      peerName,
      totalBytes,
      connectionMode
    )
    stats.status = 'transferring' as TransferStatus
    
    this.activeTransfers.set(transferId, stats)
    
    this.eventEmitter.emit('transfer:start', stats)
    this.updateNetworkStats()
    
    return stats
  }

  updateTransferProgress(
    transferId: string,
    bytesTransferred: number,
    latency: number
  ): void {
    const stats = this.activeTransfers.get(transferId)
    if (!stats) return

    const updated = updateTransferStats(stats, bytesTransferred, latency)
    this.activeTransfers.set(transferId, updated)

    const previousTransferred = stats.transferredBytes
    const delta = updated.transferredBytes - previousTransferred
    
    if (delta > 0) {
      if (updated.peerId === updated.peerId) {
        this.totalUploaded += delta
      }
    }

    this.eventEmitter.emit('transfer:progress', updated)
    this.updateNetworkStats()
  }

  completeTransfer(transferId: string): void {
    const stats = this.activeTransfers.get(transferId)
    if (!stats) return

    stats.status = 'completed' as TransferStatus
    stats.endTime = Date.now()

    this.transferHistory.push({ ...stats })
    if (this.transferHistory.length > this.maxHistorySize) {
      this.transferHistory.shift()
    }

    this.activeTransfers.delete(transferId)
    
    this.eventEmitter.emit('transfer:complete', stats)
    this.updateNetworkStats()
  }

  failTransfer(transferId: string): void {
    const stats = this.activeTransfers.get(transferId)
    if (!stats) return

    stats.status = 'failed' as TransferStatus
    stats.endTime = Date.now()

    this.transferHistory.push({ ...stats })
    if (this.transferHistory.length > this.maxHistorySize) {
      this.transferHistory.shift()
    }

    this.activeTransfers.delete(transferId)
    
    this.eventEmitter.emit('transfer:failed', stats)
    this.updateNetworkStats()
  }

  recordChunkFailure(transferId: string): void {
    const stats = this.activeTransfers.get(transferId)
    if (stats) {
      stats.failedChunks++
    }
  }

  recordChunkRetry(transferId: string): void {
    const stats = this.activeTransfers.get(transferId)
    if (stats) {
      stats.retriedChunks++
    }
  }

  getTransferStats(transferId: string): TransferSpeedStats | undefined {
    return this.activeTransfers.get(transferId)
  }

  getActiveTransfers(): TransferSpeedStats[] {
    return Array.from(this.activeTransfers.values())
  }

  getTransferHistory(): TransferSpeedStats[] {
    return [...this.transferHistory]
  }

  getNetworkStats(): NetworkStats {
    return { ...this.networkStats }
  }

  getDashboardData(): DashboardData {
    return {
      currentTransfers: this.getActiveTransfers(),
      networkStats: this.getNetworkStats(),
      transferHistory: this.getTransferHistory()
    }
  }

  getFormattedStats(): {
    currentSpeed: string
    peakSpeed: string
    averageSpeed: string
    totalTransferred: string
    activeTransfers: number
  } {
    const transfers = this.getActiveTransfers()
    let currentSpeed = 0
    let peakSpeed = 0
    let totalBytes = 0

    for (const transfer of transfers) {
      currentSpeed += transfer.currentSpeed
      peakSpeed = Math.max(peakSpeed, transfer.peakSpeed)
      totalBytes += transfer.transferredBytes
    }

    return {
      currentSpeed: formatSpeed(currentSpeed),
      peakSpeed: formatSpeed(peakSpeed),
      averageSpeed: formatSpeed(currentSpeed / Math.max(transfers.length, 1)),
      totalTransferred: this.formatBytes(totalBytes),
      activeTransfers: transfers.length
    }
  }

  on(event: string, callback: (...args: any[]) => void): void {
    this.eventEmitter.on(event, callback)
  }

  off(event: string, callback: (...args: any[]) => void): void {
    this.eventEmitter.off(event, callback)
  }

  private updateNetworkStats(): void {
    const now = Date.now()
    const elapsed = (now - this.lastUpdateTime) / 1000

    if (elapsed > 0) {
      const uploadDelta = this.totalUploaded - this.lastUploadedBytes
      const downloadDelta = this.totalDownloaded - this.lastDownloadedBytes

      this.networkStats = {
        timestamp: now,
        uploadSpeed: uploadDelta / elapsed,
        downloadSpeed: downloadDelta / elapsed,
        totalUploaded: this.totalUploaded,
        totalDownloaded: this.totalDownloaded,
        activeTransfers: this.activeTransfers.size,
        connectedPeers: this.networkStats.connectedPeers,
        averageLatency: this.calculateAverageLatency()
      }

      this.lastUpdateTime = now
      this.lastUploadedBytes = this.totalUploaded
      this.lastDownloadedBytes = this.totalDownloaded
    }
  }

  private calculateAverageLatency(): number {
    const transfers = this.getActiveTransfers()
    if (transfers.length === 0) return 0
    
    const totalLatency = transfers.reduce((sum, t) => sum + t.latency, 0)
    return totalLatency / transfers.length
  }

  private formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB']
    const unitIndex = Math.floor(Math.log(bytes) / Math.log(1024))
    const value = bytes / Math.pow(1024, unitIndex)
    return `${value.toFixed(2)} ${units[Math.min(unitIndex, units.length - 1)]}`
  }

  updateConnectedPeers(count: number): void {
    this.networkStats.connectedPeers = count
    this.eventEmitter.emit('network:update', this.networkStats)
  }

  recordDownload(bytes: number): void {
    this.totalDownloaded += bytes
    this.updateNetworkStats()
  }

  recordUpload(bytes: number): void {
    this.totalUploaded += bytes
    this.updateNetworkStats()
  }

  reset(): void {
    this.activeTransfers.clear()
    this.transferHistory = []
    this.networkStats = createNetworkStats()
    this.totalUploaded = 0
    this.totalDownloaded = 0
    this.lastUpdateTime = Date.now()
    this.lastUploadedBytes = 0
    this.lastDownloadedBytes = 0
  }

  destroy(): void {
    this.activeTransfers.clear()
    this.transferHistory = []
    this.eventEmitter.removeAllListeners()
  }
}

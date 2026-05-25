import { EventEmitter } from 'events'
import type { 
  PairingSession, 
  PairedDevice, 
  PairingStatus 
} from '@shared/types'
import { PairingStatus as PS } from '@shared/types'
import { 
  createPairingSession, 
  generateId, 
  generateVerificationCode,
  generateQRCodeData,
  parseQRCodeData,
  validatePairingCode,
  isPairingExpired
} from '@shared/utils'

interface DevicePairingManagerOptions {
  deviceId: string
  deviceName: string
  onPairingComplete?: (pairedDevice: PairedDevice) => void
  onPairingFailed?: (sessionId: string, reason: string) => void
}

export class DevicePairingManager {
  private options: DevicePairingManagerOptions
  private sessions: Map<string, PairingSession> = new Map()
  private pairedDevices: Map<string, PairedDevice> = new Map()
  private eventEmitter: EventEmitter = new EventEmitter()
  private cleanupTimer: NodeJS.Timeout | null = null

  constructor(options: DevicePairingManagerOptions) {
    this.options = options
    this.startCleanup()
  }

  createPairingSession(): PairingSession {
    const session = createPairingSession(
      this.options.deviceId,
      this.options.deviceName
    )
    this.sessions.set(session.sessionId, session)
    
    this.eventEmitter.emit('session:created', session)
    
    return session
  }

  getPairingSession(sessionId: string): PairingSession | undefined {
    return this.sessions.get(sessionId)
  }

  verifyPairingCode(sessionId: string, code: string): boolean {
    const session = this.sessions.get(sessionId)
    if (!session) {
      return false
    }

    if (isPairingExpired(session)) {
      session.status = PS.EXPIRED
      this.eventEmitter.emit('session:expired', sessionId)
      this.sessions.delete(sessionId)
      return false
    }

    if (validatePairingCode(session, code)) {
      session.status = PS.PAIRED
      this.eventEmitter.emit('session:verified', session)
      return true
    }

    session.status = PS.FAILED
    this.eventEmitter.emit('session:failed', sessionId, '验证码错误')
    return false
  }

  completePairing(
    sessionId: string, 
    remoteDeviceId: string, 
    remoteDeviceName: string,
    remoteDeviceType: string = 'desktop'
  ): PairedDevice {
    const pairedDevice: PairedDevice = {
      deviceId: remoteDeviceId,
      deviceName: remoteDeviceName,
      deviceType: remoteDeviceType,
      pairedAt: Date.now(),
      lastConnected: Date.now(),
      isTrusted: true
    }

    this.pairedDevices.set(remoteDeviceId, pairedDevice)

    const session = this.sessions.get(sessionId)
    if (session) {
      session.status = PS.PAIRED
      session.pairedDeviceId = remoteDeviceId
      session.pairedDeviceName = remoteDeviceName
    }

    this.eventEmitter.emit('pairing:complete', pairedDevice)
    
    if (this.options.onPairingComplete) {
      this.options.onPairingComplete(pairedDevice)
    }

    return pairedDevice
  }

  removePairedDevice(deviceId: string): boolean {
    const removed = this.pairedDevices.delete(deviceId)
    if (removed) {
      this.eventEmitter.emit('device:removed', deviceId)
    }
    return removed
  }

  getPairedDevices(): PairedDevice[] {
    return Array.from(this.pairedDevices.values())
  }

  isDevicePaired(deviceId: string): boolean {
    return this.pairedDevices.has(deviceId)
  }

  isTrustedDevice(deviceId: string): boolean {
    const device = this.pairedDevices.get(deviceId)
    return device?.isTrusted ?? false
  }

  updateDeviceLastConnected(deviceId: string): void {
    const device = this.pairedDevices.get(deviceId)
    if (device) {
      device.lastConnected = Date.now()
    }
  }

  parseQRCode(qrData: string): {
    deviceId: string
    deviceName: string
    verificationCode: string
  } | null {
    return parseQRCodeData(qrData)
  }

  cancelPairingSession(sessionId: string): void {
    this.sessions.delete(sessionId)
    this.eventEmitter.emit('session:cancelled', sessionId)
  }

  on(event: string, callback: (...args: any[]) => void): void {
    this.eventEmitter.on(event, callback)
  }

  off(event: string, callback: (...args: any[]) => void): void {
    this.eventEmitter.off(event, callback)
  }

  private startCleanup(): void {
    this.cleanupTimer = setInterval(() => {
      const now = Date.now()
      for (const [id, session] of this.sessions) {
        if (now > session.expiresAt && session.status !== PS.PAIRED) {
          this.sessions.delete(id)
          this.eventEmitter.emit('session:expired', id)
        }
      }
    }, 60000)
  }

  destroy(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer)
    }
    this.sessions.clear()
    this.eventEmitter.removeAllListeners()
  }
}

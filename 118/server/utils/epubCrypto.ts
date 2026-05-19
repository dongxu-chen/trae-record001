import AdmZip from 'adm-zip'
import forge from 'node-forge'
import fs from 'fs'
import path from 'path'

export interface EncryptionInfo {
  isEncrypted: boolean
  method: 'none' | 'password' | 'adobe' | 'unknown'
  encryptionData?: any
}

export class EPubDecryptor {
  private zip: AdmZip
  private encryptionMethod: string = 'none'
  private key: Buffer | null = null

  constructor(private filePath: string) {
    this.zip = new AdmZip(filePath)
  }

  async detectEncryption(): Promise<EncryptionInfo> {
    const encryptionEntries = this.zip.getEntries().filter(entry => 
      entry.entryName.includes('encryption.xml') || 
      entry.entryName.includes('META-INF/encryption.xml')
    )

    if (encryptionEntries.length === 0) {
      return { isEncrypted: false, method: 'none' }
    }

    const encryptionXml = encryptionEntries[0].getData().toString('utf-8')
    
    if (encryptionXml.includes('http://ns.adobe.com/pdf/encryption')) {
      return { isEncrypted: true, method: 'adobe', encryptionData: encryptionXml }
    }
    
    if (encryptionXml.includes('http://www.w3.org/2001/04/xmlenc')) {
      return { isEncrypted: true, method: 'password', encryptionData: encryptionXml }
    }

    return { isEncrypted: true, method: 'unknown', encryptionData: encryptionXml }
  }

  async decryptWithPassword(password: string): Promise<boolean> {
    try {
      const passwordKey = this.deriveKeyFromPassword(password)
      this.key = passwordKey
      
      const encryptedEntries = this.getEncryptedEntries()
      
      for (const entry of encryptedEntries) {
        try {
          const decryptedData = this.decryptData(entry.getData(), this.key)
          entry.setData(decryptedData)
        } catch (e) {
          console.error(`Failed to decrypt ${entry.entryName}:`, e)
        }
      }
      
      return true
    } catch (error) {
      console.error('Decryption failed:', error)
      return false
    }
  }

  private deriveKeyFromPassword(password: string): Buffer {
    const md = forge.md.sha256.create()
    md.update(password)
    const key = md.digest().getBytes(16)
    return Buffer.from(key, 'binary')
  }

  private getEncryptedEntries(): AdmZip.IZipEntry[] {
    return this.zip.getEntries().filter(entry => 
      !entry.entryName.startsWith('META-INF/') &&
      !entry.isDirectory
    )
  }

  private decryptData(data: Buffer, key: Buffer): Buffer {
    try {
      const iv = data.slice(0, 16)
      const encrypted = data.slice(16)
      
      const decipher = forge.cipher.createDecipher('AES-CBC', key.toString('binary'))
      decipher.start({ iv: iv.toString('binary') })
      decipher.update(forge.util.createBuffer(encrypted.toString('binary')))
      decipher.finish()
      
      return Buffer.from(decipher.output.getBytes(), 'binary')
    } catch {
      return data
    }
  }

  async saveDecrypted(outputPath: string): Promise<void> {
    this.zip.writeZip(outputPath)
  }

  extractToTemp(): string {
    const tempDir = path.join(process.cwd(), 'uploads', 'temp', Date.now().toString())
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true })
    }
    this.zip.extractAllTo(tempDir, true)
    return tempDir
  }
}

export async function checkEPubEncryption(filePath: string): Promise<EncryptionInfo> {
  const decryptor = new EPubDecryptor(filePath)
  return await decryptor.detectEncryption()
}

import { v4 as uuidv4 } from 'uuid'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const UPLOAD_DIR = path.join(__dirname, '..', '..', 'uploads')

if (!fs.existsSync(UPLOAD_DIR)) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true })
}

export interface ColumnMeta {
  name: string
  type: 'string' | 'number' | 'boolean' | 'date'
  uniqueValues?: number
}

export interface UploadedFileMeta {
  fileId: string
  fileName: string
  format: 'csv' | 'json' | 'parquet'
  totalRows: number
  columns: ColumnMeta[]
  fileSize: number
  filePath: string
  uploadedAt: string
}

const fileStore = new Map<string, UploadedFileMeta>()

export function getUploadDir(): string {
  return UPLOAD_DIR
}

export function getStoredFile(fileId: string): UploadedFileMeta | undefined {
  return fileStore.get(fileId)
}

export function registerFile(meta: Omit<UploadedFileMeta, 'fileId' | 'uploadedAt'>): UploadedFileMeta {
  const fileId = uuidv4()
  const fullMeta: UploadedFileMeta = {
    ...meta,
    fileId,
    uploadedAt: new Date().toISOString(),
  }
  fileStore.set(fileId, fullMeta)
  return fullMeta
}

export function detectFormat(fileName: string): 'csv' | 'json' | 'parquet' {
  const ext = path.extname(fileName).toLowerCase()
  if (ext === '.csv') return 'csv'
  if (ext === '.json' || ext === '.jsonl') return 'json'
  if (ext === '.parquet') return 'parquet'
  return 'csv'
}

export function inferColumnType(values: unknown[]): ColumnMeta['type'] {
  const sample = values.slice(0, 100)
  let numCount = 0
  let boolCount = 0
  let dateCount = 0

  for (const v of sample) {
    if (v === null || v === undefined || v === '') continue
    if (typeof v === 'boolean' || v === 'true' || v === 'false') {
      boolCount++
    } else if (typeof v === 'number' || (typeof v === 'string' && !isNaN(Number(v)) && v.trim() !== '')) {
      numCount++
    } else if (typeof v === 'string') {
      const parsed = Date.parse(v)
      if (!isNaN(parsed) && v.length > 4) {
        dateCount++
      }
    }
  }

  const total = sample.filter(v => v !== null && v !== undefined && v !== '').length
  if (total === 0) return 'string'
  if (boolCount / total > 0.7) return 'boolean'
  if (numCount / total > 0.7) return 'number'
  if (dateCount / total > 0.5) return 'date'
  return 'string'
}

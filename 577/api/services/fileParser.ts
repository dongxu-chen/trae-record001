import fs from 'fs'
import Papa from 'papaparse'
import { getStoredFile, registerFile, getUploadDir, inferColumnType, type ColumnMeta, type UploadedFileMeta } from './fileStore.js'

export function parseCSV(filePath: string): { data: Record<string, unknown>[]; columns: ColumnMeta[] } {
  const content = fs.readFileSync(filePath, 'utf-8')
  const result = Papa.parse<Record<string, string>>(content, {
    header: true,
    skipEmptyLines: true,
    dynamicTyping: false,
  })

  const data = result.data
  const columns: ColumnMeta[] = result.meta.fields
    ? result.meta.fields.map(field => {
        const colValues = data.map(row => row[field])
        return {
          name: field,
          type: inferColumnType(colValues),
        }
      })
    : []

  return { data, columns }
}

export function parseJSON(filePath: string): { data: Record<string, unknown>[]; columns: ColumnMeta[] } {
  const content = fs.readFileSync(filePath, 'utf-8')
  let parsed: unknown

  try {
    parsed = JSON.parse(content)
  } catch {
    const lines = content.trim().split('\n')
    parsed = lines.map(line => {
      try {
        return JSON.parse(line)
      } catch {
        return null
      }
    }).filter(Boolean)
  }

  let data: Record<string, unknown>[]
  if (Array.isArray(parsed)) {
    data = parsed
  } else if (typeof parsed === 'object' && parsed !== null) {
    const arrayKey = Object.keys(parsed).find(k => Array.isArray((parsed as Record<string, unknown>)[k]))
    data = arrayKey ? (parsed as Record<string, unknown[]>)[arrayKey] as Record<string, unknown>[] : [parsed as Record<string, unknown>]
  } else {
    data = []
  }

  const allKeys = new Set<string>()
  data.forEach(row => {
    if (typeof row === 'object' && row !== null) {
      Object.keys(row).forEach(k => allKeys.add(k))
    }
  })

  const columns: ColumnMeta[] = Array.from(allKeys).map(field => ({
    name: field,
    type: inferColumnType(data.map(row => (row as Record<string, unknown>)[field])),
  }))

  return { data, columns }
}

export async function parseParquet(filePath: string): Promise<{ data: Record<string, unknown>[]; columns: ColumnMeta[] }> {
  const parquetjs = await import('parquetjs')
  const reader = await parquetjs.ParquetReader.openFile(filePath)
  const cursor = reader.getCursor()
  const data: Record<string, unknown>[] = []
  let record: Record<string, unknown> | null = null

  while ((record = await cursor.read() as Record<string, unknown> | null) !== null) {
    data.push(record)
  }

  await reader.close()

  const schema = reader.metadata.schema
  const columns: ColumnMeta[] = schema.fields
    ? schema.fields.map((f: { name: string }) => ({
        name: f.name,
        type: inferColumnType(data.map(row => row[f.name])),
      }))
    : data.length > 0
      ? Object.keys(data[0]).map(k => ({
          name: k,
          type: inferColumnType(data.map(row => row[k])),
        }))
      : []

  return { data, columns }
}

export async function processUploadedFile(filePath: string, fileName: string, fileSize: number): Promise<UploadedFileMeta> {
  const format = fileName.toLowerCase().endsWith('.csv') ? 'csv' as const
    : (fileName.toLowerCase().endsWith('.json') || fileName.toLowerCase().endsWith('.jsonl')) ? 'json' as const
    : 'parquet' as const

  let data: Record<string, unknown>[]
  let columns: ColumnMeta[]

  switch (format) {
    case 'csv': {
      const result = parseCSV(filePath)
      data = result.data
      columns = result.columns
      break
    }
    case 'json': {
      const result = parseJSON(filePath)
      data = result.data
      columns = result.columns
      break
    }
    case 'parquet': {
      const result = await parseParquet(filePath)
      data = result.data
      columns = result.columns
      break
    }
  }

  const meta = registerFile({
    fileName,
    format,
    totalRows: data.length,
    columns,
    fileSize,
    filePath,
  })

  const cachePath = filePath + '.cache.json'
  fs.writeFileSync(cachePath, JSON.stringify(data))

  return meta
}

export function readChunk(fileId: string, offset: number, limit: number): { data: Record<string, unknown>[]; totalRows: number } {
  const meta = getStoredFile(fileId)
  if (!meta) throw new Error('File not found')

  const cachePath = meta.filePath + '.cache.json'
  if (!fs.existsSync(cachePath)) throw new Error('Cache file not found')

  const content = fs.readFileSync(cachePath, 'utf-8')
  const allData: Record<string, unknown>[] = JSON.parse(content)

  return {
    data: allData.slice(offset, offset + limit),
    totalRows: allData.length,
  }
}

export function getColumnStats(fileId: string, columnName: string): { column: string; uniqueValues: number; distribution: Array<{ value: string; count: number }> } {
  const meta = getStoredFile(fileId)
  if (!meta) throw new Error('File not found')

  const cachePath = meta.filePath + '.cache.json'
  if (!fs.existsSync(cachePath)) throw new Error('Cache file not found')

  const content = fs.readFileSync(cachePath, 'utf-8')
  const allData: Record<string, unknown>[] = JSON.parse(content)

  const distribution = new Map<string, number>()
  for (const row of allData) {
    const val = String(row[columnName] ?? 'null')
    distribution.set(val, (distribution.get(val) ?? 0) + 1)
  }

  return {
    column: columnName,
    uniqueValues: distribution.size,
    distribution: Array.from(distribution.entries())
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 50),
  }
}

export function buildStratifyIndex(fileId: string, columnName: string): Record<string, number[]> {
  const meta = getStoredFile(fileId)
  if (!meta) throw new Error('File not found')

  const stratifyCachePath = meta.filePath + `.stratify-${columnName}.json`
  if (fs.existsSync(stratifyCachePath)) {
    return JSON.parse(fs.readFileSync(stratifyCachePath, 'utf-8'))
  }

  const cachePath = meta.filePath + '.cache.json'
  if (!fs.existsSync(cachePath)) throw new Error('Cache file not found')

  const content = fs.readFileSync(cachePath, 'utf-8')
  const allData: Record<string, unknown>[] = JSON.parse(content)

  const groups: Record<string, number[]> = {}
  for (let i = 0; i < allData.length; i++) {
    const key = String(allData[i][columnName] ?? '__null__')
    if (!groups[key]) groups[key] = []
    groups[key].push(i)
  }

  fs.writeFileSync(stratifyCachePath, JSON.stringify(groups))
  return groups
}

export function exportSample(fileId: string, sampleIndices: number[], format: 'csv' | 'json'): string {
  const meta = getStoredFile(fileId)
  if (!meta) throw new Error('File not found')

  const cachePath = meta.filePath + '.cache.json'
  if (!fs.existsSync(cachePath)) throw new Error('Cache file not found')

  const content = fs.readFileSync(cachePath, 'utf-8')
  const allData: Record<string, unknown>[] = JSON.parse(content)

  const sampleData = sampleIndices
    .filter(i => i >= 0 && i < allData.length)
    .map(i => allData[i])

  if (format === 'json') {
    return JSON.stringify(sampleData, null, 2)
  }

  if (sampleData.length === 0) return ''

  const headers = Object.keys(sampleData[0])
  const csvRows = [headers.join(',')]
  for (const row of sampleData) {
    const values = headers.map(h => {
      const v = row[h]
      const s = String(v ?? '')
      return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s
    })
    csvRows.push(values.join(','))
  }

  return csvRows.join('\n')
}

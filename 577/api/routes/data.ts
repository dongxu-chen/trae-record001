import { Router, type Request, type Response } from 'express'
import multer from 'multer'
import path from 'path'
import fs from 'fs'
import { getUploadDir, getStoredFile } from '../services/fileStore.js'
import { processUploadedFile, readChunk, getColumnStats, buildStratifyIndex, exportSample } from '../services/fileParser.js'

const router = Router()

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, getUploadDir())
  },
  filename: (_req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1e9)
    cb(null, uniqueSuffix + path.extname(file.originalname))
  },
})

const upload = multer({
  storage,
  limits: { fileSize: 500 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase()
    if (['.csv', '.json', '.jsonl', '.parquet'].includes(ext)) {
      cb(null, true)
    } else {
      cb(new Error('Only CSV, JSON, and Parquet files are supported'))
    }
  },
})

router.post('/upload', upload.single('file'), async (req: Request, res: Response) => {
  try {
    if (!req.file) {
      res.status(400).json({ success: false, error: 'No file uploaded' })
      return
    }

    const meta = await processUploadedFile(
      req.file.path,
      req.file.originalname,
      req.file.size,
    )

    res.json({ success: true, data: meta })
  } catch (error) {
    console.error('Upload error:', error)
    res.status(500).json({ success: false, error: 'Failed to process file' })
  }
})

router.get('/data/:fileId/chunk', (req: Request, res: Response) => {
  try {
    const { fileId } = req.params
    const offset = parseInt(req.query.offset as string) || 0
    const limit = parseInt(req.query.limit as string) || 100

    const result = readChunk(fileId, offset, limit)
    res.json({ success: true, data: { ...result, offset, limit } })
  } catch (error) {
    console.error('Chunk read error:', error)
    res.status(500).json({ success: false, error: 'Failed to read data chunk' })
  }
})

router.get('/data/:fileId/column-stats', (req: Request, res: Response) => {
  try {
    const { fileId } = req.params
    const column = req.query.column as string

    if (!column) {
      res.status(400).json({ success: false, error: 'Column name is required' })
      return
    }

    const stats = getColumnStats(fileId, column)
    res.json({ success: true, data: stats })
  } catch (error) {
    console.error('Column stats error:', error)
    res.status(500).json({ success: false, error: 'Failed to get column stats' })
  }
})

router.get('/data/:fileId/stratify-index', (req: Request, res: Response) => {
  try {
    const { fileId } = req.params
    const column = req.query.column as string

    if (!column) {
      res.status(400).json({ success: false, error: 'Column name is required' })
      return
    }

    const groups = buildStratifyIndex(fileId, column)
    res.json({ success: true, data: { column, groups } })
  } catch (error) {
    console.error('Stratify index error:', error)
    res.status(500).json({ success: false, error: 'Failed to build stratify index' })
  }
})

router.post('/export', (req: Request, res: Response) => {
  try {
    const { fileId, sampleIndices, format } = req.body

    if (!fileId || !sampleIndices || !format) {
      res.status(400).json({ success: false, error: 'Missing required fields' })
      return
    }

    const content = exportSample(fileId, sampleIndices, format)
    const meta = getStoredFile(fileId)

    const mimeType = format === 'json' ? 'application/json' : 'text/csv'
    const ext = format === 'json' ? '.json' : '.csv'
    const fileName = meta ? `sample_${meta.fileName}${ext}` : `sample${ext}`

    res.setHeader('Content-Type', mimeType)
    res.setHeader('Content-Disposition', `attachment; filename="${fileName}"`)
    res.send(content)
  } catch (error) {
    console.error('Export error:', error)
    res.status(500).json({ success: false, error: 'Failed to export sample' })
  }
})

router.get('/data/:fileId/info', (req: Request, res: Response) => {
  try {
    const { fileId } = req.params
    const meta = getStoredFile(fileId)

    if (!meta) {
      res.status(404).json({ success: false, error: 'File not found' })
      return
    }

    res.json({
      success: true,
      data: {
        fileId: meta.fileId,
        fileName: meta.fileName,
        format: meta.format,
        totalRows: meta.totalRows,
        columns: meta.columns,
        fileSize: meta.fileSize,
        uploadedAt: meta.uploadedAt,
      },
    })
  } catch (error) {
    console.error('Info error:', error)
    res.status(500).json({ success: false, error: 'Failed to get file info' })
  }
})

export default router

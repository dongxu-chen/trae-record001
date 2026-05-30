import express, {
  type Request,
  type Response,
  type NextFunction,
} from 'express'
import cors from 'cors'
import path from 'path'
import dotenv from 'dotenv'
import { fileURLToPath } from 'url'
import multer from 'multer'
import Papa from 'papaparse'
import { createObjectCsvWriter } from 'csv-writer'
import * as XLSX from 'xlsx'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

dotenv.config()

const app: express.Application = express()

app.use(cors())
app.use(express.json({ limit: '10mb' }))
app.use(express.urlencoded({ extended: true, limit: '10mb' }))

const upload = multer({ storage: multer.memoryStorage() })

const projects: any[] = []
const annotations: any[] = []

app.get('/api/projects', (req: Request, res: Response) => {
  res.json(projects)
})

app.post('/api/projects', (req: Request, res: Response) => {
  const project = {
    ...req.body,
    id: 'proj-' + Date.now(),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
  projects.push(project)
  res.json(project)
})

app.get('/api/projects/:id', (req: Request, res: Response) => {
  const project = projects.find(p => p.id === req.params.id)
  if (!project) {
    return res.status(404).json({ error: 'Project not found' })
  }
  res.json(project)
})

app.delete('/api/projects/:id', (req: Request, res: Response) => {
  const index = projects.findIndex(p => p.id === req.params.id)
  if (index === -1) {
    return res.status(404).json({ error: 'Project not found' })
  }
  projects.splice(index, 1)
  res.status(204).send()
})

app.get('/api/projects/:id/annotations', (req: Request, res: Response) => {
  const projectAnnotations = annotations.filter(a => a.projectId === req.params.id)
  res.json(projectAnnotations)
})

app.get('/api/projects/:id/statistics', (req: Request, res: Response) => {
  const projectAnnotations = annotations.filter(a => a.projectId === req.params.id)
  const project = projects.find(p => p.id === req.params.id)
  
  const stats = {
    totalAnnotations: projectAnnotations.length,
    byType: {
      classification: projectAnnotations.filter(a => a.type === 'classification').length,
      anomaly: projectAnnotations.filter(a => a.type === 'anomaly').length,
      trend: projectAnnotations.filter(a => a.type === 'trend').length,
    },
    byUser: Array.from(
      projectAnnotations.reduce((acc, a) => {
        const existing = acc.get(a.createdBy) || { userId: a.createdBy, userName: a.createdBy, count: 0 }
        acc.set(a.createdBy, { ...existing, count: existing.count + 1 })
        return acc
      }, new Map()).values()
    ),
    recentAnnotations: projectAnnotations.slice(-10).reverse(),
    dataPointCoverage: project ? (new Set(projectAnnotations.map(a => a.dataPointIndex)).size / project.dataPoints.length * 100) : 0,
  }
  
  res.json(stats)
})

app.post('/api/projects/:id/upload', upload.single('file'), (req: Request, res: Response) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' })
  }
  
  const content = req.file.buffer.toString('utf-8')
  const result = Papa.parse(content, { header: true, skipEmptyLines: true })
  
  const dataPoints = result.data.map((row: any) => ({
    x: row.x || row.date || row.time || row[0],
    y: parseFloat(row.y || row.value || row[1]) || 0,
  }))
  
  res.json({ dataPoints })
})

app.get('/api/projects/:id/export', (req: Request, res: Response) => {
  const projectId = req.params.id
  const format = req.query.format as string || 'json'
  const projectAnnotations = annotations.filter(a => a.projectId === projectId)
  const project = projects.find(p => p.id === projectId)
  
  if (format === 'csv' || format === 'excel') {
    const data = projectAnnotations.map(a => ({
      id: a.id,
      type: a.type,
      dataPointIndex: a.dataPointIndex,
      label: a.label,
      description: a.description || '',
      createdBy: a.createdBy,
      createdAt: a.createdAt,
      dataPointX: project?.dataPoints[a.dataPointIndex]?.x || '',
      dataPointY: project?.dataPoints[a.dataPointIndex]?.y || '',
    }))
    
    if (format === 'csv') {
      const headers = Object.keys(data[0] || {})
      const csv = [
        headers.join(','),
        ...data.map(row => headers.map(h => `"${row[h as keyof typeof row] || ''}"`).join(','))
      ].join('\n')
      
      res.setHeader('Content-Type', 'text/csv')
      res.setHeader('Content-Disposition', `attachment; filename="annotations_${Date.now()}.csv"`)
      return res.send(csv)
    } else {
      const ws = XLSX.utils.json_to_sheet(data)
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, 'Annotations')
      const buffer = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' })
      
      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
      res.setHeader('Content-Disposition', `attachment; filename="annotations_${Date.now()}.xlsx"`)
      return res.send(buffer)
    }
  }
  
  res.json({
    annotations: projectAnnotations,
    dataPoints: project?.dataPoints || [],
    exportedAt: new Date().toISOString(),
  })
})

app.use(
  '/api/health',
  (req: Request, res: Response, next: NextFunction): void => {
    res.status(200).json({
      success: true,
      message: 'ok',
    })
  },
)

app.use((error: Error, req: Request, res: Response, next: NextFunction) => {
  res.status(500).json({
    success: false,
    error: 'Server internal error',
  })
})

app.use((req: Request, res: Response) => {
  res.status(404).json({
    success: false,
    error: 'API not found',
  })
})

export default app

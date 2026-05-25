import { Router } from 'express'
import multer from 'multer'
import path from 'path'
import fs from 'fs'
import db from '../database'

const router = Router()

const uploadDir = path.join(process.cwd(), 'uploads')
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true })
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadDir)
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1e9)
    cb(null, `${uniqueSuffix}${path.extname(file.originalname)}`)
  },
})

const upload = multer({ storage })

router.get('/', (req, res) => {
  const projects = db.prepare(`
    SELECT p.*, u.username as creator_name
    FROM projects p
    LEFT JOIN users u ON p.created_by = u.id
    ORDER BY p.created_at DESC
  `).all()

  res.json(projects.map((p: any) => ({
    id: p.id.toString(),
    name: p.name,
    description: p.description,
    pointCloudPath: p.point_cloud_path,
    createdAt: p.created_at,
    createdBy: p.created_by?.toString(),
  })))
})

router.get('/:id', (req, res) => {
  const project = db.prepare(`
    SELECT p.*, u.username as creator_name
    FROM projects p
    LEFT JOIN users u ON p.created_by = u.id
    WHERE p.id = ?
  `).get(req.params.id)

  if (!project) {
    return res.status(404).json({ error: 'Project not found' })
  }

  res.json({
    id: (project as any).id.toString(),
    name: (project as any).name,
    description: (project as any).description,
    pointCloudPath: (project as any).point_cloud_path,
    createdAt: (project as any).created_at,
    createdBy: (project as any).created_by?.toString(),
  })
})

router.post('/', (req, res) => {
  const { name, description } = req.body
  const createdBy = 1

  const result = db.prepare(`
    INSERT INTO projects (name, description, created_by)
    VALUES (?, ?, ?)
  `).run(name, description || '', createdBy)

  const project = db.prepare('SELECT * FROM projects WHERE id = ?').get(result.lastInsertRowid)

  res.status(201).json({
    id: (project as any).id.toString(),
    name: (project as any).name,
    description: (project as any).description,
    pointCloudPath: (project as any).point_cloud_path,
    createdAt: (project as any).created_at,
    createdBy: (project as any).created_by?.toString(),
  })
})

router.post('/:id/upload', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' })
  }

  db.prepare(`
    UPDATE projects
    SET point_cloud_path = ?
    WHERE id = ?
  `).run(req.file.path, req.params.id)

  res.json({
    success: true,
    filePath: req.file.path,
  })
})

export default router

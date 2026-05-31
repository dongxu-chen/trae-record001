import { Router, type Request, type Response } from 'express'
import { readFile, writeFile } from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'
import { v4 as uuidv4 } from 'uuid'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const dataPath = path.join(__dirname, '..', 'data', 'themes.json')

interface ThemeData {
  themes: Theme[]
}

interface Theme {
  id: string
  name: string
  createdAt: string
  updatedAt: string
  colors: Record<string, string>
  fonts: Record<string, string | number>
  charts: Record<string, string | number | boolean | string[]>
  spacing: Record<string, number>
  [key: string]: unknown
}

async function readThemes(): Promise<ThemeData> {
  const raw = await readFile(dataPath, 'utf-8')
  return JSON.parse(raw)
}

async function writeThemes(data: ThemeData): Promise<void> {
  await writeFile(dataPath, JSON.stringify(data, null, 2), 'utf-8')
}

const router = Router()

router.get('/', async (_req: Request, res: Response): Promise<void> => {
  const data = await readThemes()
  res.json(data.themes)
})

router.get('/:id', async (req: Request, res: Response): Promise<void> => {
  const data = await readThemes()
  const theme = data.themes.find((t) => t.id === req.params.id)
  if (!theme) {
    res.status(404).json({ error: 'Theme not found' })
    return
  }
  res.json(theme)
})

router.post('/', async (req: Request, res: Response): Promise<void> => {
  const data = await readThemes()
  const now = new Date().toISOString()
  const newTheme: Theme = {
    id: uuidv4(),
    createdAt: now,
    updatedAt: now,
    ...req.body,
  }
  data.themes.push(newTheme)
  await writeThemes(data)
  res.status(201).json(newTheme)
})

router.put('/:id', async (req: Request, res: Response): Promise<void> => {
  const data = await readThemes()
  const index = data.themes.findIndex((t) => t.id === req.params.id)
  if (index === -1) {
    res.status(404).json({ error: 'Theme not found' })
    return
  }
  const updated: Theme = {
    ...data.themes[index],
    ...req.body,
    id: data.themes[index].id,
    createdAt: data.themes[index].createdAt,
    updatedAt: new Date().toISOString(),
  }
  data.themes[index] = updated
  await writeThemes(data)
  res.json(updated)
})

router.delete('/:id', async (req: Request, res: Response): Promise<void> => {
  const data = await readThemes()
  const index = data.themes.findIndex((t) => t.id === req.params.id)
  if (index === -1) {
    res.status(404).json({ error: 'Theme not found' })
    return
  }
  data.themes.splice(index, 1)
  await writeThemes(data)
  res.status(204).send()
})

export default router

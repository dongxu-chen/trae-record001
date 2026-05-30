import { Router, type Request, type Response } from 'express'

const router = Router()

router.post('/single', (req: Request, res: Response): void => {
  const { imageData, filterConfig } = req.body
  if (!imageData) {
    res.status(400).json({ success: false, error: 'imageData is required' })
    return
  }
  const base64Match = imageData.match(/^data:image\/(png|jpeg|jpg|webp);base64,(.+)$/)
  if (!base64Match) {
    res.status(400).json({ success: false, error: 'Invalid image data format' })
    return
  }
  const mimeType = base64Match[1] === 'jpg' ? 'jpeg' : base64Match[1]
  const buffer = Buffer.from(base64Match[2], 'base64')
  res.setHeader('Content-Type', `image/${mimeType}`)
  res.setHeader('X-Filter-Config', JSON.stringify(filterConfig || {}))
  res.send(buffer)
})

router.post('/batch', (req: Request, res: Response): void => {
  const { items } = req.body
  if (!items || !Array.isArray(items)) {
    res.status(400).json({ success: false, error: 'items array is required' })
    return
  }
  res.json({
    success: true,
    message: 'Batch processing started',
    count: items.length,
  })
})

export default router

import { Router } from 'express'
import { exportPNG, downloadPNG } from '../controllers/exportController.js'

const router = Router()

router.post('/export/png', exportPNG)
router.get('/download/:filename', downloadPNG)

export default router

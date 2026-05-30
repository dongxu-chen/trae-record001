/**
 * This is a API server
 */

import express, {
  type Request,
  type Response,
  type NextFunction,
} from 'express'
import cors from 'cors'
import path from 'path'
import dotenv from 'dotenv'
import { fileURLToPath } from 'url'
import './db.js'
import dashboardRoutes from './routes/dashboard.js'
import rulesRoutes from './routes/rules.js'
import scoresRoutes from './routes/scores.js'
import alertsRoutes from './routes/alerts.js'
import impactRoutes from './routes/impact.js'
import lineageRoutes from './routes/lineage.js'
import samplesRoutes from './routes/samples.js'
import forecastRoutes from './routes/forecast.js'

// for esm mode
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// load env
dotenv.config()

const app: express.Application = express()

app.use(cors())
app.use(express.json({ limit: '10mb' }))
app.use(express.urlencoded({ extended: true, limit: '10mb' }))

/**
 * API Routes
 */
app.use('/api/dashboard', dashboardRoutes)
app.use('/api/rules', rulesRoutes)
app.use('/api/scores', scoresRoutes)
app.use('/api/alerts', alertsRoutes)
app.use('/api/impact', impactRoutes)
app.use('/api/lineage', lineageRoutes)
app.use('/api/samples', samplesRoutes)
app.use('/api/forecast', forecastRoutes)

/**
 * health
 */
app.use(
  '/api/health',
  (req: Request, res: Response, next: NextFunction): void => {
    res.status(200).json({
      success: true,
      message: 'ok',
    })
  },
)

/**
 * error handler middleware
 */
app.use((error: Error, req: Request, res: Response, next: NextFunction) => {
  res.status(500).json({
    success: false,
    error: 'Server internal error',
  })
})

/**
 * 404 handler
 */
app.use((req: Request, res: Response) => {
  res.status(404).json({
    success: false,
    error: 'API not found',
  })
})

export default app

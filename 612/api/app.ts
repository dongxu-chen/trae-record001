import express from 'express'
import cors from 'cors'
import themeRoutes from './routes/themes.js'

const app = express()

app.use(cors())
app.use(express.json())

app.use('/api/themes', themeRoutes)

app.use((error: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  res.status(500).json({ error: 'Server internal error' })
})

app.use((req: express.Request, res: express.Response) => {
  res.status(404).json({ error: 'API not found' })
})

export default app

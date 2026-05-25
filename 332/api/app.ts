import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import authRoutes from './routes/authRoutes.js';
import dynamicRoutes from './routes/dynamicRoutes.js';
import statsRoutes from './routes/statsRoutes.js';
import qrRoutes from './routes/qrRoutes.js';
import { redirectShortCode } from './controllers/dynamicController.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

app.use(cors());
app.use(express.json());
app.use(morgan('dev'));

app.get('/r/:shortCode', redirectShortCode);

app.use('/api/auth', authRoutes);
app.use('/api/dynamic', dynamicRoutes);
app.use('/api/stats', statsRoutes);
app.use('/api/qrcodes', qrRoutes);

app.use(express.static(path.join(__dirname, '../dist')));

app.get('*', (req, res) => {
  if (!req.path.startsWith('/api') && !req.path.startsWith('/r/')) {
    res.sendFile(path.join(__dirname, '../dist/index.html'));
  }
});

app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error(err.stack);
  res.status(500).json({
    success: false,
    message: '服务器内部错误',
  });
});

export default app;

import express from 'express';
import cors from 'cors';
import pdfRoutes from './routes/pdfRoutes.js';
import ocrRoutes from './routes/ocrRoutes.js';
import reviewRoutes from './routes/reviewRoutes.js';

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

app.use('/api/pdf', pdfRoutes);
app.use('/api/ocr', ocrRoutes);
app.use('/api/review', reviewRoutes);

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'PDF Annotator Server is running' });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});

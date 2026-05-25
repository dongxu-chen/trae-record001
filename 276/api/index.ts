import express from 'express';
import cors from 'cors';
import mongoose from 'mongoose';
import boardRoutes from './routes/boards';
import taskRoutes from './routes/tasks';
import automationRoutes from './routes/automation';
import templateRoutes from './routes/templates';

const app = express();
const PORT = process.env.PORT || 5000;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/task-kanban';

app.use(cors());
app.use(express.json());

mongoose.connect(MONGODB_URI)
  .then(() => console.log('MongoDB connected successfully'))
  .catch(err => console.error('MongoDB connection error:', err));

app.use('/api/boards', boardRoutes);
app.use('/api/tasks', taskRoutes);
app.use('/api/automation', automationRoutes);
app.use('/api/templates', templateRoutes);

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Server is running' });
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

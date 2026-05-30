require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');

const taskRoutes = require('./src/routes/tasks');
const documentRoutes = require('./src/routes/documents');
const annotationRoutes = require('./src/routes/annotations');
const exportRoutes = require('./src/routes/export');
const preAnnotateRoutes = require('./src/routes/preannotate');
const templateRoutes = require('./src/routes/templates');
const qualityRoutes = require('./src/routes/quality');
const achievementRoutes = require('./src/routes/achievements');

const { initializeDefaultTemplates } = require('./src/controllers/templateController');
const { initializeDefaultAchievements } = require('./src/controllers/achievementController');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

mongoose.connect(process.env.MONGODB_URI, {
  useNewUrlParser: true,
  useUnifiedTopology: true
});

const db = mongoose.connection;
db.on('error', console.error.bind(console, 'MongoDB connection error:'));
db.once('open', async () => {
  console.log('Connected to MongoDB');
  try {
    await initializeDefaultTemplates();
    await initializeDefaultAchievements();
  } catch (error) {
    console.error('Error initializing defaults:', error);
  }
});

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Annotation Tool API is running' });
});

app.use('/api/tasks', taskRoutes);
app.use('/api/documents', documentRoutes);
app.use('/api/annotations', annotationRoutes);
app.use('/api/export', exportRoutes);
app.use('/api/preannotate', preAnnotateRoutes);
app.use('/api/templates', templateRoutes);
app.use('/api/quality', qualityRoutes);
app.use('/api/achievements', achievementRoutes);

app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

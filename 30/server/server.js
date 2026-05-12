require('dotenv').config();
const express = require('express');
const cors = require('cors');
const examRoutes = require('./routes/exam');
const proctorRoutes = require('./proctor');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.json({ limit: '10mb' }));

app.use('/api/exam', examRoutes);
app.use('/api/proctor', proctorRoutes);

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
  console.log(`Exam API: http://localhost:${PORT}/api/exam`);
  console.log(`Proctor API: http://localhost:${PORT}/api/proctor`);
});

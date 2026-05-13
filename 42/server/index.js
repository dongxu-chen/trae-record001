const express = require('express');
const cors = require('cors');
const feedRoutes = require('./routes/feed');
const interactRoutes = require('./routes/interact');
const { redis } = require('./cache');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.use('/api/feed', feedRoutes);
app.use('/api/interact', interactRoutes);

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.get('/health/cache', async (req, res) => {
  try {
    const isConnected = await redis.ping();
    res.json({ 
      status: 'ok', 
      cacheConnected: isConnected === 'PONG',
      message: 'Redis connection healthy'
    });
  } catch (error) {
    res.status(503).json({ 
      status: 'error', 
      cacheConnected: false,
      message: 'Redis connection failed',
      error: error.message
    });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

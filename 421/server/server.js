const express = require('express');
const http = require('http');
const mongoose = require('mongoose');
const cors = require('cors');
const dotenv = require('dotenv');
const socketIo = require('socket.io');
const ShareDB = require('sharedb');
const ShareDBMongo = require('sharedb-mongo');

dotenv.config();

const authRoutes = require('./routes/auth');
const documentRoutes = require('./routes/documents');
const reviewRoutes = require('./routes/reviews');
const commentRoutes = require('./routes/comments');
const notificationRoutes = require('./routes/notifications');
const aiRoutes = require('./routes/ai');
const templateRoutes = require('./routes/templates');
const statsRoutes = require('./routes/stats');

const otController = require('./controllers/otController');

const app = express();
const server = http.createServer(app);

app.use(cors({
  origin: 'http://localhost:3000',
  credentials: true
}));
app.use(express.json());

mongoose.connect(process.env.MONGODB_URI, {
  useNewUrlParser: true,
  useUnifiedTopology: true
}).then(() => console.log('MongoDB connected'))
  .catch(err => console.error('MongoDB connection error:', err));

const shareDBMongo = ShareDBMongo(process.env.MONGODB_URI);
const shareDB = new ShareDB({ db: shareDBMongo });
const connection = shareDB.connect();

app.use((req, res, next) => {
  req.shareDBConnection = connection;
  next();
});

app.use('/api/auth', authRoutes);
app.use('/api/documents', documentRoutes);
app.use('/api/reviews', reviewRoutes);
app.use('/api/comments', commentRoutes);
app.use('/api/notifications', notificationRoutes);
app.use('/api/ai', aiRoutes);
app.use('/api/templates', templateRoutes);
app.use('/api/stats', statsRoutes);

const io = socketIo(server, {
  cors: {
    origin: 'http://localhost:3000',
    methods: ['GET', 'POST']
  }
});

otController.initialize(io, shareDB, connection);

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

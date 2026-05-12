const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const cors = require('koa2-cors');
const mongoose = require('mongoose');
const path = require('path');

require('./services/redis');

const songRouter = require('./routes/song');
const recommendRouter = require('./routes/recommend');

const app = new Koa();
const router = new Router();

mongoose.connect('mongodb://localhost:27017/music-streaming')
  .then(() => console.log('MongoDB connected'))
  .catch(err => console.error('MongoDB connection error:', err));

app.use(cors({
  origin: '*',
  allowMethods: ['GET', 'POST', 'PUT', 'DELETE'],
  allowHeaders: ['Content-Type', 'Authorization']
}));

app.use(bodyParser());

router.use('/api/songs', songRouter.routes(), songRouter.allowedMethods());
router.use('/api/recommend', recommendRouter.routes(), recommendRouter.allowedMethods());

app.use(router.routes());
app.use(router.allowedMethods());

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
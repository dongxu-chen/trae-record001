const Router = require('koa-router');
const mongoose = require('mongoose');

const {
  getUserRecommendations,
  getSimilarSongs,
  getPopularSongs,
  recordPlay,
  addSongFeatures
} = require('../services/recommend');

const router = new Router();

const Song = mongoose.model('Song');

router.get('/user/:userId', async (ctx) => {
  try {
    const { userId } = ctx.params;
    const topN = parseInt(ctx.query.topN || '10', 10);
    
    const songIds = await getUserRecommendations(userId, topN);
    
    if (songIds.length === 0) {
      const popularIds = await getPopularSongs(topN);
      if (popularIds.length === 0) {
        const songs = await Song.find().sort({ playCount: -1 }).limit(topN);
        ctx.body = { success: true, data: songs };
        return;
      }
      
      const songs = await Song.find({ _id: { $in: popularIds } });
      const sortedSongs = popularIds.map(id => songs.find(s => s._id.toString() === id)).filter(Boolean);
      ctx.body = { success: true, data: sortedSongs };
      return;
    }
    
    const songs = await Song.find({ _id: { $in: songIds } });
    const sortedSongs = songIds.map(id => songs.find(s => s._id.toString() === id)).filter(Boolean);
    
    ctx.body = { success: true, data: sortedSongs };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

router.get('/similar/:songId', async (ctx) => {
  try {
    const { songId } = ctx.params;
    const topN = parseInt(ctx.query.topN || '10', 10);
    
    const songIds = await getSimilarSongs(songId, topN);
    
    if (songIds.length === 0) {
      ctx.body = { success: true, data: [] };
      return;
    }
    
    const songs = await Song.find({ _id: { $in: songIds } });
    const sortedSongs = songIds.map(id => songs.find(s => s._id.toString() === id)).filter(Boolean);
    
    ctx.body = { success: true, data: sortedSongs };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

router.get('/popular', async (ctx) => {
  try {
    const topN = parseInt(ctx.query.topN || '10', 10);
    
    const songIds = await getPopularSongs(topN);
    
    if (songIds.length === 0) {
      const songs = await Song.find().sort({ playCount: -1 }).limit(topN);
      ctx.body = { success: true, data: songs };
      return;
    }
    
    const songs = await Song.find({ _id: { $in: songIds } });
    const sortedSongs = songIds.map(id => songs.find(s => s._id.toString() === id)).filter(Boolean);
    
    if (sortedSongs.length === 0) {
      const fallback = await Song.find().sort({ playCount: -1 }).limit(topN);
      ctx.body = { success: true, data: fallback };
      return;
    }
    
    ctx.body = { success: true, data: sortedSongs };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

router.post('/play', async (ctx) => {
  try {
    const { userId, songId } = ctx.request.body;
    
    if (!userId || !songId) {
      ctx.status = 400;
      ctx.body = { success: false, message: 'userId and songId are required' };
      return;
    }
    
    await recordPlay(userId, songId);
    
    ctx.body = { success: true };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

router.post('/features/:songId', async (ctx) => {
  try {
    const { songId } = ctx.params;
    const features = ctx.request.body;
    
    if (!features || Object.keys(features).length === 0) {
      ctx.status = 400;
      ctx.body = { success: false, message: 'Features are required' };
      return;
    }
    
    await addSongFeatures(songId, features);
    
    ctx.body = { success: true };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

module.exports = router;

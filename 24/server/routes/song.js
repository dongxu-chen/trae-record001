const Router = require('koa-router');
const mongoose = require('mongoose');
const fs = require('fs');
const path = require('path');

const router = new Router();

const songSchema = new mongoose.Schema({
  title: { type: String, required: true },
  artist: { type: String, required: true },
  album: String,
  duration: Number,
  url: { type: String, required: true },
  filePath: String,
  fileSize: Number,
  cover: String,
  lyrics: String,
  playCount: { type: Number, default: 0 },
  createdAt: { type: Date, default: Date.now }
});

const Song = mongoose.model('Song', songSchema);

function parseRange(rangeHeader, fileSize) {
  if (!rangeHeader) {
    return null;
  }
  
  const match = rangeHeader.match(/bytes=(\d*)-(\d*)/);
  if (!match) {
    return null;
  }
  
  const startStr = match[1];
  const endStr = match[2];
  
  let start = startStr ? parseInt(startStr, 10) : 0;
  let end = endStr ? parseInt(endStr, 10) : fileSize - 1;
  
  if (start > end || start >= fileSize) {
    return null;
  }
  
  end = Math.min(end, fileSize - 1);
  
  return { start, end };
}

router.get('/', async (ctx) => {
  try {
    const songs = await Song.find().sort({ createdAt: -1 });
    ctx.body = { success: true, data: songs };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

router.get('/:id', async (ctx) => {
  try {
    const song = await Song.findById(ctx.params.id);
    if (!song) {
      ctx.status = 404;
      ctx.body = { success: false, message: 'Song not found' };
      return;
    }
    ctx.body = { success: true, data: song };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

router.get('/:id/stream', async (ctx) => {
  try {
    const song = await Song.findById(ctx.params.id);
    if (!song) {
      ctx.status = 404;
      ctx.body = { success: false, message: 'Song not found' };
      return;
    }
    
    const rangeHeader = ctx.headers.range;
    const isNewPlay = !rangeHeader || rangeHeader === 'bytes=0-';
    
    if (isNewPlay) {
      song.playCount = (song.playCount || 0) + 1;
      await song.save();
    }
    
    if (song.filePath) {
      if (!fs.existsSync(song.filePath)) {
        ctx.status = 404;
        ctx.body = { success: false, message: 'Audio file not found' };
        return;
      }
      
      const stat = fs.statSync(song.filePath);
      const fileSize = stat.size;
      
      if (rangeHeader) {
        const range = parseRange(rangeHeader, fileSize);
        
        if (!range) {
          ctx.status = 416;
          ctx.set('Content-Range', `bytes */${fileSize}`);
          ctx.body = { success: false, message: 'Range Not Satisfiable' };
          return;
        }
        
        const { start, end } = range;
        const chunkSize = end - start + 1;
        
        ctx.status = 206;
        ctx.set('Content-Range', `bytes ${start}-${end}/${fileSize}`);
        ctx.set('Accept-Ranges', 'bytes');
        ctx.set('Content-Length', chunkSize);
        ctx.set('Content-Type', 'audio/mpeg');
        
        ctx.body = fs.createReadStream(song.filePath, { start, end });
      } else {
        ctx.status = 200;
        ctx.set('Content-Length', fileSize);
        ctx.set('Accept-Ranges', 'bytes');
        ctx.set('Content-Type', 'audio/mpeg');
        
        ctx.body = fs.createReadStream(song.filePath);
      }
    } else if (song.url) {
      ctx.redirect(song.url);
    } else {
      ctx.status = 404;
      ctx.body = { success: false, message: 'No audio source available' };
    }
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

router.post('/', async (ctx) => {
  try {
    const { title, artist, album, duration, url, cover, lyrics } = ctx.request.body;
    const song = new Song({ title, artist, album, duration, url, cover, lyrics });
    await song.save();
    ctx.status = 201;
    ctx.body = { success: true, data: song };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

router.put('/:id', async (ctx) => {
  try {
    const song = await Song.findByIdAndUpdate(
      ctx.params.id,
      ctx.request.body,
      { new: true, runValidators: true }
    );
    if (!song) {
      ctx.status = 404;
      ctx.body = { success: false, message: 'Song not found' };
      return;
    }
    ctx.body = { success: true, data: song };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

router.get('/:id/lyrics', async (ctx) => {
  try {
    const song = await Song.findById(ctx.params.id);
    if (!song) {
      ctx.status = 404;
      ctx.body = { success: false, message: 'Song not found' };
      return;
    }
    ctx.body = {
      success: true,
      data: {
        lyrics: song.lyrics || ''
      }
    };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

router.put('/:id/lyrics', async (ctx) => {
  try {
    const { lyrics } = ctx.request.body;
    const song = await Song.findByIdAndUpdate(
      ctx.params.id,
      { lyrics },
      { new: true }
    );
    if (!song) {
      ctx.status = 404;
      ctx.body = { success: false, message: 'Song not found' };
      return;
    }
    ctx.body = {
      success: true,
      data: {
        lyrics: song.lyrics
      }
    };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

router.delete('/:id', async (ctx) => {
  try {
    const song = await Song.findByIdAndDelete(ctx.params.id);
    if (!song) {
      ctx.status = 404;
      ctx.body = { success: false, message: 'Song not found' };
      return;
    }
    ctx.body = { success: true, message: 'Song deleted' };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { success: false, message: error.message };
  }
});

module.exports = router;
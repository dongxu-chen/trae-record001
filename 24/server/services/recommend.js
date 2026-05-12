const { spawn } = require('child_process');
const path = require('path');
const { redis, CACHE_TTL, getOrSet } = require('./redis');

const RECOMMEND_PY_PATH = path.join(__dirname, '..', 'recommend.py');
const RECOMMEND_STATE_KEY = 'recommend:state';

async function runPythonScript(args) {
  return new Promise((resolve, reject) => {
    const python = process.platform === 'win32' ? 'python' : 'python3';
    const process = spawn(python, [RECOMMEND_PY_PATH, ...args]);
    
    let stdout = '';
    let stderr = '';
    
    process.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    process.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    process.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(stderr || `Python script exited with code ${code}`));
        return;
      }
      
      try {
        const result = JSON.parse(stdout.trim());
        resolve(result);
      } catch (error) {
        reject(new Error('Failed to parse Python output: ' + stdout));
      }
    });
    
    process.on('error', (error) => {
      reject(error);
    });
  });
}

async function getRecommendState() {
  try {
    const state = await redis.get(RECOMMEND_STATE_KEY);
    return state ? JSON.parse(state) : null;
  } catch (error) {
    console.error('Get recommend state error:', error);
    return null;
  }
}

async function saveRecommendState(state) {
  try {
    await redis.set(RECOMMEND_STATE_KEY, JSON.stringify(state));
  } catch (error) {
    console.error('Save recommend state error:', error);
  }
}

async function getUserRecommendations(userId, topN = 10) {
  const cacheKey = `recommend:user:${userId}:${topN}`;
  
  return getOrSet(cacheKey, async () => {
    try {
      const state = await getRecommendState();
      const args = ['recommend', userId, String(topN)];
      if (state) {
        args.push(JSON.stringify(state));
      }
      
      const result = await runPythonScript(args);
      
      if (result.error) {
        throw new Error(result.error);
      }
      
      return result.recommendations || [];
    } catch (error) {
      console.error('Get user recommendations error:', error);
      return [];
    }
  }, CACHE_TTL.MEDIUM);
}

async function getSimilarSongs(songId, topN = 10) {
  const cacheKey = `recommend:similar:${songId}:${topN}`;
  
  return getOrSet(cacheKey, async () => {
    try {
      const state = await getRecommendState();
      const args = ['similar', songId, String(topN)];
      if (state) {
        args.push(JSON.stringify(state));
      }
      
      const result = await runPythonScript(args);
      
      if (result.error) {
        throw new Error(result.error);
      }
      
      return result.similar || [];
    } catch (error) {
      console.error('Get similar songs error:', error);
      return [];
    }
  }, CACHE_TTL.LONG);
}

async function getPopularSongs(topN = 10) {
  const cacheKey = `recommend:popular:${topN}`;
  
  return getOrSet(cacheKey, async () => {
    try {
      const state = await getRecommendState();
      const args = ['popular', String(topN)];
      if (state) {
        args.push(JSON.stringify(state));
      }
      
      const result = await runPythonScript(args);
      
      if (result.error) {
        throw new Error(result.error);
      }
      
      return result.popular || [];
    } catch (error) {
      console.error('Get popular songs error:', error);
      return [];
    }
  }, CACHE_TTL.POPULAR_SONGS);
}

async function recordPlay(userId, songId) {
  try {
    let state = await getRecommendState();
    const args = ['add_play', userId, songId];
    if (state) {
      args.push(JSON.stringify(state));
    }
    
    const result = await runPythonScript(args);
    
    if (result.success && result.state) {
      await saveRecommendState(result.state);
      
      const { invalidatePattern } = require('./redis');
      await invalidatePattern('recommend:user:*');
      await invalidatePattern('recommend:popular:*');
    }
  } catch (error) {
    console.error('Record play error:', error);
  }
}

async function addSongFeatures(songId, features) {
  try {
    let state = await getRecommendState();
    const args = ['add_features', songId, JSON.stringify(features)];
    if (state) {
      args.push(JSON.stringify(state));
    }
    
    const result = await runPythonScript(args);
    
    if (result.success && result.state) {
      await saveRecommendState(result.state);
      
      const { invalidatePattern } = require('./redis');
      await invalidatePattern('recommend:similar:*');
    }
  } catch (error) {
    console.error('Add song features error:', error);
  }
}

module.exports = {
  getUserRecommendations,
  getSimilarSongs,
  getPopularSongs,
  recordPlay,
  addSongFeatures
};

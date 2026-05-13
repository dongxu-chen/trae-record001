const express = require('express');
const {
  searchVideos,
  fuzzySearchVideos,
  recordInteraction,
  getUserPreferences,
  initializeIndices,
  insertSampleVideos,
} = require('../elastic');

const router = express.Router();

const MAX_VIDEOS_PER_REQUEST = 10;

router.get('/initialize', async (req, res) => {
  try {
    await initializeIndices();
    await insertSampleVideos();
    res.json({ message: 'Indices initialized with sample data' });
  } catch (error) {
    console.error('Initialization error:', error);
    res.status(500).json({ error: 'Failed to initialize' });
  }
});

router.get('/', async (req, res) => {
  try {
    const {
      userId = 'anonymous',
      excludedIds = '',
      limit = MAX_VIDEOS_PER_REQUEST,
      q = '',
    } = req.query;

    const excludedVideoIds = excludedIds ? excludedIds.split(',').filter(Boolean) : [];
    const requestLimit = Math.min(parseInt(limit) || MAX_VIDEOS_PER_REQUEST, MAX_VIDEOS_PER_REQUEST);

    let videos;
    if (q && q.trim()) {
      videos = await fuzzySearchVideos({
        query: q.trim(),
        excludedVideoIds,
        limit: requestLimit,
      });
    } else {
      const userPreferences = userId !== 'anonymous'
        ? await getUserPreferences(userId)
        : [];

      videos = await searchVideos({
        userId,
        excludedVideoIds,
        limit: requestLimit,
        userPreferences,
      });
    }

    const seenIds = new Set();
    const uniqueVideos = videos.filter((video) => {
      if (seenIds.has(video.id)) {
        return false;
      }
      seenIds.add(video.id);
      return true;
    });

    res.json({
      videos: uniqueVideos,
      count: uniqueVideos.length,
      searchQuery: q || null,
    });
  } catch (error) {
    console.error('Feed error:', error);
    res.status(500).json({ error: 'Failed to fetch feed' });
  }
});

router.post('/interact', async (req, res) => {
  try {
    const {
      userId = 'anonymous',
      videoId,
      interactionType,
      durationWatched = 0,
    } = req.body;

    if (!videoId || !interactionType) {
      return res.status(400).json({
        error: 'videoId and interactionType are required',
      });
    }

    const validTypes = ['view', 'like', 'unlike', 'comment', 'share', 'complete_watch', 'skip'];
    if (!validTypes.includes(interactionType)) {
      return res.status(400).json({
        error: `Invalid interaction type. Must be one of: ${validTypes.join(', ')}`,
      });
    }

    await recordInteraction({
      userId,
      videoId,
      interactionType,
      durationWatched: parseFloat(durationWatched) || 0,
    });

    res.json({ success: true });
  } catch (error) {
    console.error('Interaction error:', error);
    res.status(500).json({ error: 'Failed to record interaction' });
  }
});

router.get('/preferences/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    const preferences = await getUserPreferences(userId);

    res.json({
      userId,
      preferences,
    });
  } catch (error) {
    console.error('Preferences error:', error);
    res.status(500).json({ error: 'Failed to get preferences' });
  }
});

module.exports = router;

const express = require('express');
const {
  cacheLike,
  removeCachedLike,
  getUserLikes,
  getVideoLikes,
  isLiked,
  addComment,
  getVideoComments,
  cacheFollow,
  removeCachedFollow,
  getFollowers,
  getFollowing,
  isFollowing,
  invalidateUserFeed,
} = require('../cache');

const { client, VIDEO_INDEX, USER_INTERACTIONS_INDEX } = require('../elastic');

const router = express.Router();

router.post('/like', async (req, res) => {
  try {
    const { userId, videoId } = req.body;

    if (!userId || !videoId) {
      return res.status(400).json({
        error: 'userId and videoId are required',
      });
    }

    const alreadyLiked = await isLiked(userId, videoId);
    if (alreadyLiked) {
      return res.status(200).json({ success: true, liked: true });
    }

    await cacheLike(userId, videoId);
    invalidateUserFeed(userId);

    await client.index({
      index: USER_INTERACTIONS_INDEX,
      document: {
        userId,
        videoId,
        interactionType: 'like',
        timestamp: new Date(),
      },
      refresh: true,
    });

    await client.update({
      index: VIDEO_INDEX,
      id: videoId,
      script: {
        source: 'ctx._source.likes += 1',
      },
    });

    res.json({ success: true, liked: true });
  } catch (error) {
    console.error('Like error:', error);
    res.status(500).json({ error: 'Failed to like video' });
  }
});

router.post('/unlike', async (req, res) => {
  try {
    const { userId, videoId } = req.body;

    if (!userId || !videoId) {
      return res.status(400).json({
        error: 'userId and videoId are required',
      });
    }

    await removeCachedLike(userId, videoId);
    invalidateUserFeed(userId);

    await client.index({
      index: USER_INTERACTIONS_INDEX,
      document: {
        userId,
        videoId,
        interactionType: 'unlike',
        timestamp: new Date(),
      },
      refresh: true,
    });

    await client.update({
      index: VIDEO_INDEX,
      id: videoId,
      script: {
        source: 'if (ctx._source.likes > 0) { ctx._source.likes -= 1 }',
      },
    });

    res.json({ success: true, liked: false });
  } catch (error) {
    console.error('Unlike error:', error);
    res.status(500).json({ error: 'Failed to unlike video' });
  }
});

router.get('/likes/videos/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    const likedVideoIds = await getUserLikes(userId);

    let videos = [];
    if (likedVideoIds.length > 0) {
      const result = await client.search({
        index: VIDEO_INDEX,
        query: {
          terms: {
            id: likedVideoIds,
          },
        },
        size: likedVideoIds.length,
      });

      videos = result.hits.hits.map((hit) => ({
        id: hit._source.id,
        ...hit._source,
      }));
    }

    res.json({
      userId,
      count: videos.length,
      videos,
    });
  } catch (error) {
    console.error('Get likes error:', error);
    res.status(500).json({ error: 'Failed to get likes' });
  }
});

router.get('/likes/users/:videoId', async (req, res) => {
  try {
    const { videoId } = req.params;
    const userIds = await getVideoLikes(videoId);

    res.json({
      videoId,
      count: userIds.length,
      userIds,
    });
  } catch (error) {
    console.error('Get video likes error:', error);
    res.status(500).json({ error: 'Failed to get video likes' });
  }
});

router.post('/comments', async (req, res) => {
  try {
    const { userId, videoId, content, parentCommentId = null } = req.body;

    if (!userId || !videoId || !content) {
      return res.status(400).json({
        error: 'userId, videoId, and content are required',
      });
    }

    const comment = {
      id: `comment_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      userId,
      videoId,
      content: content.trim(),
      parentCommentId,
      createdAt: new Date(),
      likes: 0,
    };

    await addComment(comment);

    await client.index({
      index: USER_INTERACTIONS_INDEX,
      document: {
        ...comment,
        interactionType: 'comment',
      },
      refresh: true,
    });

    await client.update({
      index: VIDEO_INDEX,
      id: videoId,
      script: {
        source: 'ctx._source.comments += 1',
      },
    });

    res.json({ success: true, comment });
  } catch (error) {
    console.error('Comment error:', error);
    res.status(500).json({ error: 'Failed to add comment' });
  }
});

router.get('/comments/:videoId', async (req, res) => {
  try {
    const { videoId } = req.params;
    const { limit = 50 } = req.query;

    const cachedComments = await getVideoComments(videoId, parseInt(limit));

    if (cachedComments.length > 0) {
      return res.json({
        videoId,
        count: cachedComments.length,
        comments: cachedComments,
        fromCache: true,
      });
    }

    const result = await client.search({
      index: USER_INTERACTIONS_INDEX,
      query: {
        bool: {
          must: [
            { term: { videoId } },
            { term: { interactionType: 'comment' } },
          ],
        },
      },
      sort: [{ timestamp: { order: 'desc' } }],
      size: parseInt(limit),
    });

    const comments = result.hits.hits.map((hit) => ({
      id: hit._source.id,
      userId: hit._source.userId,
      videoId: hit._source.videoId,
      content: hit._source.content,
      parentCommentId: hit._source.parentCommentId,
      createdAt: hit._source.timestamp,
      likes: hit._source.likes || 0,
    }));

    for (const comment of comments) {
      await addComment(comment);
    }

    res.json({
      videoId,
      count: comments.length,
      comments,
      fromCache: false,
    });
  } catch (error) {
    console.error('Get comments error:', error);
    res.status(500).json({ error: 'Failed to get comments' });
  }
});

router.post('/follow', async (req, res) => {
  try {
    const { followerId, followingId } = req.body;

    if (!followerId || !followingId) {
      return res.status(400).json({
        error: 'followerId and followingId are required',
      });
    }

    if (followerId === followingId) {
      return res.status(400).json({
        error: 'Cannot follow yourself',
      });
    }

    const alreadyFollowing = await isFollowing(followerId, followingId);
    if (alreadyFollowing) {
      return res.status(200).json({ success: true, following: true });
    }

    await cacheFollow(followerId, followingId);
    invalidateUserFeed(followerId);

    await client.index({
      index: USER_INTERACTIONS_INDEX,
      document: {
        userId: followerId,
        targetUserId: followingId,
        interactionType: 'follow',
        timestamp: new Date(),
      },
      refresh: true,
    });

    res.json({ success: true, following: true });
  } catch (error) {
    console.error('Follow error:', error);
    res.status(500).json({ error: 'Failed to follow user' });
  }
});

router.post('/unfollow', async (req, res) => {
  try {
    const { followerId, followingId } = req.body;

    if (!followerId || !followingId) {
      return res.status(400).json({
        error: 'followerId and followingId are required',
      });
    }

    await removeCachedFollow(followerId, followingId);
    invalidateUserFeed(followerId);

    await client.index({
      index: USER_INTERACTIONS_INDEX,
      document: {
        userId: followerId,
        targetUserId: followingId,
        interactionType: 'unfollow',
        timestamp: new Date(),
      },
      refresh: true,
    });

    res.json({ success: true, following: false });
  } catch (error) {
    console.error('Unfollow error:', error);
    res.status(500).json({ error: 'Failed to unfollow user' });
  }
});

router.get('/followers/:userId', async (req, res) => {
  try {
    const { userId } = req.params;

    const cachedFollowers = await getFollowers(userId);

    if (cachedFollowers.length > 0) {
      return res.json({
        userId,
        count: cachedFollowers.length,
        followerIds: cachedFollowers,
        fromCache: true,
      });
    }

    const result = await client.search({
      index: USER_INTERACTIONS_INDEX,
      query: {
        bool: {
          must: [
            { term: { targetUserId: userId } },
            { term: { interactionType: 'follow' } },
          ],
          must_not: [
            { term: { interactionType: 'unfollow' } },
          ],
        },
      },
      aggs: {
        uniqueFollowers: {
          terms: {
            field: 'userId',
            size: 1000,
          },
        },
      },
      size: 0,
    });

    const followerIds = result.aggregations?.uniqueFollowers?.buckets?.map((b) => b.key) || [];

    for (const followerId of followerIds) {
      await cacheFollow(followerId, userId);
    }

    res.json({
      userId,
      count: followerIds.length,
      followerIds,
      fromCache: false,
    });
  } catch (error) {
    console.error('Get followers error:', error);
    res.status(500).json({ error: 'Failed to get followers' });
  }
});

router.get('/following/:userId', async (req, res) => {
  try {
    const { userId } = req.params;

    const cachedFollowing = await getFollowing(userId);

    if (cachedFollowing.length > 0) {
      return res.json({
        userId,
        count: cachedFollowing.length,
        followingIds: cachedFollowing,
        fromCache: true,
      });
    }

    const result = await client.search({
      index: USER_INTERACTIONS_INDEX,
      query: {
        bool: {
          must: [
            { term: { userId } },
            { term: { interactionType: 'follow' } },
          ],
          must_not: [
            { term: { interactionType: 'unfollow' } },
          ],
        },
      },
      aggs: {
        uniqueFollowing: {
          terms: {
            field: 'targetUserId',
            size: 1000,
          },
        },
      },
      size: 0,
    });

    const followingIds = result.aggregations?.uniqueFollowing?.buckets?.map((b) => b.key) || [];

    for (const followingId of followingIds) {
      await cacheFollow(userId, followingId);
    }

    res.json({
      userId,
      count: followingIds.length,
      followingIds,
      fromCache: false,
    });
  } catch (error) {
    console.error('Get following error:', error);
    res.status(500).json({ error: 'Failed to get following' });
  }
});

router.get('/status/follow/:followerId/:followingId', async (req, res) => {
  try {
    const { followerId, followingId } = req.params;
    const following = await isFollowing(followerId, followingId);

    res.json({
      followerId,
      followingId,
      isFollowing: following,
    });
  } catch (error) {
    console.error('Check follow status error:', error);
    res.status(500).json({ error: 'Failed to check follow status' });
  }
});

module.exports = router;

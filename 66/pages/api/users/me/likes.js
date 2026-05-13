import { getServerSession } from 'next-auth/next';
import { connectDB, Image, Like } from '../../../../lib/db';
import { cacheUserLikes, getCachedUserLikes } from '../../../../lib/redis';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const session = await getServerSession(req, res);
    if (!session || !session.user?.id) {
      return res.status(401).json({
        success: false,
        error: '请先登录',
      });
    }

    await connectDB();

    const userId = session.user.id;

    const cached = await getCachedUserLikes(userId);
    if (cached) {
      const images = await Image.find({ _id: { $in: cached } })
        .sort({ createdAt: -1 })
        .lean();

      return res.status(200).json({
        success: true,
        images,
        cached: true,
      });
    }

    const likes = await Like.find({ userId })
      .sort({ createdAt: -1 })
      .limit(50)
      .lean();

    const imageIds = likes.map((like) => like.imageId);

    if (imageIds.length > 0) {
      await cacheUserLikes(userId, imageIds);
    }

    const images = await Image.find({ _id: { $in: imageIds } })
      .sort({ createdAt: -1 })
      .lean();

    res.status(200).json({
      success: true,
      images,
      cached: false,
    });
  } catch (error) {
    console.error('Get user likes error:', error);
    res.status(500).json({ error: 'Failed to fetch user likes' });
  }
}

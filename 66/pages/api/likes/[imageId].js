import { getServerSession } from 'next-auth/next';
import { connectDB, Image, Like } from '../../../lib/db';
import { invalidateTrendingCache, invalidateUserLikesCache } from '../../../lib/redis';

export default async function handler(req, res) {
  const { imageId } = req.query;

  try {
    const session = await getServerSession(req, res);
    if (!session || !session.user?.id) {
      return res.status(401).json({
        success: false,
        redirect: '/api/auth/signin',
        error: '请先登录',
      });
    }

    await connectDB();

    const userId = session.user.id;

    const image = await Image.findById(imageId);
    if (!image) {
      return res.status(404).json({
        success: false,
        error: '图片不存在',
      });
    }

    const existingLike = await Like.findOne({
      userId,
      imageId,
    });

    let liked;

    if (existingLike) {
      await existingLike.deleteOne();
      image.likes = Math.max(0, image.likes - 1);
      liked = false;
    } else {
      await Like.create({
        userId,
        imageId,
      });
      image.likes += 1;
      liked = true;
    }

    await image.save();

    await Promise.all([
      invalidateUserLikesCache(userId),
      invalidateTrendingCache(),
    ]);

    res.status(200).json({
      success: true,
      likes: image.likes,
      liked,
    });
  } catch (error) {
    console.error('Like error:', error);
    res.status(500).json({
      success: false,
      error: '操作失败',
    });
  }
}

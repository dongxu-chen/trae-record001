import { connectDB, User, getUserImagesPaginated } from '../../../../lib/db';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    await connectDB();

    const { name } = req.query;
    const { limit = 12, cursor = null, direction = 'next' } = req.query;

    const user = await User.findOne({ username: name }).lean();
    if (!user) {
      return res.status(404).json({
        success: false,
        error: '用户不存在',
      });
    }

    const limitNum = Math.min(parseInt(limit) || 12, 50);

    const result = await getUserImagesPaginated(user._id, {
      limit: limitNum,
      cursor,
      direction,
    });

    res.status(200).json({
      success: true,
      images: result.images,
      pagination: {
        ...result.pagination,
        limit: limitNum,
      },
      user: {
        id: user._id,
        name: user.name,
        username: user.username,
      },
    });
  } catch (error) {
    console.error('Get user images error:', error);
    res.status(500).json({ error: 'Failed to fetch user images' });
  }
}

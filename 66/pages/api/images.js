import { connectDB, getImagesPaginated } from '../../lib/db';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    await connectDB();

    const {
      limit = 12,
      cursor = null,
      direction = 'next',
      tag = null,
    } = req.query;

    const limitNum = Math.min(parseInt(limit) || 12, 50);

    const result = await getImagesPaginated({
      limit: limitNum,
      cursor,
      direction,
      tag,
    });

    res.status(200).json({
      success: true,
      images: result.images,
      pagination: {
        ...result.pagination,
        limit: limitNum,
      },
    });
  } catch (error) {
    console.error('Get images error:', error);
    res.status(500).json({ error: 'Failed to fetch images' });
  }
}

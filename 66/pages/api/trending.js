import { connectDB, getTrendingImages } from '../../lib/db';
import { cacheTrendingImages, getCachedTrendingImages } from '../../lib/redis';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    let cached = await getCachedTrendingImages();

    if (cached) {
      return res.status(200).json({
        success: true,
        images: cached,
        cached: true,
      });
    }

    await connectDB();
    const images = await getTrendingImages(10);

    if (images.length > 0) {
      await cacheTrendingImages(images);
    }

    res.status(200).json({
      success: true,
      images,
      cached: false,
    });
  } catch (error) {
    console.error('Trending error:', error);
    res.status(500).json({ error: 'Failed to fetch trending images' });
  }
}

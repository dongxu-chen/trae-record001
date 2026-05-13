import { Image, connectDB } from '../../../lib/db';
import { deleteFromCloudinary } from '../../../lib/cloudinary';

export default async function handler(req, res) {
  const { id } = req.query;

  try {
    await connectDB();

    if (req.method === 'GET') {
      const image = await Image.findById(id);
      if (!image) {
        return res.status(404).json({ error: 'Image not found' });
      }

      image.views += 1;
      await image.save();

      return res.status(200).json({
        success: true,
        image,
      });
    }

    if (req.method === 'DELETE') {
      const image = await Image.findById(id);
      if (!image) {
        return res.status(404).json({ error: 'Image not found' });
      }

      await deleteFromCloudinary(image.publicId);
      await image.deleteOne();

      return res.status(200).json({
        success: true,
        message: 'Image deleted successfully',
      });
    }

    if (req.method === 'POST') {
      const { action } = req.body;

      if (action === 'like') {
        const image = await Image.findById(id);
        if (!image) {
          return res.status(404).json({ error: 'Image not found' });
        }

        image.likes += 1;
        await image.save();

        return res.status(200).json({
          success: true,
          likes: image.likes,
        });
      }

      return res.status(400).json({ error: 'Invalid action' });
    }

    return res.status(405).json({ error: 'Method not allowed' });
  } catch (error) {
    console.error('Image detail error:', error);
    res.status(500).json({ error: 'Failed to process request' });
  }
}

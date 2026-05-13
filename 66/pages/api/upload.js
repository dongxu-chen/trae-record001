import { IncomingForm } from 'formidable';
import { getServerSession } from 'next-auth/next';
import { Image, connectDB } from '../../lib/db';
import { uploadToCloudinary } from '../../lib/cloudinary';
import { invalidateTrendingCache } from '../../lib/redis';

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const session = await getServerSession(req, res);
    if (!session || !session.user?.id) {
      return res.status(401).json({
        success: false,
        error: '请先登录后再上传图片',
      });
    }

    await connectDB();

    const form = new IncomingForm({
      keepExtensions: true,
      maxFileSize: 10 * 1024 * 1024,
    });

    const [fields, files] = await new Promise((resolve, reject) => {
      form.parse(req, (err, fields, files) => {
        if (err) reject(err);
        else resolve([fields, files]);
      });
    });

    const imageFile = files.image?.[0] || files.image;
    if (!imageFile) {
      return res.status(400).json({ error: 'No image file provided' });
    }

    const { url, publicId } = await uploadToCloudinary(imageFile.filepath);

    const tags = fields.tags?.[0] || fields.tags || '';
    const tagsArray = tags
      ? tags.split(',').map((tag) => tag.trim()).filter(Boolean)
      : [];

    const image = new Image({
      userId: session.user.id,
      title: fields.title?.[0] || fields.title || 'Untitled',
      description: fields.description?.[0] || fields.description || '',
      cloudinaryUrl: url,
      publicId: publicId,
      tags: tagsArray,
    });

    const savedImage = await image.save();

    await invalidateTrendingCache();

    res.status(200).json({
      success: true,
      image: savedImage,
    });
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ error: 'Failed to upload image' });
  }
}

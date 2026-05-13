import mongoose from 'mongoose';

const UserSchema = new mongoose.Schema(
  {
    username: {
      type: String,
      required: true,
      unique: true,
      trim: true,
      lowercase: true,
    },
    name: {
      type: String,
      required: true,
      trim: true,
    },
    email: {
      type: String,
      trim: true,
      lowercase: true,
      default: null,
    },
    password: {
      type: String,
      required: true,
    },
    avatar: {
      type: String,
      default: null,
    },
  },
  {
    timestamps: true,
  }
);

UserSchema.index({ username: 1 }, { unique: true });

const ImageSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      default: null,
    },
    title: {
      type: String,
      required: true,
      trim: true,
    },
    description: {
      type: String,
      trim: true,
    },
    cloudinaryUrl: {
      type: String,
      required: true,
    },
    publicId: {
      type: String,
      required: true,
    },
    tags: {
      type: [String],
      default: [],
    },
    views: {
      type: Number,
      default: 0,
    },
    likes: {
      type: Number,
      default: 0,
    },
  },
  {
    timestamps: true,
  }
);

ImageSchema.index({ createdAt: -1, _id: -1 });
ImageSchema.index({ tags: 1, createdAt: -1, _id: -1 });
ImageSchema.index({ userId: 1, createdAt: -1, _id: -1 });
ImageSchema.index({ likes: -1, createdAt: -1 });

const LikeSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'User',
      required: true,
    },
    imageId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: 'Image',
      required: true,
    },
  },
  {
    timestamps: true,
  }
);

LikeSchema.index({ userId: 1, imageId: 1 }, { unique: true });
LikeSchema.index({ imageId: 1 });

let User, Image, Like;

try {
  User = mongoose.model('User');
} catch (error) {
  User = mongoose.model('User', UserSchema);
}

try {
  Image = mongoose.model('Image');
} catch (error) {
  Image = mongoose.model('Image', ImageSchema);
}

try {
  Like = mongoose.model('Like');
} catch (error) {
  Like = mongoose.model('Like', LikeSchema);
}

const connectDB = async () => {
  if (mongoose.connections[0].readyState) {
    return;
  }

  try {
    await mongoose.connect(process.env.MONGODB_URI, {
      dbName: 'image_gallery',
      serverSelectionTimeoutMS: 30000,
      socketTimeoutMS: 60000,
    });
    console.log('MongoDB connected successfully');
  } catch (error) {
    console.error('MongoDB connection error:', error);
    throw new Error('Failed to connect to MongoDB');
  }
};

const getImagesPaginated = async (options = {}) => {
  const {
    limit = 12,
    cursor = null,
    direction = 'next',
    tag = null,
  } = options;

  const query = tag ? { tags: { $in: [tag] } } : {};
  const findQuery = { ...query };

  if (cursor) {
    const [createdAt, id] = cursor.split('|');
    const cursorDate = new Date(parseInt(createdAt));
    const cursorId = mongoose.Types.ObjectId(id);

    if (direction === 'next') {
      findQuery.$or = [
        { createdAt: { $lt: cursorDate } },
        { createdAt: cursorDate, _id: { $lt: cursorId } },
      ];
    } else {
      findQuery.$or = [
        { createdAt: { $gt: cursorDate } },
        { createdAt: cursorDate, _id: { $gt: cursorId } },
      ];
    }
  }

  const sortOrder = direction === 'prev' ? { createdAt: 1, _id: 1 } : { createdAt: -1, _id: -1 };

  const images = await Image.find(findQuery)
    .sort(sortOrder)
    .limit(limit + 1)
    .lean();

  const hasMore = images.length > limit;
  const resultImages = hasMore ? images.slice(0, limit) : images;
  const orderedImages = direction === 'prev' ? resultImages.reverse() : resultImages;

  const createCursor = (image) => {
    return `${image.createdAt.getTime()}|${image._id.toString()}`;
  };

  return {
    images: orderedImages,
    pagination: {
      hasNext: direction === 'next' ? hasMore : cursor !== null,
      hasPrev: direction === 'prev' ? hasMore : cursor !== null,
      nextCursor:
        direction === 'next' && hasMore
          ? createCursor(resultImages[resultImages.length - 1])
          : null,
      prevCursor:
        direction === 'prev' && hasMore
          ? createCursor(resultImages[0])
          : null,
      firstCursor: orderedImages.length > 0 ? createCursor(orderedImages[0]) : null,
      lastCursor: orderedImages.length > 0 ? createCursor(orderedImages[orderedImages.length - 1]) : null,
    },
  };
};

const getUserImagesPaginated = async (userId, options = {}) => {
  const { limit = 12, cursor = null, direction = 'next' } = options;

  const findQuery = { userId };

  if (cursor) {
    const [createdAt, id] = cursor.split('|');
    const cursorDate = new Date(parseInt(createdAt));
    const cursorId = mongoose.Types.ObjectId(id);

    if (direction === 'next') {
      findQuery.$or = [
        { createdAt: { $lt: cursorDate } },
        { createdAt: cursorDate, _id: { $lt: cursorId } },
      ];
    } else {
      findQuery.$or = [
        { createdAt: { $gt: cursorDate } },
        { createdAt: cursorDate, _id: { $gt: cursorId } },
      ];
    }
  }

  const sortOrder = direction === 'prev' ? { createdAt: 1, _id: 1 } : { createdAt: -1, _id: -1 };

  const images = await Image.find(findQuery)
    .sort(sortOrder)
    .limit(limit + 1)
    .lean();

  const hasMore = images.length > limit;
  const resultImages = hasMore ? images.slice(0, limit) : images;
  const orderedImages = direction === 'prev' ? resultImages.reverse() : resultImages;

  const createCursor = (image) => {
    return `${image.createdAt.getTime()}|${image._id.toString()}`;
  };

  return {
    images: orderedImages,
    pagination: {
      hasNext: direction === 'next' ? hasMore : cursor !== null,
      hasPrev: direction === 'prev' ? hasMore : cursor !== null,
      nextCursor:
        direction === 'next' && hasMore
          ? createCursor(resultImages[resultImages.length - 1])
          : null,
      prevCursor:
        direction === 'prev' && hasMore
          ? createCursor(resultImages[0])
          : null,
      firstCursor: orderedImages.length > 0 ? createCursor(orderedImages[0]) : null,
      lastCursor: orderedImages.length > 0 ? createCursor(orderedImages[orderedImages.length - 1]) : null,
    },
  };
};

const getTrendingImages = async (limit = 10) => {
  return Image.find()
    .sort({ likes: -1, createdAt: -1 })
    .limit(limit)
    .lean();
};

export { User, Image, Like, connectDB, getImagesPaginated, getUserImagesPaginated, getTrendingImages };


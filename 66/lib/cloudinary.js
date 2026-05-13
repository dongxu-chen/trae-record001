import { v2 as cloudinary } from 'cloudinary';

const cloudinaryConfig = {
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
};

cloudinary.config(cloudinaryConfig);

const getFreshCloudinary = () => {
  cloudinary.config(cloudinaryConfig);
  return cloudinary;
};

const isSignatureExpiredError = (error) => {
  if (!error) return false;
  const errorMessage = (error.message || error.toString()).toLowerCase();
  return (
    errorMessage.includes('signature') &&
    (errorMessage.includes('expired') ||
      errorMessage.includes('invalid') ||
      errorMessage.includes('authentication'))
  );
};

const isRateLimitError = (error) => {
  if (!error) return false;
  const errorMessage = (error.message || error.toString()).toLowerCase();
  return (
    error.http_code === 429 ||
    errorMessage.includes('rate limit') ||
    errorMessage.includes('too many requests')
  );
};

export const uploadToCloudinary = async (
  filePath,
  options = {},
  maxRetries = 3
) => {
  const cld = getFreshCloudinary();
  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const result = await cld.uploader.upload(filePath, {
        folder: 'image-gallery',
        timeout: 120000,
        ...options,
      });
      return {
        url: result.secure_url,
        publicId: result.public_id,
      };
    } catch (error) {
      lastError = error;
      console.error(`Cloudinary upload attempt ${attempt + 1} failed:`, error);

      if (attempt < maxRetries) {
        if (isSignatureExpiredError(error)) {
          console.log('Signature expired, refreshing and retrying...');
          getFreshCloudinary();
          await new Promise((resolve) => setTimeout(resolve, 1000));
          continue;
        }

        if (isRateLimitError(error)) {
          const delay = Math.min(2000 * Math.pow(2, attempt), 10000);
          console.log(`Rate limited, retrying in ${delay}ms...`);
          await new Promise((resolve) => setTimeout(resolve, delay));
          continue;
        }

        if (error.message && error.message.includes('timeout')) {
          const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
          console.log(`Timeout, retrying in ${delay}ms...`);
          await new Promise((resolve) => setTimeout(resolve, delay));
          continue;
        }

        throw error;
      }
    }
  }

  throw lastError || new Error('Failed to upload image to Cloudinary');
};

export const deleteFromCloudinary = async (publicId, maxRetries = 2) => {
  const cld = getFreshCloudinary();
  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      await cld.uploader.destroy(publicId, {
        timeout: 60000,
      });
      return;
    } catch (error) {
      lastError = error;
      console.error(
        `Cloudinary delete attempt ${attempt + 1} failed:`,
        error
      );

      if (attempt < maxRetries) {
        if (isSignatureExpiredError(error)) {
          console.log('Signature expired, refreshing and retrying...');
          getFreshCloudinary();
          await new Promise((resolve) => setTimeout(resolve, 500));
          continue;
        }

        if (isRateLimitError(error)) {
          const delay = Math.min(2000 * Math.pow(2, attempt), 8000);
          await new Promise((resolve) => setTimeout(resolve, delay));
          continue;
        }

        throw error;
      }
    }
  }

  throw lastError || new Error('Failed to delete image from Cloudinary');
};

export default cloudinary;

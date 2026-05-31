import { type Request, type Response, type NextFunction } from 'express';
import multer from 'multer';

export const errorHandler = (
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction,
): void => {
  console.error('Error:', error);

  if (error instanceof multer.MulterError) {
    if (error.code === 'LIMIT_FILE_SIZE') {
      res.status(400).json({
        success: false,
        error: 'File too large. Maximum size is 10MB',
      });
      return;
    }
    res.status(400).json({
      success: false,
      error: `File upload error: ${error.message}`,
    });
    return;
  }

  if (error.message.includes('Invalid file type')) {
    res.status(400).json({
      success: false,
      error: error.message,
    });
    return;
  }

  res.status(500).json({
    success: false,
    error: 'Server internal error',
    message: error.message,
  });
};

export const notFoundHandler = (
  req: Request,
  res: Response,
): void => {
  res.status(404).json({
    success: false,
    error: 'API not found',
    path: req.path,
  });
};

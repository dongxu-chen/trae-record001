import multer from 'multer';

const FILE_SIZE_LIMIT = 10 * 1024 * 1024;

const ALLOWED_EXTENSIONS = [
  '.pdf',
  '.xml',
  '.p7s',
  '.pkcs7',
  '.pem',
  '.der',
];

const ALLOWED_MIME_TYPES = [
  'application/pdf',
  'application/xml',
  'text/xml',
  'application/pkcs7-signature',
  'application/pkcs7-mime',
  'application/x-pkcs7-signature',
  'application/x-pkcs7-certificates',
  'application/x-pem-file',
  'application/x-x509-ca-cert',
  'application/pkix-cert',
  'application/octet-stream',
];

const storage = multer.memoryStorage();

const fileFilter = (
  req: Express.Request,
  file: Express.Multer.File,
  cb: multer.FileFilterCallback,
): void => {
  const originalName = file.originalname.toLowerCase();
  const hasValidExtension = ALLOWED_EXTENSIONS.some((ext) =>
    originalName.endsWith(ext),
  );
  const hasValidMimeType = ALLOWED_MIME_TYPES.includes(file.mimetype);

  if (hasValidExtension || hasValidMimeType) {
    cb(null, true);
  } else {
    cb(
      new Error(
        `Invalid file type. Allowed types: ${ALLOWED_EXTENSIONS.join(', ')}`,
      ),
    );
  }
};

export const upload = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: FILE_SIZE_LIMIT,
  },
});

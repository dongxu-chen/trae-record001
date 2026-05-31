import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Image, X } from 'lucide-react';

function ImageUpload({ onImageUpload, currentImage, type = 'content' }) {
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onImageUpload(acceptedFiles[0]);
    }
  }, [onImageUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.webp']
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
  });

  const handleRemove = (e) => {
    e.stopPropagation();
    onImageUpload(null);
  };

  if (currentImage) {
    return (
      <div className="relative">
        <div className="relative w-full aspect-square rounded-xl overflow-hidden bg-gray-800/50">
          <img
            src={currentImage}
            alt="Uploaded"
            className="w-full h-full object-contain"
          />
        </div>
        <button
          onClick={handleRemove}
          className="absolute top-2 right-2 p-2 bg-red-500/80 hover:bg-red-500 rounded-full text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={`drop-zone cursor-pointer w-full aspect-square rounded-xl border-2 border-dashed flex flex-col items-center justify-center transition-all ${
        isDragActive
          ? 'border-primary-400 bg-primary-400/10'
          : 'border-gray-600 hover:border-gray-500 bg-gray-800/30'
      }`}
    >
      <input {...getInputProps()} />
      <div className="text-center p-6">
        <div className={`mx-auto w-16 h-16 rounded-full flex items-center justify-center mb-4 ${
          isDragActive ? 'bg-primary-400/20' : 'bg-gray-700/50'
        }`}>
          {isDragActive ? (
            <Image className="w-8 h-8 text-primary-400" />
          ) : (
            <Upload className="w-8 h-8 text-gray-400" />
          )}
        </div>
        <p className="text-gray-300 font-medium mb-2">
          {isDragActive ? '释放以上传图片' : '点击或拖拽上传图片'}
        </p>
        <p className="text-gray-500 text-sm">
          支持 JPG, PNG, WebP (最大 10MB)
        </p>
      </div>
    </div>
  );
}

export default ImageUpload;

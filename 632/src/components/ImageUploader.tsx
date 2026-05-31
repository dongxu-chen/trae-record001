import { useState, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import { Upload, Image as ImageIcon, X, AlertCircle } from 'lucide-react';
import { useImageStore } from '../store/useImageStore';

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];

export function ImageUploader() {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const addImage = useImageStore((state) => state.addImage);

  const validateFile = (file: File): boolean => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError(`不支持的文件格式: ${file.name}。请上传 PNG, JPG 或 WebP 格式的图片。`);
      return false;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError(`文件过大: ${file.name}。最大支持 10MB。`);
      return false;
    }
    return true;
  };

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    
    setError(null);
    const validFiles: File[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (validateFile(file)) {
        validFiles.push(file);
      }
    }

    for (const file of validFiles) {
      try {
        await addImage(file);
      } catch (e) {
        setError(`处理文件失败: ${file.name}`);
      }
    }
  }, [addImage]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full">
      <motion.div
        className={`drop-zone border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-300 ${
          isDragging
            ? 'border-neon-blue-400 bg-neon-blue-500/10 animate-pulse-glow'
            : 'border-deep-space-600 hover:border-neon-blue-400/50 hover:bg-deep-space-800/50'
        }`}
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg,image/webp"
          multiple
          className="hidden"
          onChange={handleFileChange}
        />
        
        <div className="flex flex-col items-center gap-4">
          <motion.div
            className="w-16 h-16 rounded-full bg-deep-space-700 flex items-center justify-center"
            animate={isDragging ? { y: [0, -5, 0] } : {}}
            transition={{ duration: 0.5, repeat: isDragging ? Infinity : 0 }}
          >
            {isDragging ? (
              <ImageIcon className="w-8 h-8 text-neon-blue-400" />
            ) : (
              <Upload className="w-8 h-8 text-deep-space-400" />
            )}
          </motion.div>
          
          <div>
            <p className="text-lg font-semibold text-deep-space-200">
              {isDragging ? '释放以上传图片' : '拖拽图片到此处'}
            </p>
            <p className="text-sm text-deep-space-400 mt-1">
              或 <span className="text-neon-blue-400 hover:text-neon-blue-300">点击选择文件</span>
            </p>
            <p className="text-xs text-deep-space-500 mt-2">
              支持 PNG, JPG, WebP • 最大 10MB • 可多文件上传
            </p>
          </div>
        </div>
      </motion.div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-2"
        >
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-red-400">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-deep-space-400 hover:text-red-400 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </motion.div>
      )}
    </div>
  );
}

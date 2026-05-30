import { useRef, useCallback, useState } from 'react';
import { Upload, Image as ImageIcon, X, Plus } from 'lucide-react';
import useFilterStore from '@/store/filterStore';
import { cn } from '@/lib/utils';

interface ImageUploaderProps {
  className?: string;
}

export default function ImageUploader({ className = '' }: ImageUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const { images, selectedImageId, addImage, removeImage, selectImage } =
    useFilterStore();

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files) return;
      Array.from(files).forEach((file) => {
        if (file.type.startsWith('image/')) {
          addImage(file);
        }
      });
    },
    [addImage]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className={`glass-panel rounded-xl p-4 ${className}`}>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
        className={cn(
          'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all duration-200',
          isDragging
            ? 'border-neon-cyan bg-neon-cyan/5'
            : 'border-surface-border hover:border-neon-cyan/50 hover:bg-surface-hover/50'
        )}
      >
        <div
          className={cn(
            'w-12 h-12 mx-auto mb-3 rounded-full flex items-center justify-center transition-colors',
            isDragging ? 'bg-neon-cyan/20' : 'bg-surface-card'
          )}
        >
          <Upload
            className={cn(
              'transition-colors',
              isDragging ? 'text-neon-cyan' : 'text-gray-400'
            )}
            size={24}
          />
        </div>
        <p className="text-sm font-medium">
          {isDragging ? '释放以上传' : '拖拽图片到此处'}
        </p>
        <p className="text-xs text-gray-500 mt-1">或点击选择文件</p>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => handleFiles(e.target.files)}
          className="hidden"
        />
      </div>

      {images.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
            已上传 ({images.length})
          </p>
          <div className="grid grid-cols-4 gap-2">
            {images.map((image) => (
              <div
                key={image.id}
                className={cn(
                  'relative aspect-square rounded-lg overflow-hidden group cursor-pointer transition-all duration-200',
                  selectedImageId === image.id
                    ? 'ring-2 ring-neon-cyan ring-offset-2 ring-offset-surface-panel'
                    : 'ring-1 ring-surface-border hover:ring-neon-cyan/50'
                )}
                onClick={() => selectImage(image.id)}
              >
                <img
                  src={image.src}
                  alt={image.name}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <ImageIcon size={20} className="text-white" />
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeImage(image.id);
                  }}
                  className="absolute top-1 right-1 w-5 h-5 bg-red-500/80 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500"
                >
                  <X size={12} className="text-white" />
                </button>
              </div>
            ))}
            {images.length < 8 && (
              <button
                onClick={handleClick}
                className="aspect-square rounded-lg border-2 border-dashed border-surface-border hover:border-neon-cyan/50 flex items-center justify-center transition-colors"
              >
                <Plus size={20} className="text-gray-500" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

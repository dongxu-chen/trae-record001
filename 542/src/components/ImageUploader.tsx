import { Upload, ClipboardPaste, Image } from 'lucide-react';
import { useCallback, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

interface ImageUploaderProps {
  onImageLoad: (file: File) => void;
  hasImage: boolean;
}

export default function ImageUploader({ onImageLoad, hasImage }: ImageUploaderProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      if (file.type.startsWith('image/')) {
        onImageLoad(file);
      }
    },
    [onImageLoad]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handlePaste = useCallback(() => {
    navigator.clipboard.read().then(async (items) => {
      for (const item of items) {
        for (const type of item.types) {
          if (type.startsWith('image/')) {
            const blob = await item.getType(type);
            const file = new File([blob], 'pasted-image.png', { type });
            handleFile(file);
            return;
          }
        }
      }
    }).catch(() => {});
  }, [handleFile]);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  if (hasImage) return null;

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      className={cn(
        'border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 cursor-pointer',
        'hover:border-[#00d4aa] hover:bg-[#00d4aa]/5',
        isDragOver
          ? 'border-[#00d4aa] bg-[#00d4aa]/10 scale-[1.02]'
          : 'border-zinc-700 bg-zinc-900/50'
      )}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleInputChange}
        className="hidden"
      />

      <div className="flex flex-col items-center gap-4">
        <div className="w-16 h-16 rounded-2xl bg-zinc-800 flex items-center justify-center">
          <Upload className="w-8 h-8 text-[#00d4aa]" />
        </div>

        <div>
          <p className="text-lg font-medium text-zinc-200">
            拖拽图片到此处上传
          </p>
          <p className="text-sm text-zinc-500 mt-1">
            支持 PNG、JPG、WebP 格式
          </p>
        </div>

        <div className="flex gap-3 mt-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              fileInputRef.current?.click();
            }}
            className="px-4 py-2 rounded-lg bg-[#00d4aa] text-zinc-900 font-medium text-sm hover:bg-[#00d4aa]/90 transition-colors flex items-center gap-2"
          >
            <Image className="w-4 h-4" />
            选择文件
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handlePaste();
            }}
            className="px-4 py-2 rounded-lg border border-zinc-700 text-zinc-300 text-sm hover:border-[#00d4aa] hover:text-[#00d4aa] transition-colors flex items-center gap-2"
          >
            <ClipboardPaste className="w-4 h-4" />
            从剪贴板粘贴
          </button>
        </div>
      </div>
    </div>
  );
}

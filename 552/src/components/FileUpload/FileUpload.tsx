import { useState, useCallback, useRef } from 'react';
import { Upload, FileText, X } from 'lucide-react';
import { useVerificationStore } from '@/store/verificationStore';
import { cn } from '@/lib/utils';

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ACCEPTED_TYPES = [
  'application/pdf',
  'application/xml',
  'text/xml',
  'application/pkcs7-mime',
  'application/pkcs7-signature',
  'application/x-pkcs7-signature',
  'application/pkcs7',
  '.pdf',
  '.xml',
  '.p7s',
  '.p7m',
  '.pkcs7',
];

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const getFileIcon = (type: string) => {
  return FileText;
};

interface FileUploadProps {
  className?: string;
}

export default function FileUpload({ className }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const { currentFile, setCurrentFile, setFileInfo } = useVerificationStore();

  const validateFile = useCallback((file: File): boolean => {
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    const isValidType = ACCEPTED_TYPES.includes(file.type) || ACCEPTED_TYPES.includes(fileExtension);
    
    if (!isValidType) {
      setError('不支持的文件格式，请上传 PDF、XML 或 PKCS#7 文件');
      return false;
    }
    
    if (file.size > MAX_FILE_SIZE) {
      setError('文件大小超过限制，最大支持 10MB');
      return false;
    }
    
    setError(null);
    return true;
  }, []);

  const handleFile = useCallback((file: File) => {
    if (validateFile(file)) {
      setCurrentFile(file);
      setFileInfo({
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified,
      });
    }
  }, [validateFile, setCurrentFile, setFileInfo]);

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
    
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  }, [handleFile]);

  const handleClick = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  }, [handleFile]);

  const handleRemoveFile = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrentFile(null);
    setFileInfo(null);
    setError(null);
  }, [setCurrentFile, setFileInfo]);

  const FileIcon = currentFile ? getFileIcon(currentFile.type) : FileText;

  return (
    <div className={cn('w-full', className)}>
      <div
        className={cn(
          'relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-all duration-300 cursor-pointer min-h-[200px]',
          isDragging
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-700 hover:border-blue-400 hover:bg-gray-50 dark:hover:bg-gray-800/50',
          currentFile && 'border-green-500 bg-green-50 dark:bg-green-900/20'
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.xml,.p7s,.p7m,.pkcs7,application/pdf,application/xml,text/xml,application/pkcs7-mime,application/pkcs7-signature"
          onChange={handleInputChange}
          className="hidden"
        />
        
        {currentFile ? (
          <div className="flex flex-col items-center gap-4 w-full">
            <div className="flex items-center gap-4 w-full max-w-md p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
              <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <FileIcon className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
                  {currentFile.name}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {formatFileSize(currentFile.size)}
                </p>
              </div>
              <button
                onClick={handleRemoveFile}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors"
              >
                <X className="w-5 h-5 text-gray-500 hover:text-red-500" />
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className={cn(
              'p-4 rounded-full mb-4 transition-colors',
              isDragging ? 'bg-blue-100 dark:bg-blue-900/30' : 'bg-gray-100 dark:bg-gray-800'
            )}>
              <Upload className={cn(
                'w-10 h-10 transition-colors',
                isDragging ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'
              )} />
            </div>
            <p className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-1">
              {isDragging ? '释放以上传文件' : '拖拽文件到此处或点击上传'}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              支持 PDF、XML、PKCS#7 格式，最大 10MB
            </p>
          </>
        )}
      </div>
      
      {error && (
        <p className="mt-2 text-sm text-red-500">{error}</p>
      )}
    </div>
  );
}

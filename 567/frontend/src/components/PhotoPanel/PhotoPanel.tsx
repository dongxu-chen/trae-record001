import { useRef, useState, useCallback } from 'react';
import { Upload, X, Image, MapPin, Clock, Camera, CheckSquare, Square, Trash2 } from 'lucide-react';
import { useStore } from '@/store/useStore';
import { parseExifData, generateThumbnail, generateId } from '@/utils/exif';
import { Photo } from '@/types';
import { getPhotoEffectiveGPS } from '@/utils/export';

export default function PhotoPanel() {
  const { 
    photos, 
    selectedPhotoId, 
    addPhotos, 
    removePhoto, 
    clearPhotos,
    selectPhoto,
    togglePhotoSelection,
    selectAllPhotos,
  } = useStore();
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleFileSelect = useCallback(async (files: FileList) => {
    setIsLoading(true);
    const imageFiles = Array.from(files).filter(f => f.type.startsWith('image/'));
    
    const newPhotos: Photo[] = [];
    
    for (const file of imageFiles) {
      try {
        const [exifData, thumbnail] = await Promise.all([
          parseExifData(file),
          generateThumbnail(file),
        ]);
        
        newPhotos.push({
          id: generateId(),
          name: file.name,
          file,
          thumbnail,
          originalUrl: URL.createObjectURL(file),
          exifData,
          originalGps: exifData.gps,
          matched: false,
          selected: false,
        });
      } catch (error) {
        console.error(`处理照片 ${file.name} 失败:`, error);
      }
    }
    
    addPhotos(newPhotos);
    setIsLoading(false);
  }, [addPhotos]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files) {
      handleFileSelect(e.dataTransfer.files);
    }
  }, [handleFileSelect]);

  const allSelected = photos.length > 0 && photos.every(p => p.selected);

  const selectedPhoto = photos.find(p => p.id === selectedPhotoId);

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <Image size={20} />
            照片
            <span className="text-sm font-normal text-gray-500">({photos.length})</span>
          </h2>
          {photos.length > 0 && (
            <button
              onClick={() => clearPhotos()}
              className="text-gray-400 hover:text-red-500 transition-colors"
              title="清空所有照片"
            >
              <Trash2 size={18} />
            </button>
          )}
        </div>
        
        <div
          className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-all ${
            dragOver 
              ? 'border-accent-500 bg-accent-500/10' 
              : 'border-gray-300 hover:border-gray-400 bg-gray-50'
          }`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <Upload size={24} className="mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-600">
            拖放照片到这里或点击上传
          </p>
          <p className="text-xs text-gray-400 mt-1">支持 JPG, PNG, WEBP</p>
        </div>
        
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*"
          className="hidden"
          onChange={(e) => e.target.files && handleFileSelect(e.target.files)}
        />
      </div>
      
      {photos.length > 0 && (
        <div className="px-4 py-2 border-b border-gray-100 flex items-center gap-2">
          <button
            onClick={() => selectAllPhotos(!allSelected)}
            className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-800"
          >
            {allSelected ? <CheckSquare size={16} /> : <Square size={16} />}
            全选
          </button>
          <span className="text-xs text-gray-400">
            已选 {photos.filter(p => p.selected).length} 张
          </span>
        </div>
      )}
      
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {isLoading ? (
          <div className="p-4 text-center text-gray-500">
            <div className="animate-spin w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full mx-auto mb-2" />
            正在处理照片...
          </div>
        ) : photos.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <Image size={48} className="mx-auto mb-2 opacity-50" />
            <p>暂无照片</p>
          </div>
        ) : (
          <div className="p-2">
            {photos.map(photo => {
              const gps = getPhotoEffectiveGPS(photo);
              const isSelected = photo.id === selectedPhotoId;
              
              return (
                <div
                  key={photo.id}
                  className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all mb-1 ${
                    isSelected 
                      ? 'bg-accent-500/10 border border-accent-500/30' 
                      : 'hover:bg-gray-100 border border-transparent'
                  }`}
                  onClick={() => selectPhoto(photo.id)}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      togglePhotoSelection(photo.id);
                    }}
                    className="flex-shrink-0 text-gray-400 hover:text-gray-600"
                  >
                    {photo.selected ? <CheckSquare size={18} /> : <Square size={18} />}
                  </button>
                  
                  <img
                    src={photo.thumbnail}
                    alt={photo.name}
                    className="w-12 h-12 object-cover rounded flex-shrink-0"
                  />
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">
                      {photo.name}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                      {gps ? (
                        <span className="flex items-center gap-1 text-green-600">
                          <MapPin size={12} />
                          已标记
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-orange-500">
                          <MapPin size={12} />
                          未标记
                        </span>
                      )}
                      {photo.exifData.dateTimeOriginal && (
                        <span className="flex items-center gap-1">
                          <Clock size={12} />
                          {photo.exifData.dateTimeOriginal.toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removePhoto(photo.id);
                    }}
                    className="flex-shrink-0 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <X size={16} />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      {selectedPhoto && (
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">照片详情</h3>
          <img
            src={selectedPhoto.originalUrl}
            alt={selectedPhoto.name}
            className="w-full h-32 object-cover rounded mb-2"
          />
          <div className="text-xs text-gray-600 space-y-1">
            <p><span className="text-gray-400">文件名:</span> {selectedPhoto.name}</p>
            {selectedPhoto.exifData.make && selectedPhoto.exifData.model && (
              <p className="flex items-center gap-1">
                <Camera size={12} />
                {selectedPhoto.exifData.make} {selectedPhoto.exifData.model}
              </p>
            )}
            {selectedPhoto.exifData.dateTimeOriginal && (
              <p className="flex items-center gap-1">
                <Clock size={12} />
                {selectedPhoto.exifData.dateTimeOriginal.toLocaleString()}
              </p>
            )}
            {getPhotoEffectiveGPS(selectedPhoto) && (
              <p className="flex items-center gap-1 text-green-600">
                <MapPin size={12} />
                {getPhotoEffectiveGPS(selectedPhoto)!.lat.toFixed(6)}, {getPhotoEffectiveGPS(selectedPhoto)!.lng.toFixed(6)}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

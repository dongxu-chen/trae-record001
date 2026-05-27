import React, { useRef, useState } from 'react';
import { Upload, Image, HelpCircle, X, Check } from 'lucide-react';
import { useAnnotationStore } from '@/store/useAnnotationStore';
import { uploadImage, getImageData, getSAMStatus } from '@/services/api';

export const Header: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { images, currentImageId, setCurrentImage, addImage, setCanvasState } = useAnnotationStore();
  const [samStatus, setSamStatus] = useState<{ loaded: boolean; modelType: string } | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [showImageList, setShowImageList] = useState(false);

  const checkSAMStatus = async () => {
    try {
      const status = await getSAMStatus();
      setSamStatus(status);
    } catch (e) {
      setSamStatus({ loaded: false, modelType: 'unknown' });
    }
  };

  React.useEffect(() => {
    checkSAMStatus();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        const imageInfo = await uploadImage(file);
        const url = await getImageData(imageInfo.id);
        addImage({ ...imageInfo, url });
      } catch (err) {
        console.error('Failed to upload image:', err);
      }
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSelectImage = async (id: string) => {
    if (id === currentImageId) return;
    setCurrentImage(id);
    
    const url = await getImageData(id);
    const image = images.find(img => img.id === id);
    if (image && url) {
      setCanvasState({
        imageWidth: image.width,
        imageHeight: image.height,
        scale: 1,
        offsetX: 0,
        offsetY: 0,
      });
    }
    setShowImageList(false);
  };

  return (
    <header className="h-14 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-b border-slate-700 flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">✂️</span>
          </div>
          <h1 className="text-lg font-bold text-white tracking-tight">
            图像分割标注工具
          </h1>
          <span className="text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
            v1.0
          </span>
        </div>

        {samStatus && (
          <div className={`ml-4 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs
            ${samStatus.loaded 
              ? 'bg-green-500/20 text-green-400' 
              : 'bg-red-500/20 text-red-400'
            }`}>
            <div className={`w-2 h-2 rounded-full ${samStatus.loaded ? 'bg-green-400' : 'bg-red-400'}`} />
            SAM {samStatus.loaded ? '已就绪' : '未加载'}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <div className="relative">
          <button
            onClick={() => setShowImageList(!showImageList)}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors"
          >
            <Image size={16} />
            图像列表
            <span className="bg-slate-600 px-1.5 py-0.5 rounded text-xs">
              {images.length}
            </span>
          </button>

          {showImageList && images.length > 0 && (
            <div className="absolute right-0 top-full mt-1 w-64 bg-slate-800 border border-slate-700 rounded-lg shadow-xl overflow-hidden z-50 max-h-80 overflow-y-auto">
              {images.map((img) => (
                <div
                  key={img.id}
                  onClick={() => handleSelectImage(img.id)}
                  className={`flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors
                    ${currentImageId === img.id 
                      ? 'bg-cyan-500/20 text-cyan-400' 
                      : 'hover:bg-slate-700 text-white'
                    }`}
                >
                  {img.url && (
                    <img
                      src={img.url}
                      alt={img.filename}
                      className="w-10 h-10 object-cover rounded"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm truncate">{img.filename}</div>
                    <div className="text-xs text-slate-400">
                      {img.width} × {img.height}
                    </div>
                  </div>
                  {currentImageId === img.id && (
                    <Check size={16} className="text-cyan-400 flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileUpload}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-sm rounded-lg transition-colors shadow-lg shadow-cyan-500/20"
        >
          <Upload size={16} />
          上传图像
        </button>

        <div className="relative">
          <button
            onClick={() => setShowHelp(!showHelp)}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
          >
            <HelpCircle size={20} />
          </button>

          {showHelp && (
            <div className="absolute right-0 top-full mt-1 w-80 bg-slate-800 border border-slate-700 rounded-lg shadow-xl p-4 z-50">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-white font-medium">快捷键</h3>
                <button
                  onClick={() => setShowHelp(false)}
                  className="text-slate-400 hover:text-white"
                >
                  <X size={16} />
                </button>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">选择工具</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">V</kbd>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">多边形工具</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">P</kbd>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">点工具</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">O</kbd>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">矩形工具</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">R</kbd>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">画笔工具</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">B</kbd>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">SAM 工具</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">S</kbd>
                </div>
                <div className="h-px bg-slate-700 my-2" />
                <div className="flex justify-between">
                  <span className="text-slate-400">撤销</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">Ctrl+Z</kbd>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">重做</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">Ctrl+Y</kbd>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">平移画布</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">Space</kbd>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">缩放画布</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">滚轮</kbd>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">取消当前操作</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">Esc</kbd>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">右键取消多边形</span>
                  <kbd className="px-2 py-0.5 bg-slate-700 rounded text-white text-xs">右键</kbd>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {showImageList && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowImageList(false)}
        />
      )}
      {showHelp && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowHelp(false)}
        />
      )}
    </header>
  );
};

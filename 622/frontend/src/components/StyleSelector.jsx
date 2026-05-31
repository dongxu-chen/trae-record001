import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, Check, Palette } from 'lucide-react';

const styleColors = {
  vangogh: 'from-yellow-500 to-orange-500',
  picasso: 'from-blue-500 to-purple-500',
  monet: 'from-green-400 to-teal-500',
  kanagawa: 'from-blue-400 to-indigo-500',
  cyberpunk: 'from-pink-500 to-purple-500',
  watercolor: 'from-cyan-400 to-blue-500',
  oil_painting: 'from-amber-500 to-red-500',
  sketch: 'from-gray-400 to-gray-600',
};

function StyleSelector({ styles, selectedStyle, onStyleSelect, customStyleImage, onCustomStyleUpload }) {
  const [activeTab, setActiveTab] = useState('presets');

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onCustomStyleUpload(acceptedFiles[0]);
    }
  }, [onCustomStyleUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.webp']
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
  });

  return (
    <div>
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('presets')}
          className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'presets'
              ? 'bg-primary-500/20 text-primary-400'
              : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50'
          }`}
        >
          风格预设
        </button>
        <button
          onClick={() => setActiveTab('custom')}
          className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'custom'
              ? 'bg-primary-500/20 text-primary-400'
              : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50'
          }`}
        >
          自定义风格
        </button>
      </div>

      {activeTab === 'presets' && (
        <div className="grid grid-cols-2 gap-3 max-h-80 overflow-y-auto pr-1">
          {styles.map((style) => (
            <button
              key={style.id}
              onClick={() => onStyleSelect(style)}
              className={`style-card relative p-3 rounded-xl text-left transition-all ${
                selectedStyle?.id === style.id
                  ? 'ring-2 ring-primary-400 bg-primary-500/10'
                  : 'bg-gray-800/50 hover:bg-gray-700/50'
              }`}
            >
              <div className={`w-full aspect-video rounded-lg bg-gradient-to-br ${styleColors[style.id] || 'from-gray-500 to-gray-700'} mb-2 flex items-center justify-center`}>
                <Palette className="w-6 h-6 text-white/70" />
              </div>
              <p className="text-white text-sm font-medium truncate">{style.name}</p>
              <p className="text-gray-500 text-xs truncate">{style.description}</p>
              {selectedStyle?.id === style.id && (
                <div className="absolute top-2 right-2 w-5 h-5 bg-primary-400 rounded-full flex items-center justify-center">
                  <Check className="w-3 h-3 text-white" />
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {activeTab === 'custom' && (
        <div>
          {customStyleImage ? (
            <div className="relative">
              <div className="w-full aspect-video rounded-xl overflow-hidden">
                <img
                  src={customStyleImage.url}
                  alt="Custom style"
                  className="w-full h-full object-cover"
                />
              </div>
              <p className="text-gray-400 text-sm mt-2 text-center">已选择自定义风格</p>
            </div>
          ) : (
            <div
              {...getRootProps()}
              className={`drop-zone cursor-pointer w-full aspect-video rounded-xl border-2 border-dashed flex flex-col items-center justify-center transition-all ${
                isDragActive
                  ? 'border-primary-400 bg-primary-400/10'
                  : 'border-gray-600 hover:border-gray-500 bg-gray-800/30'
              }`}
            >
              <input {...getInputProps()} />
              <Upload className="w-10 h-10 text-gray-400 mb-3" />
              <p className="text-gray-300 text-sm">上传自定义风格图片</p>
              <p className="text-gray-500 text-xs mt-1">AI 将学习此图片的艺术风格</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default StyleSelector;

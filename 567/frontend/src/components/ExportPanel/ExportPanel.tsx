import { useState } from 'react';
import { Download, FileImage, FileText, Map, Table, Check } from 'lucide-react';
import { useStore } from '@/store/useStore';
import { exportPhotosAsZip, exportPhotosAsGPX, exportPhotosAsKML, exportPhotosAsCSV, getPhotoEffectiveGPS } from '@/utils/export';

type ExportFormat = 'jpeg' | 'gpx' | 'kml' | 'csv';

interface ExportOption {
  id: ExportFormat;
  name: string;
  description: string;
  icon: React.ReactNode;
}

const exportOptions: ExportOption[] = [
  {
    id: 'jpeg',
    name: 'JPEG 照片',
    description: '下载包含GPS信息的照片文件',
    icon: <FileImage size={20} />,
  },
  {
    id: 'gpx',
    name: 'GPX 轨迹',
    description: '导出为GPX航点文件',
    icon: <Map size={20} />,
  },
  {
    id: 'kml',
    name: 'KML 文件',
    description: '导出为Google Earth格式',
    icon: <Map size={20} />,
  },
  {
    id: 'csv',
    name: 'CSV 表格',
    description: '导出为CSV表格数据',
    icon: <Table size={20} />,
  },
];

export default function ExportPanel() {
  const { photos, getSelectedPhotos, getMatchedPhotos, privacy } = useStore();
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('jpeg');
  const [exportSelection, setExportSelection] = useState<'all' | 'selected'>('all');
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState({ current: 0, total: 0 });
  const [exportSuccess, setExportSuccess] = useState(false);

  const selectedPhotos = getSelectedPhotos();
  const matchedPhotos = getMatchedPhotos();
  
  const photosToExport = exportSelection === 'all' 
    ? matchedPhotos 
    : selectedPhotos.filter(p => getPhotoEffectiveGPS(p));

  const handleExport = async () => {
    if (photosToExport.length === 0) return;
    
    setIsExporting(true);
    setExportProgress({ current: 0, total: photosToExport.length });
    setExportSuccess(false);
    
    try {
      switch (selectedFormat) {
        case 'jpeg':
          await exportPhotosAsZip(photosToExport, (current, total) => {
            setExportProgress({ current, total });
          }, privacy);
          break;
        case 'gpx':
          exportPhotosAsGPX(photosToExport, undefined, privacy);
          break;
        case 'kml':
          exportPhotosAsKML(photosToExport, undefined, privacy);
          break;
        case 'csv':
          exportPhotosAsCSV(photosToExport, undefined, privacy);
          break;
      }
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 3000);
    } catch (error) {
      console.error('导出失败:', error);
    } finally {
      setIsExporting(false);
      setExportProgress({ current: 0, total: 0 });
    }
  };

  return (
    <div className="p-4 bg-white rounded-lg shadow-lg">
      <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2 mb-4">
        <Download size={20} />
        导出
      </h3>
      
      <div className="space-y-3 mb-4">
        {exportOptions.map(option => (
          <button
            key={option.id}
            onClick={() => setSelectedFormat(option.id)}
            className={`w-full p-3 rounded-lg border-2 text-left transition-all flex items-center gap-3 ${
              selectedFormat === option.id
                ? 'border-accent-500 bg-accent-500/5'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className={`p-2 rounded-lg ${
              selectedFormat === option.id ? 'bg-accent-500 text-white' : 'bg-gray-100 text-gray-500'
            }`}>
              {option.icon}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-800">{option.name}</p>
              <p className="text-xs text-gray-500">{option.description}</p>
            </div>
            {selectedFormat === option.id && (
              <Check size={18} className="text-accent-500" />
            )}
          </button>
        ))}
      </div>
      
      <div className="mb-4">
        <p className="text-sm font-medium text-gray-700 mb-2">导出范围</p>
        <div className="flex gap-2">
          <button
            onClick={() => setExportSelection('all')}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
              exportSelection === 'all'
                ? 'bg-accent-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            全部标记 ({matchedPhotos.length})
          </button>
          <button
            onClick={() => setExportSelection('selected')}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
              exportSelection === 'selected'
                ? 'bg-accent-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            已选择 ({photosToExport.length})
          </button>
        </div>
      </div>
      
      {isExporting && exportProgress.total > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
            <span>导出中...</span>
            <span>{exportProgress.current} / {exportProgress.total}</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-accent-500 transition-all duration-300"
              style={{ width: `${(exportProgress.current / exportProgress.total) * 100}%` }}
            />
          </div>
        </div>
      )}
      
      {exportSuccess && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700 text-sm">
          <Check size={16} />
          导出成功！
        </div>
      )}
      
      <button
        onClick={handleExport}
        disabled={photosToExport.length === 0 || isExporting}
        className="w-full py-3 bg-gradient-to-r from-warning-500 to-warning-600 text-white rounded-lg font-medium flex items-center justify-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isExporting ? (
          <>
            <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
            正在导出...
          </>
        ) : (
          <>
            <Download size={18} />
            导出 {photosToExport.length} 个文件
          </>
        )}
      </button>
      
      {privacy.enabled && privacy.applyToExport && (
        <div className="mb-4 p-3 bg-orange-50 border border-orange-200 rounded-lg flex items-center gap-2 text-orange-700 text-sm">
          🔒 导出将应用隐私保护模糊化处理
        </div>
      )}
      
      {photosToExport.length === 0 && matchedPhotos.length === 0 && (
        <p className="mt-3 text-xs text-center text-orange-500">
          暂无已标记的照片可导出
        </p>
      )}
    </div>
  );
}

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Barcode, QrCode, Check } from 'lucide-react';
import { useHistory } from '../../hooks/useHistory';
import type { ScanRecord } from '../../types';

export function ManualInput() {
  const navigate = useNavigate();
  const [content, setContent] = useState('');
  const [type, setType] = useState<'qrcode' | 'barcode'>('qrcode');
  const [saved, setSaved] = useState(false);
  
  const { addRecord } = useHistory();

  const handleSave = () => {
    if (!content.trim()) return;
    
    const record: ScanRecord = {
      id: Date.now().toString(),
      content: content.trim(),
      type: 'manual',
      format: type === 'qrcode' ? 'qr_code' : 'barcode',
      timestamp: Date.now(),
    };
    
    addRecord(record);
    setSaved(true);
    setContent('');
    
    setTimeout(() => {
      setSaved(false);
      navigate('/history');
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-[#0d1117]">
      <div className="sticky top-0 z-40 bg-[#0d1117]/95 backdrop-blur-xl border-b border-gray-800">
        <div className="px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="p-2 -ml-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-lg font-semibold text-white">手动输入</h1>
        </div>
      </div>

      <div className="p-4 max-w-lg mx-auto">
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setType('qrcode')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all ${
              type === 'qrcode'
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <QrCode className="w-5 h-5" />
            二维码
          </button>
          <button
            onClick={() => setType('barcode')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all ${
              type === 'barcode'
                ? 'bg-green-600 text-white shadow-lg shadow-green-600/30'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <Barcode className="w-5 h-5" />
            条形码
          </button>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-400 mb-2">
            输入内容
          </label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="请输入或粘贴内容..."
            rows={6}
            className="w-full px-4 py-3 bg-[#161b22] border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none font-mono text-sm"
          />
          <p className="mt-2 text-sm text-gray-500">
            {content.length} 个字符
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={!content.trim() || saved}
          className={`w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
            saved
              ? 'bg-green-600 text-white'
              : content.trim()
              ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/30'
              : 'bg-gray-700 text-gray-500 cursor-not-allowed'
          }`}
        >
          {saved ? (
            <>
              <Check className="w-5 h-5" />
              已保存
            </>
          ) : (
            <>
              保存到历史记录
            </>
          )}
        </button>
      </div>
    </div>
  );
}

import { motion } from 'framer-motion';
import { Bookmark, Trash2, Edit2, Download, QrCode } from 'lucide-react';
import { toast } from '@/components/ui/toast';
import { useAppStore } from '@/store';
import { getTypeLabel } from '@/utils/contentGenerator';
import { downloadAsPNG, generateFileName } from '@/utils/exportUtils';
import QRCodePreview from '@/components/QRCodePreview';
import type { SavedQRCode, QRStyle } from '@/types';

export default function MyQRCodes() {
  const { savedQRCodes, deleteQRCode, setFormData, setStyle, formData, style } = useAppStore();

  const handleDownload = (code: SavedQRCode) => {
    const tempCanvas = document.createElement('canvas');
    tempCanvas.id = `temp-download-${code.id}`;
    tempCanvas.style.display = 'none';
    document.body.appendChild(tempCanvas);

    import('@/utils/qrGenerator').then(async ({ generateQRCodeCanvas }) => {
      try {
        await generateQRCodeCanvas(code.content, code.style, tempCanvas.id);
        const filename = generateFileName(code.type, code.name);
        const link = document.createElement('a');
        link.download = `${filename}.png`;
        link.href = tempCanvas.toDataURL('image/png');
        link.click();
        toast.success('下载成功');
      } catch (error) {
        toast.error('下载失败');
      } finally {
        document.body.removeChild(tempCanvas);
      }
    });
  };

  const handleReuse = (code: SavedQRCode) => {
    setStyle(code.style);
    toast.success('样式已加载到生成器');
  };

  const handleDelete = (id: string) => {
    if (confirm('确定要删除这个二维码吗？')) {
      deleteQRCode(id);
      toast.success('已删除');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent mb-2">
            我的二维码
          </h1>
          <p className="text-slate-400">管理您保存的所有二维码</p>
        </motion.div>

        {savedQRCodes.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20"
          >
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-slate-800/50 flex items-center justify-center">
              <Bookmark size={40} className="text-slate-600" />
            </div>
            <h3 className="text-xl font-semibold text-slate-300 mb-2">
              暂无保存的二维码
            </h3>
            <p className="text-slate-500">
              在生成器中点击「保存」按钮即可保存二维码到这里
            </p>
          </motion.div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {savedQRCodes.map((code, index) => (
              <motion.div
                key={code.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="group rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6 hover:border-slate-700/50 transition-all"
              >
                <div className="flex justify-center mb-4">
                  <QRCodePreview
                    content={code.content}
                    style={{ ...code.style, size: 200 } as QRStyle}
                    canvasId={`qr-saved-${code.id}`}
                  />
                </div>

                <div className="mb-4">
                  <h3 className="font-semibold text-slate-200 mb-1 truncate">
                    {code.name}
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      {getTypeLabel(code.type)}
                    </span>
                    <span className="text-xs text-slate-500">
                      {new Date(code.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                <p className="text-xs text-slate-500 font-mono mb-4 truncate">
                  {code.content}
                </p>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleReuse(code)}
                    className="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm transition-colors"
                  >
                    <Edit2 size={14} />
                    复用样式
                  </button>
                  <button
                    onClick={() => handleDownload(code)}
                    className="flex items-center justify-center gap-1 px-3 py-2 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 text-sm transition-colors"
                  >
                    <Download size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(code.id)}
                    className="flex items-center justify-center gap-1 px-3 py-2 rounded-lg bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 text-sm transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

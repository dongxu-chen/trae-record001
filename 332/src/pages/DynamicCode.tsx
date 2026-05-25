import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Zap, Plus, Edit2, Trash2, ToggleLeft, ToggleRight, Link, Eye, Copy, Check, Wifi, WifiOff } from 'lucide-react';
import { toast } from '@/components/ui/toast';
import { useAppStore, useDynamicCodeStore, useAuthStore } from '@/store';
import { dynamicCodeAPI } from '@/utils/api';
import { generateContent, getTypeLabel } from '@/utils/contentGenerator';
import QRCodePreview from '@/components/QRCodePreview';
import { wsClient } from '@/utils/websocket';
import type { DynamicCode, QRCodeType, QRStyle } from '@/types';

export default function DynamicCode() {
  const { style } = useAppStore();
  const { codes, loading, setCodes, addCode, updateCode, deleteCode, setLoading, setError } = useDynamicCodeStore();
  const { isAuthenticated, user } = useAuthStore();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingCode, setEditingCode] = useState<DynamicCode | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    originalUrl: '',
    type: 'url' as QRCodeType,
  });

  const setupWebSocket = useCallback(() => {
    if (!user?.id) return;

    wsClient.connect(user.id, {
      onConnected: () => {
        setWsConnected(true);
        console.log('WebSocket已连接');
      },
      onDisconnected: () => {
        setWsConnected(false);
        console.log('WebSocket已断开');
      },
      onDynamicCodeCreated: (data) => {
        addCode(data);
        toast.info('新的动态二维码已创建');
      },
      onDynamicCodeUpdated: (data) => {
        updateCode(data.id, data);
        toast.info(`动态二维码 "${data.name}" 已更新`);
      },
      onDynamicCodeDeleted: (data) => {
        deleteCode(data.id);
        toast.info('动态二维码已被删除');
      },
      onScanUpdated: (data) => {
        const existingCode = codes.find(c => c.id === data.id);
        if (existingCode) {
          updateCode(data.id, { scanCount: data.scanCount });
        }
      },
      onError: (error) => {
        console.error('WebSocket错误:', error);
        setWsConnected(false);
      },
    });
  }, [user, codes, addCode, updateCode, deleteCode]);

  useEffect(() => {
    if (isAuthenticated() && user?.id) {
      loadCodes();
      setupWebSocket();

      return () => {
        wsClient.disconnect();
      };
    }
  }, [isAuthenticated, user?.id, setupWebSocket]);

  const loadCodes = async () => {
    setLoading(true);
    try {
      const result = await dynamicCodeAPI.list();
      if (result.success && result.data) {
        setCodes(result.data);
      }
    } catch (error) {
      setError('加载失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.name || !formData.originalUrl) {
      toast.error('请填写完整信息');
      return;
    }

    try {
      const shortUrl = `${window.location.origin}/r/${Math.random().toString(36).substring(2, 8)}`;
      const mockCode: DynamicCode = {
        id: `dyn_${Date.now()}`,
        shortCode: shortUrl.split('/').pop() || '',
        originalUrl: formData.originalUrl,
        name: formData.name,
        type: formData.type,
        style: { ...style },
        scanCount: 0,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        isActive: true,
      };

      addCode(mockCode);
      toast.success('动态二维码创建成功');
      setShowCreateModal(false);
      setFormData({ name: '', originalUrl: '', type: 'url' });
    } catch (error) {
      toast.error('创建失败');
    }
  };

  const handleToggle = async (code: DynamicCode) => {
    const newStatus = !code.isActive;
    updateCode(code.id, { isActive: newStatus });
    toast.success(newStatus ? '已启用' : '已停用');
  };

  const handleCopy = async (code: DynamicCode) => {
    const shortUrl = `${window.location.origin}/r/${code.shortCode}`;
    await navigator.clipboard.writeText(shortUrl);
    setCopiedId(code.id);
    toast.success('链接已复制');
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDelete = (id: string) => {
    if (confirm('确定要删除这个动态二维码吗？')) {
      deleteCode(id);
      toast.success('已删除');
    }
  };

  if (!isAuthenticated()) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Zap className="mx-auto h-16 w-16 text-slate-600 mb-4" />
          <h2 className="text-2xl font-bold text-slate-300 mb-2">请先登录</h2>
          <p className="text-slate-500">登录后即可使用动态二维码功能</p>
        </div>
      </div>
    );
  }

  const dynamicStyle: QRStyle = {
    ...style,
    size: 200,
  };

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent">
                动态二维码
              </h1>
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${
                wsConnected 
                  ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                  : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
              }`}>
                {wsConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
                {wsConnected ? '实时同步' : '离线'}
              </span>
            </div>
            <p className="text-slate-400">
              创建可编辑的动态二维码，随时更新内容无需重新打印
            </p>
          </motion.div>
          <motion.button
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-medium shadow-lg shadow-blue-500/25"
          >
            <Plus size={20} />
            创建动态码
          </motion.button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
          </div>
        ) : codes.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-20"
          >
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-slate-800/50 flex items-center justify-center">
              <Zap size={40} className="text-slate-600" />
            </div>
            <h3 className="text-xl font-semibold text-slate-300 mb-2">
              暂无动态二维码
            </h3>
            <p className="text-slate-500 mb-6">
              创建您的第一个动态二维码，享受内容可编辑、扫描可统计的功能
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium transition-colors"
            >
              <Plus size={18} />
              立即创建
            </button>
          </motion.div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {codes.map((code, index) => (
              <motion.div
                key={code.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="group relative rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6 hover:border-slate-700/50 transition-all"
              >
                <div className="absolute top-4 right-4 flex items-center gap-2">
                  <button
                    onClick={() => handleToggle(code)}
                    className="text-slate-400 hover:text-white transition-colors"
                  >
                    {code.isActive ? (
                      <ToggleRight size={24} className="text-green-400" />
                    ) : (
                      <ToggleLeft size={24} className="text-slate-600" />
                    )}
                  </button>
                </div>

                <div className="flex justify-center mb-4">
                  <QRCodePreview
                    content={`${window.location.origin}/r/${code.shortCode}`}
                    style={code.style || dynamicStyle}
                    canvasId={`qr-dynamic-${code.id}`}
                  />
                </div>

                <h3 className="font-semibold text-slate-200 mb-1 truncate">
                  {code.name}
                </h3>
                <div className="flex items-center gap-2 mb-3">
                  <span className="px-2 py-0.5 rounded-full text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    {getTypeLabel(code.type)}
                  </span>
                  <span className="text-xs text-slate-500">
                    {code.scanCount} 次扫描
                  </span>
                </div>

                <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-800/50 mb-4">
                  <Link size={14} className="text-slate-500 flex-shrink-0" />
                  <span className="text-xs text-slate-400 flex-1 truncate font-mono">
                    /r/{code.shortCode}
                  </span>
                  <button
                    onClick={() => handleCopy(code)}
                    className="text-slate-400 hover:text-blue-400 transition-colors"
                  >
                    {copiedId === code.id ? (
                      <Check size={14} className="text-green-400" />
                    ) : (
                      <Copy size={14} />
                    )}
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setEditingCode(code)}
                    className="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm transition-colors"
                  >
                    <Edit2 size={14} />
                    编辑
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

        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6"
            >
              <h3 className="text-xl font-bold text-slate-200 mb-4">
                创建动态二维码
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    名称
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="例如：产品宣传页"
                    className="w-full px-4 py-3 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    目标链接
                  </label>
                  <input
                    type="url"
                    value={formData.originalUrl}
                    onChange={(e) => setFormData({ ...formData, originalUrl: e.target.value })}
                    placeholder="https://example.com"
                    className="w-full px-4 py-3 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    类型
                  </label>
                  <select
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value as QRCodeType })}
                    className="w-full px-4 py-3 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value="url">网址</option>
                    <option value="text">文本</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleCreate}
                  className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-medium"
                >
                  创建
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { X, Copy, Check, Link2, Clock, Lock, Unlock, Eye, Edit3 } from 'lucide-react';

interface ShareDialogProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
}

const ShareDialog: React.FC<ShareDialogProps> = ({ isOpen, onClose, sessionId }) => {
  const [shareLink, setShareLink] = useState<string>('');

  const [copied, setCopied] = useState(false);

  const [expiresIn, setExpiresIn] = useState(86400000);

  const [password, setPassword] = useState('');

  const [permissions, setPermissions] = useState<'read' | 'write'>('write');

  const [loading, setLoading] = useState(false);

  const [hasPassword, setHasPassword] = useState(false);

  const generateShareLink = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/share', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId,
          expiresIn,
          password: password || undefined,
          permissions,
        }),
      });
      const data = await response.json();
      if (data.shareUrl) {
        setShareLink(data.shareUrl);
        setHasPassword(!!password);
      }
    } catch (error) {
      console.error('Failed to generate share link:', error);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async () => {
    if (shareLink) {
      await navigator.clipboard.writeText(shareLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="bg-gradient-to-r from-blue-600 to-cyan-600 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 text-white">
            <Link2 size={24} />
            <h2 className="text-xl font-semibold">分享协作</h2>

          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              链接有效期
            </label>
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-gray-400" />
              <select
                value={expiresIn}
                onChange={(e) => setExpiresIn(Number(e.target.value))}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value={3600000}>1 小时</option>
                <option value={86400000}>1 天</option>
                <option value={604800000}>7 天</option>
                <option value={2592000000}>30 天</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              访问权限
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setPermissions('read')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
                  permissions === 'read'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <Eye size={18} />
                <div className="text-left">
                  <div className="text-sm font-medium">仅查看</div>
                  <div className="text-xs text-gray-500">可查看注释但不能编辑</div>
                </div>
              </button>
              <button
                onClick={() => setPermissions('write')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
                  permissions === 'write'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <Edit3 size={18} />
                <div className="text-left">
                  <div className="text-sm font-medium">可编辑</div>
                  <div className="text-xs text-gray-500">可以添加和编辑注释</div>
                </div>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              密码保护 (可选)
            </label>
            <div className="relative">
              {password ? (
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              ) : (
                <Unlock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              )}
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="设置密码保护链接"
                className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            {password && (
              <p className="text-xs text-gray-500 mt-1">
                访问者需要输入密码才能加入

              </p>
            )}
          </div>

          {!shareLink ? (
            <button
              onClick={generateShareLink}
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-lg font-medium hover:from-blue-700 hover:to-cyan-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '生成中...' : '生成分享链接'}
            </button>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
                <input
                  type="text"
                  value={shareLink}
                  readOnly
                  className="flex-1 bg-transparent text-sm text-gray-700 outline-none"
                />
                <button
                  onClick={copyToClipboard}
                  className="p-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-colors"
                >
                  {copied ? <Check size={18} /> : <Copy size={18} />}
                </button>
              </div>
              
              {copied && (
                <p className="text-sm text-green-600 text-center">
                  ✓ 链接已复制到剪贴板

                </p>
              )}

              <div className="flex items-center justify-center gap-4 text-sm text-gray-500">
                {hasPassword && (
                  <span className="flex items-center gap-1">
                    <Lock size={14} />
                    已设置密码

                  </span>
                )}
                <span className="flex items-center gap-1">
                  {permissions === 'read' ? <Eye size={14} /> : <Edit3 size={14} />}
                  {permissions === 'read' ? '仅查看' : '可编辑'}
                </span>
              </div>

              <p className="text-sm text-gray-500 text-center">
                任何人获得此链接都可以{permissions === 'read' ? '查看' : '编辑'}图表注释

              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ShareDialog;

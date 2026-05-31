import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Lock, Unlock, AlertCircle, ArrowRight } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';
import { USER_COLORS } from '../../shared/types';
import { User } from '../../shared/types';
import { useWebSocket } from '../hooks/useWebSocket';
import { useStore } from '../store/useStore';

const ShareAccess: React.FC = () => {
  const { shareId } = useParams<{ shareId: string }>();
  const navigate = useNavigate();
  
  const [password, setPassword] = useState('');
  const [userName, setUserName] = useState('');
  const [requiresPassword, setRequiresPassword] = useState(false);
  const [permissions, setPermissions] = useState<'read' | 'write'>('write');
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linkInfo, setLinkInfo] = useState<any>(null);
  
  const { connect } = useWebSocket();
  const { setSessionId, setCurrentUser, setChartData, setPermissions: setStorePermissions } = useStore();

  useEffect(() => {
    if (shareId) {
      checkShareLink();
    }
  }, [shareId]);

  const checkShareLink = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/share/${shareId}/info`);
      
      if (response.status === 404) {
        setError('分享链接已过期或不存在');
        return;
      }
      
      const data = await response.json();
      setLinkInfo(data);
      setRequiresPassword(data.requiresPassword);
      setPermissions(data.permissions);
      
      if (!data.requiresPassword) {
        verifyAccess();
      }
    } catch (error) {
      setError('加载分享链接信息失败');
    } finally {
      setLoading(false);
    }
  };

  const verifyAccess = async (pwd?: string) => {
    if (!shareId) return;
    
    try {
      setVerifying(true);
      setError(null);
      
      const response = await fetch(`/api/share/${shareId}/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password: pwd }),
      });
      
      if (response.status === 401) {
        setError('密码错误，请重试');
        return;
      }
      
      if (response.status === 404) {
        setError('分享链接已过期或不存在');
        return;
      }
      
      const data = await response.json();
      
      if (data.sessionId) {
        const sessionResponse = await fetch(`/api/sessions/${data.sessionId}`);
        const sessionData = await sessionResponse.json();
        
        setSessionId(data.sessionId);
        setStorePermissions(data.permissions);
        setChartData(sessionData.chartData);
      }
    } catch (error) {
      setError('验证失败，请重试');
    } finally {
      setVerifying(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (requiresPassword && !password) {
      setError('请输入密码');
      return;
    }
    
    if (!userName.trim()) {
      setError('请输入您的名字');
      return;
    }
    
    verifyAccess(requiresPassword ? password : undefined);
  };

  const handleJoin = () => {
    if (!userName.trim()) {
      setError('请输入您的名字');
      return;
    }

    const user: User = {
      id: uuidv4(),
      name: userName,
      color: USER_COLORS[Math.floor(Math.random() * USER_COLORS.length)],
    };
    
    setCurrentUser(user);
    
    const sessionId = useStore.getState().sessionId;
    if (sessionId) {
      connect(sessionId, user, permissions);
      navigate('/');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
      </div>
    );
  }

  if (error && !linkInfo) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">链接无效</h2>
          <p className="text-gray-500 mb-6">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="w-full py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors"
          >
            返回首页
          </button>
        </div>
      </div>
    );
  }

  const sessionId = useStore.getState().sessionId;
  
  if (sessionId) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">加入协作</h1>
            <p className="text-gray-500">输入您的名字开始查看和注释图表</p>
          </div>

          <div className="mb-6 p-4 bg-blue-50 rounded-xl border border-blue-100">
            <div className="flex items-center gap-3">
              {permissions === 'read' ? (
                <>
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Lock size={20} className="text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-blue-900">仅查看权限</p>
                    <p className="text-xs text-blue-600">您可以查看注释，但无法编辑</p>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <Unlock size={20} className="text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-green-900">完全访问权限</p>
                    <p className="text-xs text-green-600">您可以添加和编辑注释</p>
                  </div>
                </>
              )}
            </div>
          </div>

          <form onSubmit={(e) => { e.preventDefault(); handleJoin(); }} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                您的名字
              </label>
              <input
                type="text"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                placeholder="例如：张三"
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && userName.trim()) {
                    handleJoin();
                  }
                }}
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={verifying || !userName.trim()}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-xl font-medium hover:from-blue-700 hover:to-cyan-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/30 flex items-center justify-center gap-2"
            >
              加入协作
              <ArrowRight size={18} />
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">需要密码</h1>
          <p className="text-gray-500">此分享链接受密码保护</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              访问密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              您的名字
            </label>
            <input
              type="text"
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              placeholder="例如：张三"
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={verifying}
            className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-xl font-medium hover:from-blue-700 hover:to-cyan-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/30"
          >
            {verifying ? '验证中...' : '验证并进入'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ShareAccess;

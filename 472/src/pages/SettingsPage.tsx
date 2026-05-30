import { useState } from 'react';
import { User, Palette, Bell, Shield, Save } from 'lucide-react';
import { useStore } from '../stores/useStore';

export const SettingsPage = () => {
  const { currentUser, setCurrentUser } = useStore();
  const [userName, setUserName] = useState(currentUser.name);
  const [notifications, setNotifications] = useState(true);
  const [autoSave, setAutoSave] = useState(true);

  const handleSave = () => {
    setCurrentUser({ ...currentUser, name: userName });
  };

  return (
    <div className="p-8 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">设置</h1>
        <p className="text-slate-400">管理您的账户和应用偏好</p>
      </div>

      <div className="space-y-6">
        <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-blue-600/20 rounded-xl flex items-center justify-center">
              <User className="w-5 h-5 text-blue-400" />
            </div>
            <h2 className="text-lg font-semibold text-white">个人信息</h2>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-6">
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center text-white font-bold text-2xl"
                style={{ backgroundColor: currentUser.color }}
              >
                {currentUser.name.charAt(0)}
              </div>
              <div>
                <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors">
                  更换头像
                </button>
                <p className="text-xs text-slate-500 mt-2">支持 JPG、PNG 格式，最大 2MB</p>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">用户名</label>
              <input
                type="text"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">邮箱</label>
              <input
                type="email"
                value={`${currentUser.name.toLowerCase().replace(/\s/g, '')}@example.com`}
                className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
                disabled
              />
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-purple-600/20 rounded-xl flex items-center justify-center">
              <Palette className="w-5 h-5 text-purple-400" />
            </div>
            <h2 className="text-lg font-semibold text-white">外观设置</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">主题颜色</label>
              <div className="flex gap-3">
                {['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'].map((color) => (
                  <button
                    key={color}
                    className={`w-10 h-10 rounded-xl transition-transform hover:scale-110 ${
                      currentUser.color === color ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-800' : ''
                    }`}
                    style={{ backgroundColor: color }}
                    onClick={() => setCurrentUser({ ...currentUser, color })}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-orange-600/20 rounded-xl flex items-center justify-center">
              <Bell className="w-5 h-5 text-orange-400" />
            </div>
            <h2 className="text-lg font-semibold text-white">通知设置</h2>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">协作通知</p>
                <p className="text-sm text-slate-400">当有协作者添加标注时通知</p>
              </div>
              <button
                onClick={() => setNotifications(!notifications)}
                className={`w-12 h-6 rounded-full transition-colors ${
                  notifications ? 'bg-blue-600' : 'bg-slate-600'
                }`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    notifications ? 'translate-x-6' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">自动保存</p>
                <p className="text-sm text-slate-400">自动保存标注更改</p>
              </div>
              <button
                onClick={() => setAutoSave(!autoSave)}
                className={`w-12 h-6 rounded-full transition-colors ${
                  autoSave ? 'bg-blue-600' : 'bg-slate-600'
                }`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                    autoSave ? 'translate-x-6' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-red-600/20 rounded-xl flex items-center justify-center">
              <Shield className="w-5 h-5 text-red-400" />
            </div>
            <h2 className="text-lg font-semibold text-white">安全设置</h2>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-700/50 rounded-xl">
              <div>
                <p className="text-white font-medium">修改密码</p>
                <p className="text-sm text-slate-400">上次修改: 30天前</p>
              </div>
              <button className="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white text-sm font-medium rounded-lg transition-colors">
                修改
              </button>
            </div>

            <div className="flex items-center justify-between p-4 bg-slate-700/50 rounded-xl">
              <div>
                <p className="text-white font-medium">双因素认证</p>
                <p className="text-sm text-slate-400">增强账户安全性</p>
              </div>
              <span className="px-3 py-1 bg-green-600/20 text-green-400 text-sm font-medium rounded-full">
                已启用
              </span>
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-all hover:shadow-lg hover:shadow-blue-600/30"
          >
            <Save className="w-5 h-5" />
            保存更改
          </button>
        </div>
      </div>
    </div>
  );
};

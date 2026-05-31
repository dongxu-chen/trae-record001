import { useEffect } from 'react';
import { Palette, Eye, Hash, Globe, Save } from 'lucide-react';
import { motion } from 'framer-motion';
import { useStore } from '../store/useStore';
import type { NamingStyle, Language } from '../../shared/types';

const Settings = () => {
  const { settings, updateSettings, loadSettings } = useStore();

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const namingStyles: { value: NamingStyle; label: string; example: string }[] = [
    { value: 'camelCase', label: 'camelCase (小驼峰)', example: 'userName' },
    { value: 'snake_case', label: 'snake_case (下划线)', example: 'user_name' },
    { value: 'PascalCase', label: 'PascalCase (大驼峰)', example: 'UserName' },
    { value: 'kebab-case', label: 'kebab-case (短横线)', example: 'user-name' },
    { value: 'SCREAMING_SNAKE_CASE', label: 'UPPER_SNAKE (大写下划线)', example: 'USER_NAME' }
  ];

  const languages: { value: Language; label: string }[] = [
    { value: 'zh', label: '中文' },
    { value: 'en', label: 'English' },
    { value: 'ja', label: '日本語' },
    { value: 'ko', label: '한국어' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50/30">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-bold text-gray-900">设置</h2>
          <p className="text-gray-600 mt-1">自定义您的命名偏好</p>
        </motion.div>

        <div className="space-y-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                <Palette className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">默认命名风格</h3>
                <p className="text-sm text-gray-500">选择您偏好的命名风格</p>
              </div>
            </div>

            <div className="space-y-3">
              {namingStyles.map((style) => (
                <label
                  key={style.value}
                  className="flex items-center justify-between p-4 rounded-xl border cursor-pointer transition-all hover:bg-gray-50 hover:border-blue-300"
                >
                  <div className="flex items-center gap-3">
                    <input
                      type="radio"
                      name="defaultStyle"
                      value={style.value}
                      checked={settings.defaultStyle === style.value}
                      onChange={(e) =>
                        updateSettings({ defaultStyle: e.target.value as NamingStyle })
                      }
                      className="w-4 h-4 text-blue-600"
                    />
                    <div>
                      <div className="font-medium text-gray-900">{style.label}</div>
                      <code className="text-sm text-gray-500 font-mono">{style.example}</code>
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-cyan-100 rounded-xl flex items-center justify-center">
                <Globe className="w-5 h-5 text-cyan-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">语言偏好</h3>
                <p className="text-sm text-gray-500">设置您的首选语言</p>
              </div>
            </div>

            <div className="space-y-3">
              <label className="flex items-center justify-between p-4 rounded-xl border cursor-pointer transition-all hover:bg-gray-50 hover:border-blue-300">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={settings.autoDetectLanguage}
                    onChange={(e) =>
                      updateSettings({ autoDetectLanguage: e.target.checked })
                    }
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="font-medium text-gray-900">自动检测语言</span>
                </div>
              </label>

              {!settings.autoDetectLanguage && (
                <div className="mt-4">
                  <label className="text-sm font-medium text-gray-700 mb-2 block">
                    首选语言
                  </label>
                  <select
                    value={settings.preferredLanguage}
                    onChange={(e) =>
                      updateSettings({ preferredLanguage: e.target.value as Language })
                    }
                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
                  >
                    {languages.map((lang) => (
                      <option key={lang.value} value={lang.value}>
                        {lang.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center">
                <Eye className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">显示选项</h3>
                <p className="text-sm text-gray-500">自定义界面显示内容</p>
              </div>
            </div>

            <div className="space-y-3">
              <label className="flex items-center justify-between p-4 rounded-xl border cursor-pointer transition-all hover:bg-gray-50 hover:border-blue-300">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={settings.showConfidence}
                    onChange={(e) =>
                      updateSettings({ showConfidence: e.target.checked })
                    }
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="font-medium text-gray-900">显示置信度</span>
                </div>
              </label>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
                <Hash className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">推荐数量</h3>
                <p className="text-sm text-gray-500">设置每次推荐的结果数量</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <input
                type="range"
                min="3"
                max="15"
                value={settings.maxRecommendations}
                onChange={(e) =>
                  updateSettings({ maxRecommendations: parseInt(e.target.value) })
                }
                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <span className="w-12 text-center font-semibold text-gray-900">
                {settings.maxRecommendations}
              </span>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="flex items-center justify-center gap-3 py-4"
          >
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Save className="w-4 h-4" />
              设置自动保存
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Settings;

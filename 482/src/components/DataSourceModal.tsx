import { useState } from 'react';
import { X, Plus, Database, Server, Trash2, RefreshCw, Check } from 'lucide-react';
import { useLineageStore } from '@/stores/useLineageStore';
import { DataSource, DataSourceType } from '@/types';

type FormState = Omit<DataSource, 'id'>;

export const DataSourceModal = () => {
  const {
    dataSources,
    showDataSourceModal,
    setShowDataSourceModal,
    addDataSource,
    removeDataSource,
    testDataSource,
  } = useLineageStore();

  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState<Partial<FormState>>({
    name: '',
    type: 'mysql',
    host: '',
    port: 3306,
    database: '',
    username: '',
    password: '',
    status: 'disconnected',
  });
  const [testingId, setTestingId] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.name && formData.host && formData.database) {
      addDataSource(formData as FormState);
      setShowAddForm(false);
      setFormData({
        name: '',
        type: 'mysql',
        host: '',
        port: 3306,
        database: '',
        username: '',
        password: '',
        status: 'disconnected',
      });
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    await testDataSource(id);
    setTestingId(null);
  };

  if (!showDataSourceModal) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-fade-in">
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden shadow-2xl">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center">
              <Database className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">数据源管理</h2>
              <p className="text-sm text-gray-500">管理MySQL和Hive数据源配置</p>
            </div>
          </div>
          <button
            onClick={() => setShowDataSourceModal(false)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(80vh-140px)]">
          <div className="space-y-4">
            {dataSources.map((ds) => (
              <div
                key={ds.id}
                className="p-4 bg-gray-50 rounded-xl border border-gray-100"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        ds.type === 'mysql'
                          ? 'bg-blue-100 text-blue-600'
                          : 'bg-orange-100 text-orange-600'
                    }`}
                    >
                      <Server className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">{ds.name}</div>
                      <div className="text-sm text-gray-500 mt-1 font-mono">
                        {ds.type.toUpperCase()} · {ds.host}:{ds.port}/{ds.database}
                      </div>
                      {ds.username && (
                        <div className="text-xs text-gray-400 mt-1">
                          用户: {ds.username}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTest(ds.id)}
                      disabled={testingId === ds.id}
                      className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
                      title="测试连接"
                    >
                      <RefreshCw
                        className={`w-4 h-4 text-gray-500 ${
                          testingId === ds.id ? 'animate-spin' : ''}
                        }`}
                      />
                    </button>
                    <button
                      onClick={() => removeDataSource(ds.id)}
                      className="p-2 hover:bg-red-100 rounded-lg transition-colors"
                      title="删除"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                    <span
                      className={`w-2 h-2 rounded-full ${
                        ds.status === 'connected'
                          ? 'bg-green-500'
                          : ds.status === 'connecting'
                          ? 'bg-yellow-500 animate-pulse'
                          : 'bg-red-500'
                    }`}
                    />
                  </div>
                </div>
              </div>
            ))}

            {showAddForm ? (
              <form
                onSubmit={handleSubmit}
                className="p-4 bg-primary-50 rounded-xl border border-primary-100 border-dashed"
              >
                <h3 className="font-medium text-gray-900 mb-4">添加数据源</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      数据源名称
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })}
                      className="input-field"
                      placeholder="例如：MySQL业务库"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      数据源类型
                    </label>
                    <select
                      value={formData.type}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          type: e.target.value as DataSourceType,
                          port: e.target.value === 'mysql' ? 3306 : 10000,
                        })}
                      className="input-field"
                    >
                      <option value="mysql">MySQL</option>
                      <option value="hive">Hive</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      主机地址
                    </label>
                    <input
                      type="text"
                      value={formData.host}
                      onChange={(e) =>
                        setFormData({ ...formData, host: e.target.value })}
                      className="input-field"
                      placeholder="192.168.1.100"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      端口
                    </label>
                    <input
                      type="number"
                      value={formData.port}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          port: parseInt(e.target.value) || 3306,
                        })}
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      数据库名
                    </label>
                    <input
                      type="text"
                      value={formData.database}
                      onChange={(e) =>
                        setFormData({ ...formData, database: e.target.value })}
                      className="input-field"
                      placeholder="business_db"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      用户名
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) =>
                        setFormData({ ...formData, username: e.target.value })}
                      className="input-field"
                      placeholder="data_ro"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      密码
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) =>
                        setFormData({ ...formData, password: e.target.value })}
                      className="input-field"
                      placeholder="••••••••"
                    />
                  </div>
                </div>
                <div className="flex gap-3 mt-6">
                  <button
                    type="button"
                    onClick={() => setShowAddForm(false)}
                    className="btn-secondary flex-1"
                  >
                    取消
                  </button>
                  <button type="submit" className="btn-primary flex-1 flex items-center justify-center gap-2">
                    <Check className="w-4 h-4" />
                    添加
                  </button>
                </div>
              </form>
            ) : (
              <button
                onClick={() => setShowAddForm(true)}
                className="w-full p-4 border-2 border-dashed border-gray-200 rounded-xl text-gray-500 hover:border-primary-300 hover:text-primary-500 transition-colors flex items-center justify-center gap-2"
              >
                <Plus className="w-5 h-5" />
                添加数据源
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

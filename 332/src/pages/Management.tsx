import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, QrCode, AlertTriangle, Bell, Search, Filter,
  MoreVertical, Play, Pause, Trash2, Edit2, Eye, RefreshCw,
  TrendingUp, TrendingDown, Activity, Users, MapPin, Smartphone,
  AlertCircle, CheckCircle, Info, X, Download, Settings
} from 'lucide-react';
import { toast } from '@/components/ui/toast';
import { useAuthStore, useDynamicCodeStore } from '@/store';
import { dynamicCodeAPI } from '@/utils/api';
import { wsClient } from '@/utils/websocket';
import type { DynamicCode, ManagementOverview } from '@/types';

interface Alert {
  id: string;
  type: 'warning' | 'error' | 'info' | 'success';
  message: string;
  codeId?: string;
  timestamp: string;
  read: boolean;
}

export default function Management() {
  const { isAuthenticated, user } = useAuthStore();
  const { codes, setCodes, updateCode, deleteCode, setLoading } = useDynamicCodeStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [selectedCodes, setSelectedCodes] = useState<string[]>([]);
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showAlertPanel, setShowAlertPanel] = useState(false);
  const [overview, setOverview] = useState<ManagementOverview | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [selectedCodeDetail, setSelectedCodeDetail] = useState<DynamicCode | null>(null);

  const setupWebSocket = useCallback(() => {
    if (!user?.id) return;

    wsClient.connect(user.id, {
      onConnected: () => {
        setWsConnected(true);
        console.log('管理平台WebSocket已连接');
      },
      onDisconnected: () => {
        setWsConnected(false);
      },
      onDynamicCodeCreated: (data) => {
        setCodes([data, ...codes]);
        addAlert({
          id: Date.now().toString(),
          type: 'success',
          message: `新二维码 "${data.name}" 已创建`,
          codeId: data.id,
          timestamp: new Date().toISOString(),
          read: false,
        });
      },
      onDynamicCodeUpdated: (data) => {
        updateCode(data.id, data);
        addAlert({
          id: Date.now().toString(),
          type: 'info',
          message: `二维码 "${data.name}" 已更新`,
          codeId: data.id,
          timestamp: new Date().toISOString(),
          read: false,
        });
      },
      onDynamicCodeDeleted: (data) => {
        deleteCode(data.id);
        addAlert({
          id: Date.now().toString(),
          type: 'warning',
          message: `二维码已被删除`,
          codeId: data.id,
          timestamp: new Date().toISOString(),
          read: false,
        });
      },
      onScanUpdated: (data) => {
        const code = codes.find(c => c.id === data.id);
        if (code) {
          updateCode(data.id, { scanCount: data.scanCount });
          if (data.scanCount % 100 === 0 && data.scanCount > 0) {
            addAlert({
              id: Date.now().toString(),
              type: 'success',
              message: `🎉 "${code.name}" 扫码量突破 ${data.scanCount} 次！`,
              codeId: data.id,
              timestamp: new Date().toISOString(),
              read: false,
            });
          }
        }
      },
    });
  }, [user, codes, setCodes, updateCode, deleteCode]);

  useEffect(() => {
    if (isAuthenticated() && user?.id) {
      loadData();
      setupWebSocket();

      return () => {
        wsClient.disconnect();
      };
    }
  }, [isAuthenticated, user?.id, setupWebSocket]);

  const loadData = async () => {
    setLoading(true);
    try {
      const result = await dynamicCodeAPI.list();
      if (result.success && result.data) {
        setCodes(result.data);
        generateMockOverview(result.data);
      }

      const mockAlerts: Alert[] = [
        { id: '1', type: 'success', message: '"产品推广码" 扫码量突破 1000 次！', codeId: '1', timestamp: new Date().toISOString(), read: false },
        { id: '2', type: 'warning', message: '"活动二维码" 已 7 天没有扫描记录', codeId: '2', timestamp: new Date(Date.now() - 3600000).toISOString(), read: false },
        { id: '3', type: 'info', message: '系统检测到异常扫描流量，已自动处理', timestamp: new Date(Date.now() - 7200000).toISOString(), read: true },
      ];
      setAlerts(mockAlerts);
    } catch (error) {
      toast.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const generateMockOverview = (codeList: DynamicCode[]) => {
    const today = new Date();
    const thisMonth = today.getMonth();

    const recentScans = Array.from({ length: 10 }, (_, i) => {
      const code = codeList[i % codeList.length];
      const countries = ['中国', '美国', '日本', '德国', '英国'];
      const devices = ['mobile', 'desktop', 'tablet'];
      return {
        id: `scan-${i}`,
        codeName: code?.name || '未知二维码',
        timestamp: new Date(Date.now() - i * 60000).toISOString(),
        country: countries[Math.floor(Math.random() * countries.length)],
        deviceType: devices[Math.floor(Math.random() * devices.length)],
      };
    });

    const topCodes = codeList.slice(0, 5).map(code => ({
      id: code.id,
      name: code.name,
      scans: code.scanCount || Math.floor(Math.random() * 5000),
      growthRate: (Math.random() - 0.3) * 100,
      status: code.isActive ? 'active' as const : 'inactive' as const,
    }));

    const mockOverview: ManagementOverview = {
      totalCodes: codeList.length,
      activeCodes: codeList.filter(c => c.isActive).length,
      inactiveCodes: codeList.filter(c => !c.isActive).length,
      totalScansToday: Math.floor(Math.random() * 500) + 100,
      totalScansThisMonth: Math.floor(Math.random() * 10000) + 2000,
      avgScansPerCode: Math.floor(Math.random() * 500) + 50,
      topCodes,
      recentScans,
      alerts: alerts.filter(a => !a.read).map(a => ({
        id: a.id,
        type: a.type,
        message: a.message,
        codeId: a.codeId,
        timestamp: a.timestamp,
      })),
    };

    setOverview(mockOverview);
  };

  const addAlert = (alert: Alert) => {
    setAlerts(prev => [alert, ...prev]);
  };

  const toggleCodeStatus = async (code: DynamicCode) => {
    try {
      const newStatus = !code.isActive;
      updateCode(code.id, { isActive: newStatus });
      toast.success(newStatus ? `已启用 "${code.name}"` : `已停用 "${code.name}"`);
      addAlert({
        id: Date.now().toString(),
        type: newStatus ? 'success' : 'warning',
        message: `二维码 "${code.name}" 已${newStatus ? '启用' : '停用'}`,
        codeId: code.id,
        timestamp: new Date().toISOString(),
        read: false,
      });
    } catch (error) {
      toast.error('操作失败');
    }
  };

  const handleBulkToggle = (active: boolean) => {
    selectedCodes.forEach(id => {
      const code = codes.find(c => c.id === id);
      if (code) {
        updateCode(id, { isActive: active });
      }
    });
    toast.success(`已${active ? '启用' : '停用'} ${selectedCodes.length} 个二维码`);
    setSelectedCodes([]);
    setShowBulkActions(false);
  };

  const handleBulkDelete = () => {
    if (confirm(`确定要删除选中的 ${selectedCodes.length} 个二维码吗？`)) {
      selectedCodes.forEach(id => deleteCode(id));
      toast.success(`已删除 ${selectedCodes.length} 个二维码`);
      setSelectedCodes([]);
      setShowBulkActions(false);
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedCodes(prev =>
      prev.includes(id) ? prev.filter(c => c !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (selectedCodes.length === filteredCodes.length) {
      setSelectedCodes([]);
    } else {
      setSelectedCodes(filteredCodes.map(c => c.id));
    }
  };

  const markAlertAsRead = (alertId: string) => {
    setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, read: true } : a));
  };

  const markAllAlertsAsRead = () => {
    setAlerts(prev => prev.map(a => ({ ...a, read: true })));
    toast.success('所有通知已标记为已读');
  };

  const filteredCodes = codes.filter(code => {
    const matchesSearch = code.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      code.shortCode.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' ||
      (statusFilter === 'active' && code.isActive) ||
      (statusFilter === 'inactive' && !code.isActive);
    return matchesSearch && matchesStatus;
  });

  const getAlertIcon = (type: Alert['type']) => {
    switch (type) {
      case 'success': return <CheckCircle size={16} className="text-green-400" />;
      case 'warning': return <AlertTriangle size={16} className="text-yellow-400" />;
      case 'error': return <AlertCircle size={16} className="text-red-400" />;
      default: return <Info size={16} className="text-blue-400" />;
    }
  };

  if (!isAuthenticated()) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <LayoutDashboard className="mx-auto h-16 w-16 text-slate-600 mb-4" />
          <h2 className="text-2xl font-bold text-slate-300 mb-2">请先登录</h2>
          <p className="text-slate-500">登录后即可使用管理平台</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent">
                二维码管理平台
              </h1>
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${
                wsConnected
                  ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                  : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
              }`}>
                {wsConnected ? <Activity size={12} /> : <X size={12} />}
                {wsConnected ? '实时监控中' : '离线'}
              </span>
            </div>
            <p className="text-slate-400">统一管理所有二维码，实时监控扫码动态</p>
          </motion.div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setShowAlertPanel(!showAlertPanel)}
                className="relative p-3 rounded-xl bg-slate-800/50 text-slate-400 hover:text-white transition-colors"
              >
                <Bell size={20} />
                {alerts.filter(a => !a.read).length > 0 && (
                  <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 rounded-full text-[10px] flex items-center justify-center text-white">
                    {alerts.filter(a => !a.read).length}
                  </span>
                )}
              </motion.button>

              <AnimatePresence>
                {showAlertPanel && (
                  <motion.div
                    initial={{ opacity: 0, y: -10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.95 }}
                    className="absolute right-0 top-full mt-2 w-80 max-h-96 overflow-y-auto rounded-xl bg-slate-900 border border-slate-800 shadow-2xl z-50"
                  >
                    <div className="p-3 border-b border-slate-800 flex items-center justify-between">
                      <h3 className="font-semibold text-slate-200">通知中心</h3>
                      <button
                        onClick={markAllAlertsAsRead}
                        className="text-xs text-blue-400 hover:text-blue-300"
                      >
                        全部已读
                      </button>
                    </div>
                    <div className="p-2">
                      {alerts.length === 0 ? (
                        <p className="text-center text-slate-500 py-8">暂无通知</p>
                      ) : (
                        alerts.map(alert => (
                          <motion.div
                            key={alert.id}
                            onClick={() => markAlertAsRead(alert.id)}
                            className={`p-3 rounded-lg mb-1 cursor-pointer transition-colors ${
                              alert.read ? 'opacity-60' : 'bg-slate-800/50'
                            } hover:bg-slate-800`}
                          >
                            <div className="flex items-start gap-2">
                              {getAlertIcon(alert.type)}
                              <div className="flex-1">
                                <p className="text-sm text-slate-200">{alert.message}</p>
                                <p className="text-xs text-slate-500 mt-1">
                                  {new Date(alert.timestamp).toLocaleString('zh-CN')}
                                </p>
                              </div>
                              {!alert.read && (
                                <div className="w-2 h-2 bg-blue-500 rounded-full mt-1" />
                              )}
                            </div>
                          </motion.div>
                        ))
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={loadData}
              className="p-3 rounded-xl bg-slate-800/50 text-slate-400 hover:text-white transition-colors"
            >
              <RefreshCw size={20} />
            </motion.button>
          </div>
        </div>

        {overview && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            {[
              { label: '总二维码', value: overview.totalCodes, icon: QrCode, color: 'blue' },
              { label: '活跃二维码', value: overview.activeCodes, icon: Play, color: 'green' },
              { label: '已停用', value: overview.inactiveCodes, icon: Pause, color: 'slate' },
              { label: '今日扫码', value: overview.totalScansToday.toLocaleString(), icon: Eye, color: 'purple' },
              { label: '本月扫码', value: overview.totalScansThisMonth.toLocaleString(), icon: Users, color: 'cyan' },
              { label: '平均扫码', value: overview.avgScansPerCode.toLocaleString(), icon: TrendingUp, color: 'orange' },
            ].map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-4"
              >
                <div className="flex items-center gap-2 mb-2">
                  <stat.icon size={16} className={`${
                    stat.color === 'blue' ? 'text-blue-400' :
                    stat.color === 'green' ? 'text-green-400' :
                    stat.color === 'purple' ? 'text-purple-400' :
                    stat.color === 'cyan' ? 'text-cyan-400' :
                    stat.color === 'orange' ? 'text-orange-400' :
                    'text-slate-400'
                  }`} />
                  <span className="text-slate-400 text-xs">{stat.label}</span>
                </div>
                <p className="text-xl font-bold text-white">{stat.value}</p>
              </motion.div>
            ))}
          </div>
        )}

        {overview && overview.topCodes.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6 mb-8"
          >
            <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
              <TrendingUp size={20} className="text-green-400" />
              表现最佳二维码
            </h3>
            <div className="grid md:grid-cols-5 gap-4">
              {overview.topCodes.map((code, index) => (
                <motion.div
                  key={code.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + index * 0.05 }}
                  className="p-4 rounded-xl bg-slate-800/30 border border-slate-700/50 hover:border-slate-600/50 transition-colors cursor-pointer"
                  onClick={() => setSelectedCodeDetail(codes.find(c => c.id === code.id) || null)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-2xl font-bold text-slate-500">#{index + 1}</span>
                    {code.growthRate >= 0 ? (
                      <span className="flex items-center gap-1 text-xs text-green-400">
                        <TrendingUp size={12} /> {code.growthRate.toFixed(0)}%
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-red-400">
                        <TrendingDown size={12} /> {Math.abs(code.growthRate).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <h4 className="font-medium text-slate-200 truncate mb-1">{code.name}</h4>
                  <p className="text-sm text-slate-400">{code.scans.toLocaleString()} 次扫码</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {overview && overview.recentScans.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6 mb-8"
          >
            <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
              <Activity size={20} className="text-cyan-400" />
              实时扫码动态
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">时间</th>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">二维码</th>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">地区</th>
                    <th className="px-4 py-3 text-left text-slate-400 font-medium">设备</th>
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence>
                    {overview.recentScans.map((scan, index) => (
                      <motion.tr
                        key={scan.id}
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 + index * 0.05 }}
                        className="border-b border-slate-800/50 hover:bg-slate-800/30"
                      >
                        <td className="px-4 py-3 text-slate-300">
                          {new Date(scan.timestamp).toLocaleTimeString('zh-CN')}
                        </td>
                        <td className="px-4 py-3 text-slate-200">{scan.codeName}</td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1 text-slate-400">
                            <MapPin size={12} /> {scan.country}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-1 text-slate-400">
                            <Smartphone size={12} /> {scan.deviceType}
                          </span>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
        >
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
            <h3 className="text-lg font-semibold text-slate-200">二维码列表</h3>

            <div className="flex items-center gap-3">
              <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="搜索二维码名称或短码..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 pr-4 py-2 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="flex gap-1 bg-slate-800/50 rounded-xl p-1">
                {(['all', 'active', 'inactive'] as const).map(status => (
                  <button
                    key={status}
                    onClick={() => setStatusFilter(status)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      statusFilter === status
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {status === 'all' ? '全部' : status === 'active' ? '活跃' : '已停用'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {selectedCodes.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 p-4 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-between"
            >
              <span className="text-blue-300">
                已选择 <span className="font-bold">{selectedCodes.length}</span> 个二维码
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => handleBulkToggle(true)}
                  className="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm font-medium transition-colors"
                >
                  批量启用
                </button>
                <button
                  onClick={() => handleBulkToggle(false)}
                  className="px-4 py-2 rounded-lg bg-yellow-600 hover:bg-yellow-500 text-white text-sm font-medium transition-colors"
                >
                  批量停用
                </button>
                <button
                  onClick={handleBulkDelete}
                  className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium transition-colors"
                >
                  批量删除
                </button>
                <button
                  onClick={() => { setSelectedCodes([]); setShowBulkActions(false); }}
                  className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium transition-colors"
                >
                  取消选择
                </button>
              </div>
            </motion.div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={selectedCodes.length === filteredCodes.length && filteredCodes.length > 0}
                      onChange={selectAll}
                      className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-slate-400 font-medium">名称</th>
                  <th className="px-4 py-3 text-left text-slate-400 font-medium">短码</th>
                  <th className="px-4 py-3 text-left text-slate-400 font-medium">扫码量</th>
                  <th className="px-4 py-3 text-left text-slate-400 font-medium">状态</th>
                  <th className="px-4 py-3 text-left text-slate-400 font-medium">创建时间</th>
                  <th className="px-4 py-3 text-left text-slate-400 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredCodes.map((code, index) => (
                  <motion.tr
                    key={code.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.8 + index * 0.02 }}
                    className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                  >
                    <td className="px-4 py-4">
                      <input
                        type="checkbox"
                        checked={selectedCodes.includes(code.id)}
                        onChange={() => toggleSelect(code.id)}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500"
                      />
                    </td>
                    <td className="px-4 py-4">
                      <span className="font-medium text-slate-200">{code.name}</span>
                    </td>
                    <td className="px-4 py-4">
                      <code className="text-xs text-cyan-400 bg-cyan-500/10 px-2 py-1 rounded">
                        /r/{code.shortCode}
                      </code>
                    </td>
                    <td className="px-4 py-4 text-slate-300">
                      {code.scanCount.toLocaleString()}
                    </td>
                    <td className="px-4 py-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
                        code.isActive
                          ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                          : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                      }`}>
                        {code.isActive ? <Play size={12} /> : <Pause size={12} />}
                        {code.isActive ? '活跃' : '已停用'}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-slate-400">
                      {new Date(code.createdAt).toLocaleDateString('zh-CN')}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => toggleCodeStatus(code)}
                          className={`p-2 rounded-lg transition-colors ${
                            code.isActive
                              ? 'text-yellow-400 hover:bg-yellow-500/10'
                              : 'text-green-400 hover:bg-green-500/10'
                          }`}
                          title={code.isActive ? '停用' : '启用'}
                        >
                          {code.isActive ? <Pause size={14} /> : <Play size={14} />}
                        </button>
                        <button
                          onClick={() => setSelectedCodeDetail(code)}
                          className="p-2 rounded-lg text-blue-400 hover:bg-blue-500/10 transition-colors"
                          title="查看详情"
                        >
                          <Eye size={14} />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`确定要删除 "${code.name}" 吗？`)) {
                              deleteCode(code.id);
                              toast.success('已删除');
                            }
                          }}
                          className="p-2 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
                          title="删除"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>

            {filteredCodes.length === 0 && (
              <div className="text-center py-12">
                <QrCode className="mx-auto h-12 w-12 text-slate-600 mb-3" />
                <p className="text-slate-400">暂无二维码</p>
              </div>
            )}
          </div>
        </motion.div>

        <AnimatePresence>
          {selectedCodeDetail && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
              onClick={() => setSelectedCodeDetail(null)}
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                onClick={e => e.stopPropagation()}
                className="w-full max-w-2xl rounded-2xl bg-slate-900 border border-slate-800 p-6 max-h-[80vh] overflow-y-auto"
              >
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-xl font-bold text-white">二维码详情</h3>
                  <button
                    onClick={() => setSelectedCodeDetail(null)}
                    className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                  >
                    <X size={20} />
                  </button>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold text-slate-200 mb-3">基本信息</h4>
                    <div className="space-y-3">
                      <div>
                        <label className="text-sm text-slate-400">名称</label>
                        <p className="text-slate-200">{selectedCodeDetail.name}</p>
                      </div>
                      <div>
                        <label className="text-sm text-slate-400">短码</label>
                        <code className="text-cyan-400 bg-cyan-500/10 px-2 py-1 rounded text-sm">
                          /r/{selectedCodeDetail.shortCode}
                        </code>
                      </div>
                      <div>
                        <label className="text-sm text-slate-400">目标链接</label>
                        <p className="text-slate-200 text-sm break-all">{selectedCodeDetail.originalUrl}</p>
                      </div>
                      <div>
                        <label className="text-sm text-slate-400">扫码量</label>
                        <p className="text-2xl font-bold text-white">{selectedCodeDetail.scanCount.toLocaleString()}</p>
                      </div>
                      <div>
                        <label className="text-sm text-slate-400">状态</label>
                        <p className={selectedCodeDetail.isActive ? 'text-green-400' : 'text-slate-400'}>
                          {selectedCodeDetail.isActive ? '活跃' : '已停用'}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-semibold text-slate-200 mb-3">时间信息</h4>
                    <div className="space-y-3">
                      <div>
                        <label className="text-sm text-slate-400">创建时间</label>
                        <p className="text-slate-200">
                          {new Date(selectedCodeDetail.createdAt).toLocaleString('zh-CN')}
                        </p>
                      </div>
                      <div>
                        <label className="text-sm text-slate-400">更新时间</label>
                        <p className="text-slate-200">
                          {new Date(selectedCodeDetail.updatedAt).toLocaleString('zh-CN')}
                        </p>
                      </div>
                    </div>

                    <h4 className="font-semibold text-slate-200 mb-3 mt-6">快速操作</h4>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => toggleCodeStatus(selectedCodeDetail)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                          selectedCodeDetail.isActive
                            ? 'bg-yellow-600 hover:bg-yellow-500 text-white'
                            : 'bg-green-600 hover:bg-green-500 text-white'
                        }`}
                      >
                        {selectedCodeDetail.isActive ? '停用' : '启用'}
                      </button>
                      <button
                        className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
                      >
                        编辑
                      </button>
                      <button
                        className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium transition-colors"
                      >
                        查看统计
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`确定要删除 "${selectedCodeDetail.name}" 吗？`)) {
                            deleteCode(selectedCodeDetail.id);
                            setSelectedCodeDetail(null);
                            toast.success('已删除');
                          }
                        }}
                        className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-medium transition-colors"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

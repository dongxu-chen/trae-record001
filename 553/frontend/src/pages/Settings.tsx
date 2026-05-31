import { useState } from 'react'
import {
  Cog6ToothIcon,
  ServerIcon,
  GaugeIcon,
  FireIcon,
  SnowflakeIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  BoltIcon,
  SignalIcon,
  ArrowsRightLeftIcon,
  ChartBarIcon,
  RocketLaunchIcon,
} from '@heroicons/react/24/outline'
import { useSpeedInfo } from '../hooks/useMonitor'

export function Settings() {
  const { data: speedInfo } = useSpeedInfo()

  const [speedLimit, setSpeedLimit] = useState('100mb')
  const [minSpeedLimit, setMinSpeedLimit] = useState('10mb')
  const [adaptiveSpeed, setAdaptiveSpeed] = useState(true)
  const [targetPendingTasks, setTargetPendingTasks] = useState('5')

  const [diskLow, setDiskLow] = useState('85%')
  const [diskHigh, setDiskHigh] = useState('90%')
  const [diskFlood, setDiskFlood] = useState('95%')
  const [dynamicWatermark, setDynamicWatermark] = useState(true)
  const [baseCapacityGB, setBaseCapacityGB] = useState('500')
  const [maxExtraPercent, setMaxExtraPercent] = useState('10')

  const [loadAwareness, setLoadAwareness] = useState(true)
  const [avoidHighLoadNodes, setAvoidHighLoadNodes] = useState(true)
  const [highLoadThreshold, setHighLoadThreshold] = useState('0.8')
  const [ioWaitThreshold, setIoWaitThreshold] = useState('50')
  const [cpuLoadThreshold, setCpuLoadThreshold] = useState('0.8')

  const [hotColdEnabled, setHotColdEnabled] = useState(false)
  const [hotAttr, setHotAttr] = useState('box_type')
  const [hotValue, setHotValue] = useState('hot')
  const [coldAttr, setColdAttr] = useState('box_type')
  const [coldValue, setColdValue] = useState('cold')
  const [autoBalance, setAutoBalance] = useState(true)
  const [schedule, setSchedule] = useState('0 */5 * * * *')

  const [shardHeatEnabled, setShardHeatEnabled] = useState(true)
  const [queryWeight, setQueryWeight] = useState('0.6')
  const [indexWeight, setIndexWeight] = useState('0.4')
  const [heatThreshold, setHeatThreshold] = useState('0.7')
  const [priorityBoost, setPriorityBoost] = useState('1.5')
  const [heatCollectInterval, setHeatCollectInterval] = useState('60')

  const [autoScalingEnabled, setAutoScalingEnabled] = useState(false)
  const [floodThreshold, setFloodThreshold] = useState('95')
  const [cooldownMinutes, setCooldownMinutes] = useState('30')
  const [minNodes, setMinNodes] = useState('3')
  const [maxNodes, setMaxNodes] = useState('10')
  const [scalingProvider, setScalingProvider] = useState('webhook')
  const [nodeType, setNodeType] = useState('data_hot')
  const [diskSizeGB, setDiskSizeGB] = useState('1000')
  const [webhookURL, setWebhookURL] = useState('http://localhost:9090/api/scale')

  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle')

  const handleSave = () => {
    setSaveStatus('success')
    setTimeout(() => setSaveStatus('idle'), 3000)
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">系统设置</h2>
        <div className="flex items-center space-x-3">
          {saveStatus === 'success' && (
            <span className="flex items-center text-es-green text-sm">
              <CheckCircleIcon className="w-4 h-4 mr-1" />
              已保存
            </span>
          )}
          <button className="btn-primary" onClick={handleSave}>
            保存设置
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-es-blue/20 rounded-lg">
                <GaugeIcon className="w-5 h-5 text-es-blue" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">迁移速度限制</h3>
                {speedInfo && (
                  <p className="text-xs text-es-dark-400">
                    当前速度: <span className="text-es-blue font-mono">{speedInfo.current_speed}</span>
                  </p>
                )}
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={adaptiveSpeed}
                onChange={(e) => setAdaptiveSpeed(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-es-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-es-blue"></div>
            </label>
          </div>
          {adaptiveSpeed ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">最小速度</label>
                  <select
                    value={minSpeedLimit}
                    onChange={(e) => setMinSpeedLimit(e.target.value)}
                    className="input-field"
                  >
                    <option value="5mb">5 MB/s</option>
                    <option value="10mb">10 MB/s</option>
                    <option value="20mb">20 MB/s</option>
                    <option value="50mb">50 MB/s</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">最大速度</label>
                  <select
                    value={speedLimit}
                    onChange={(e) => setSpeedLimit(e.target.value)}
                    className="input-field"
                  >
                    <option value="50mb">50 MB/s</option>
                    <option value="100mb">100 MB/s</option>
                    <option value="200mb">200 MB/s</option>
                    <option value="500mb">500 MB/s</option>
                    <option value="1000mb">1000 MB/s</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm text-es-dark-300 mb-2">目标待处理任务数</label>
                <input
                  type="number"
                  value={targetPendingTasks}
                  onChange={(e) => setTargetPendingTasks(e.target.value)}
                  className="input-field"
                  min="1"
                  max="100"
                />
                <p className="text-xs text-es-dark-400 mt-2">
                  系统根据待处理任务数自动调整速度，低于此值时加速，超过时减速
                </p>
              </div>
              <div className="flex items-start space-x-3 p-4 bg-es-dark-900 rounded-lg">
                <ArrowsRightLeftIcon className="w-5 h-5 text-es-blue flex-shrink-0 mt-0.5" />
                <p className="text-sm text-es-dark-300">
                  自适应限速模式：根据集群负载动态调整迁移速度，在低负载时加快迁移，在高负载时减速保护业务。
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-es-dark-300 mb-2">固定传输速度</label>
                <select
                  value={speedLimit}
                  onChange={(e) => setSpeedLimit(e.target.value)}
                  className="input-field"
                >
                  <option value="10mb">10 MB/s</option>
                  <option value="20mb">20 MB/s</option>
                  <option value="50mb">50 MB/s</option>
                  <option value="100mb">100 MB/s</option>
                  <option value="200mb">200 MB/s</option>
                  <option value="500mb">500 MB/s</option>
                </select>
                <p className="text-xs text-es-dark-400 mt-2">
                  限制分片迁移时的网络传输速度，避免影响业务
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-es-yellow/20 rounded-lg">
                <ServerIcon className="w-5 h-5 text-es-yellow" />
              </div>
              <h3 className="text-lg font-semibold text-white">磁盘水位阈值</h3>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={dynamicWatermark}
                onChange={(e) => setDynamicWatermark(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-es-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-es-blue"></div>
            </label>
          </div>
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-es-dark-300 mb-2">低水位 (%)</label>
                <input
                  type="number"
                  value={diskLow.replace('%', '')}
                  onChange={(e) => setDiskLow(e.target.value + '%')}
                  className="input-field"
                  min="0"
                  max="100"
                />
              </div>
              <div>
                <label className="block text-sm text-es-dark-300 mb-2">高水位 (%)</label>
                <input
                  type="number"
                  value={diskHigh.replace('%', '')}
                  onChange={(e) => setDiskHigh(e.target.value + '%')}
                  className="input-field"
                  min="0"
                  max="100"
                />
              </div>
              <div>
                <label className="block text-sm text-es-dark-300 mb-2">洪水水位 (%)</label>
                <input
                  type="number"
                  value={diskFlood.replace('%', '')}
                  onChange={(e) => setDiskFlood(e.target.value + '%')}
                  className="input-field"
                  min="0"
                  max="100"
                />
              </div>
            </div>
            {dynamicWatermark && (
              <div className="grid grid-cols-2 gap-4 p-4 bg-es-dark-900 rounded-lg">
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">基准容量 (GB)</label>
                  <input
                    type="number"
                    value={baseCapacityGB}
                    onChange={(e) => setBaseCapacityGB(e.target.value)}
                    className="input-field"
                    min="100"
                  />
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">最大额外百分比 (%)</label>
                  <input
                    type="number"
                    value={maxExtraPercent}
                    onChange={(e) => setMaxExtraPercent(e.target.value)}
                    className="input-field"
                    min="0"
                    max="30"
                  />
                </div>
              </div>
            )}
            <div className="flex items-start space-x-3 p-4 bg-es-dark-900 rounded-lg">
              <ExclamationCircleIcon className="w-5 h-5 text-es-yellow flex-shrink-0 mt-0.5" />
              <div className="text-sm text-es-dark-300">
                <p className="font-medium text-es-dark-200">水位说明：</p>
                <p className="mt-1">• 低水位：磁盘使用率超过时，ES 不再分配新分片</p>
                <p>• 高水位：磁盘使用率超过时，ES 尝试迁移分片到其他节点</p>
                <p>• 洪水水位：磁盘使用率超过时，ES 将索引设为只读</p>
                {dynamicWatermark && (
                  <p className="mt-2 text-es-blue">
                    • 动态水位已启用：大容量节点的阈值将按比例提高（每超出基准容量500GB增加2%，最多{maxExtraPercent}%）
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <SignalIcon className="w-5 h-5 text-purple-500" />
              </div>
              <h3 className="text-lg font-semibold text-white">负载感知</h3>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={loadAwareness}
                onChange={(e) => setLoadAwareness(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-es-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-es-blue"></div>
            </label>
          </div>
          {loadAwareness ? (
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  id="avoidHighLoad"
                  checked={avoidHighLoadNodes}
                  onChange={(e) => setAvoidHighLoadNodes(e.target.checked)}
                  className="w-4 h-4 rounded bg-es-dark-700 border-es-dark-600 text-es-blue focus:ring-es-blue"
                />
                <label htmlFor="avoidHighLoad" className="text-sm text-es-dark-200">
                  迁移时避让高负载节点
                </label>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">高负载阈值</label>
                  <input
                    type="number"
                    value={highLoadThreshold}
                    onChange={(e) => setHighLoadThreshold(e.target.value)}
                    className="input-field"
                    step="0.1"
                    min="0.1"
                    max="1.0"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">负载综合评分</p>
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">IO 等待阈值 (%)</label>
                  <input
                    type="number"
                    value={ioWaitThreshold}
                    onChange={(e) => setIoWaitThreshold(e.target.value)}
                    className="input-field"
                    min="5"
                    max="100"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">IO 等待百分比</p>
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">CPU 负载阈值</label>
                  <input
                    type="number"
                    value={cpuLoadThreshold}
                    onChange={(e) => setCpuLoadThreshold(e.target.value)}
                    className="input-field"
                    step="0.1"
                    min="0.1"
                    max="1.0"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">单核负载系数</p>
                </div>
              </div>
              <div className="flex items-start space-x-3 p-4 bg-es-dark-900 rounded-lg">
                <BoltIcon className="w-5 h-5 text-purple-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-es-dark-300">
                  负载感知模式：系统持续监控节点 CPU、负载均值、IO 等待等指标，在选择迁移目标时优先选择低负载节点，避让高负载节点，避免业务受影响。
                </p>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-es-dark-400">
              <SignalIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>负载感知已关闭</p>
              <p className="text-sm mt-1">迁移时不考虑节点负载情况</p>
            </div>
          )}
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-red-500/20 rounded-lg">
                <ChartBarIcon className="w-5 h-5 text-red-500" />
              </div>
              <h3 className="text-lg font-semibold text-white">分片热度分析</h3>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={shardHeatEnabled}
                onChange={(e) => setShardHeatEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-es-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-es-blue"></div>
            </label>
          </div>
          {shardHeatEnabled ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">查询权重</label>
                  <input
                    type="number"
                    value={queryWeight}
                    onChange={(e) => setQueryWeight(e.target.value)}
                    className="input-field"
                    step="0.1"
                    min="0"
                    max="1"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">查询频率权重占比</p>
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">写入权重</label>
                  <input
                    type="number"
                    value={indexWeight}
                    onChange={(e) => setIndexWeight(e.target.value)}
                    className="input-field"
                    step="0.1"
                    min="0"
                    max="1"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">写入频率权重占比</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">热度阈值</label>
                  <input
                    type="number"
                    value={heatThreshold}
                    onChange={(e) => setHeatThreshold(e.target.value)}
                    className="input-field"
                    step="0.1"
                    min="0"
                    max="1"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">判定为热索引的阈值</p>
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">优先级倍数</label>
                  <input
                    type="number"
                    value={priorityBoost}
                    onChange={(e) => setPriorityBoost(e.target.value)}
                    className="input-field"
                    step="0.1"
                    min="1"
                    max="5"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">热分片迁移优先级倍数</p>
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">采集间隔 (秒)</label>
                  <input
                    type="number"
                    value={heatCollectInterval}
                    onChange={(e) => setHeatCollectInterval(e.target.value)}
                    className="input-field"
                    min="10"
                    max="300"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">索引热度统计间隔</p>
                </div>
              </div>
              <div className="flex items-start space-x-3 p-4 bg-es-dark-900 rounded-lg">
                <FireIcon className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-es-dark-300">
                  分片热度分析：系统持续统计各索引的查询和写入频率，计算热度评分。热索引的分片在均衡时享有更高优先级，优先进行迁移以获得更好的性能。
                </p>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-es-dark-400">
              <ChartBarIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>分片热度分析已关闭</p>
              <p className="text-sm mt-1">迁移时不考虑分片热度优先级</p>
            </div>
          )}
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-orange-500/20 rounded-lg">
                <FireIcon className="w-5 h-5 text-orange-500" />
              </div>
              <h3 className="text-lg font-semibold text-white">冷热分离</h3>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={hotColdEnabled}
                onChange={(e) => setHotColdEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-es-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-es-blue"></div>
            </label>
          </div>
          {hotColdEnabled ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">热节点属性名</label>
                  <input
                    type="text"
                    value={hotAttr}
                    onChange={(e) => setHotAttr(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">热节点属性值</label>
                  <input
                    type="text"
                    value={hotValue}
                    onChange={(e) => setHotValue(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">冷节点属性名</label>
                  <input
                    type="text"
                    value={coldAttr}
                    onChange={(e) => setColdAttr(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">冷节点属性值</label>
                  <input
                    type="text"
                    value={coldValue}
                    onChange={(e) => setColdValue(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>
              <div className="flex items-start space-x-3 p-4 bg-es-dark-900 rounded-lg">
                <SnowflakeIcon className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-es-dark-300">
                  启用冷热分离后，分片只会在同类型节点间迁移。热节点存储近期高频访问数据，冷节点存储历史低频访问数据。
                </p>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-es-dark-400">
              <SnowflakeIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>冷热分离已关闭</p>
            </div>
          )}
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-es-green/20 rounded-lg">
                <ClockIcon className="w-5 h-5 text-es-green" />
              </div>
              <h3 className="text-lg font-semibold text-white">自动均衡</h3>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={autoBalance}
                onChange={(e) => setAutoBalance(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-es-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-es-blue"></div>
            </label>
          </div>
          {autoBalance ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-es-dark-300 mb-2">执行计划 (Cron 表达式)</label>
                <input
                  type="text"
                  value={schedule}
                  onChange={(e) => setSchedule(e.target.value)}
                  className="input-field font-mono"
                />
                <p className="text-xs text-es-dark-400 mt-2">
                  当前设置：每 5 分钟执行一次均衡检查
                </p>
              </div>
              <div className="flex items-start space-x-3 p-4 bg-es-dark-900 rounded-lg">
                <CheckCircleIcon className="w-5 h-5 text-es-green flex-shrink-0 mt-0.5" />
                <p className="text-sm text-es-dark-300">
                  开启自动均衡后，系统将按计划自动检查集群状态并执行必要的分片迁移。
                </p>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-es-dark-400">
              <Cog6ToothIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>自动均衡已关闭</p>
              <p className="text-sm mt-1">需要手动执行分片迁移</p>
            </div>
          )}
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-cyan-500/20 rounded-lg">
                <RocketLaunchIcon className="w-5 h-5 text-cyan-500" />
              </div>
              <h3 className="text-lg font-semibold text-white">自动扩容</h3>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={autoScalingEnabled}
                onChange={(e) => setAutoScalingEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-es-dark-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-es-blue"></div>
            </label>
          </div>
          {autoScalingEnabled ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">扩容触发阈值 (%)</label>
                  <input
                    type="number"
                    value={floodThreshold}
                    onChange={(e) => setFloodThreshold(e.target.value)}
                    className="input-field"
                    min="80"
                    max="100"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">磁盘使用率达到此值触发扩容</p>
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">冷却时间 (分钟)</label>
                  <input
                    type="number"
                    value={cooldownMinutes}
                    onChange={(e) => setCooldownMinutes(e.target.value)}
                    className="input-field"
                    min="5"
                    max="120"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">扩容后等待时间再检查</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">最小节点数</label>
                  <input
                    type="number"
                    value={minNodes}
                    onChange={(e) => setMinNodes(e.target.value)}
                    className="input-field"
                    min="1"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">集群最少保留节点数</p>
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">最大节点数</label>
                  <input
                    type="number"
                    value={maxNodes}
                    onChange={(e) => setMaxNodes(e.target.value)}
                    className="input-field"
                    min="1"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">集群最多扩容节点数</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">扩容提供商</label>
                  <select
                    value={scalingProvider}
                    onChange={(e) => setScalingProvider(e.target.value)}
                    className="input-field"
                  >
                    <option value="webhook">Webhook</option>
                  </select>
                  <p className="text-xs text-es-dark-500 mt-1">扩容方式</p>
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">节点类型</label>
                  <input
                    type="text"
                    value={nodeType}
                    onChange={(e) => setNodeType(e.target.value)}
                    className="input-field"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">新节点的角色类型</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">磁盘大小 (GB)</label>
                  <input
                    type="number"
                    value={diskSizeGB}
                    onChange={(e) => setDiskSizeGB(e.target.value)}
                    className="input-field"
                    min="100"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">新节点磁盘容量</p>
                </div>
                <div>
                  <label className="block text-sm text-es-dark-300 mb-2">Webhook URL</label>
                  <input
                    type="text"
                    value={webhookURL}
                    onChange={(e) => setWebhookURL(e.target.value)}
                    className="input-field font-mono text-sm"
                  />
                  <p className="text-xs text-es-dark-500 mt-1">扩容触发时调用的地址</p>
                </div>
              </div>
              <div className="flex items-start space-x-3 p-4 bg-es-dark-900 rounded-lg">
                <RocketLaunchIcon className="w-5 h-5 text-cyan-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-es-dark-300">
                  自动扩容：当节点磁盘使用率超过洪水阈值时，系统会自动调用Webhook通知基础设施层添加新节点，避免集群因磁盘不足而只读。
                </p>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center text-es-dark-400">
              <RocketLaunchIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>自动扩容已关闭</p>
              <p className="text-sm mt-1">需要手动处理集群扩容</p>
            </div>
          )}
        </div>
      </div>

      <div className="card p-6">
        <div className="flex items-center space-x-3 mb-6">
          <div className="p-2 bg-es-dark-600 rounded-lg">
            <Cog6ToothIcon className="w-5 h-5 text-es-dark-300" />
          </div>
          <h3 className="text-lg font-semibold text-white">关于</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-sm text-es-dark-400">版本</p>
            <p className="text-white font-medium mt-1">1.0.0</p>
          </div>
          <div>
            <p className="text-sm text-es-dark-400">构建时间</p>
            <p className="text-white font-medium mt-1">2024-01-01</p>
          </div>
          <div>
            <p className="text-sm text-es-dark-400">支持 ES 版本</p>
            <p className="text-white font-medium mt-1">7.x / 8.x</p>
          </div>
          <div>
            <p className="text-sm text-es-dark-400">许可证</p>
            <p className="text-white font-medium mt-1">MIT</p>
          </div>
        </div>
      </div>
    </div>
  )
}

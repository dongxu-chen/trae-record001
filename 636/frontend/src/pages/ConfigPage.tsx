import React from 'react';
import { useNavigate } from 'react-router-dom';
import { InputNumber, Slider, Button, Collapse, Alert, Select, Radio, Card, Row, Col, Statistic } from 'antd';
import AlgorithmCard from '../components/AlgorithmCard';
import { useTestStore } from '../store/testStore';
import { startTest } from '../utils/api';
import { TestWebSocketClient } from '../utils/websocket';
import { IdAlgorithm, TestConfig, ClockMode } from '../types';

const { Panel } = Collapse;
const { Option } = Select;

const ConfigPage: React.FC = () => {
  const navigate = useNavigate();
  const { testConfig, setTestConfig, startTest: setTestRunning, addMetrics, setCurrentReport, isRunning } = useTestStore();
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const wsClientRef = React.useRef<TestWebSocketClient | null>(null);

  const handleAlgorithmChange = (algorithm: IdAlgorithm) => {
    setTestConfig({ ...testConfig, algorithm });
  };

  const handleThreadCountChange = (value: number | null) => {
    if (value !== null) {
      setTestConfig({ ...testConfig, threadCount: value });
    }
  };

  const handleDurationChange = (value: number | null) => {
    if (value !== null) {
      setTestConfig({ ...testConfig, durationSeconds: value });
    }
  };

  const handleSnowflakeConfigChange = (field: 'workerId' | 'datacenterId' | 'clockOffsetMs' | 'clockBackProbability', value: number) => {
    setTestConfig({
      ...testConfig,
      snowflakeConfig: {
        ...testConfig.snowflakeConfig!,
        [field]: value,
      },
    });
  };

  const handleClockModeChange = (mode: ClockMode) => {
    setTestConfig({
      ...testConfig,
      snowflakeConfig: {
        ...testConfig.snowflakeConfig!,
        clockMode: mode,
      },
    });
  };

  const handleSegmentConfigChange = (value: number) => {
    setTestConfig({
      ...testConfig,
      segmentConfig: {
        ...testConfig.segmentConfig!,
        segmentSize: value,
      },
    });
  };

  const handleUniquenessConfigChange = (field: 'sampleSize' | 'falsePositiveProbability', value: number) => {
    setTestConfig({
      ...testConfig,
      uniquenessConfig: {
        ...testConfig.uniquenessConfig!,
        [field]: value,
      },
    });
  };

  const calculateEstimatedMemory = () => {
    const { threadCount, durationSeconds, uniquenessConfig } = testConfig;
    const estimatedIds = threadCount * durationSeconds * 50000;
    const p = uniquenessConfig?.falsePositiveProbability || 0.0001;
    const m = Math.ceil(-estimatedIds * Math.log(p) / (Math.log(2) * Math.log(2)));
    const bloomFilterMB = Math.ceil(m / 8 / 1024 / 1024);
    const originalMB = Math.ceil(estimatedIds * 24 / 1024 / 1024);
    const sampleMB = Math.ceil((uniquenessConfig?.sampleSize || 10000) * 24 / 1024 / 1024);
    return { bloomFilterMB, originalMB, sampleMB, estimatedIds };
  };

  const memoryInfo = calculateEstimatedMemory();

  const handleStartTest = async () => {
    setLoading(true);
    setError(null);

    try {
      const config: TestConfig = {
        ...testConfig,
        snowflakeConfig: testConfig.algorithm === 'SNOWFLAKE' ? testConfig.snowflakeConfig : undefined,
        segmentConfig: testConfig.algorithm === 'SEGMENT' ? testConfig.segmentConfig : undefined,
      };

      const response = await startTest(config);
      setTestRunning(response.testId);

      wsClientRef.current = new TestWebSocketClient({
        onMetrics: (metrics) => {
          addMetrics(metrics);
        },
        onComplete: (report) => {
          setCurrentReport(report);
          navigate('/report');
        },
      });

      wsClientRef.current.connect(response.testId);
      navigate('/monitor');
    } catch (err) {
      setError('启动测试失败，请检查后端服务是否正常运行');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const algorithms: IdAlgorithm[] = ['SNOWFLAKE', 'SEGMENT', 'RANDOM'];
  const clockModes: { value: ClockMode; label: string; desc: string }[] = [
    { value: 'NORMAL', label: '正常时钟', desc: '使用真实系统时间' },
    { value: 'CLOCK_DRIFT', label: '时钟漂移', desc: '模拟时钟逐渐偏移' },
    { value: 'CLOCK_BACKWARD', label: '时钟回拨', desc: '随机触发时钟回拨' },
    { value: 'MIXED', label: '混合模式', desc: '同时模拟漂移和回拨' },
  ];

  return (
    <div className="space-y-8">
      {error && (
        <Alert
          message="错误"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
        />
      )}

      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">选择 ID 生成算法</h2>
        <p className="text-gray-500">选择要测试的分布式ID生成算法</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {algorithms.map((algo) => (
          <AlgorithmCard
            key={algo}
            algorithm={algo}
            selected={testConfig.algorithm === algo}
            onClick={() => handleAlgorithmChange(algo)}
          />
        ))}
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold text-gray-800 mb-6">并发配置</h3>

        <div className="space-y-8">
          <div>
            <div className="flex justify-between items-center mb-3">
              <label className="text-sm font-medium text-gray-700">并发线程数</label>
              <span className="font-mono text-primary font-bold">{testConfig.threadCount}</span>
            </div>
            <div className="flex items-center space-x-4">
              <Slider
                className="flex-1"
                min={1}
                max={100}
                value={testConfig.threadCount}
                onChange={handleThreadCountChange}
                tooltip={{ formatter: (value) => `${value} 线程` }}
              />
              <InputNumber
                min={1}
                max={100}
                value={testConfig.threadCount}
                onChange={handleThreadCountChange}
                style={{ width: 100 }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-3">
              <label className="text-sm font-medium text-gray-700">测试时长</label>
              <span className="font-mono text-primary font-bold">{testConfig.durationSeconds} 秒</span>
            </div>
            <div className="flex items-center space-x-4">
              <Slider
                className="flex-1"
                min={1}
                max={60}
                value={testConfig.durationSeconds}
                onChange={handleDurationChange}
                tooltip={{ formatter: (value) => `${value} 秒` }}
              />
              <InputNumber
                min={1}
                max={60}
                value={testConfig.durationSeconds}
                onChange={handleDurationChange}
                style={{ width: 100 }}
                addonAfter="秒"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <Collapse defaultActiveKey={['1', '2']} ghost>
          <Panel header="🔧 算法参数配置" key="1" className="px-6">
            <div className="pt-4 space-y-6">
              {testConfig.algorithm === 'SNOWFLAKE' && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Worker ID (机器ID)
                      </label>
                      <InputNumber
                        min={0}
                        max={31}
                        value={testConfig.snowflakeConfig?.workerId}
                        onChange={(v) => handleSnowflakeConfigChange('workerId', v || 0)}
                        style={{ width: '100%' }}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Datacenter ID (数据中心ID)
                      </label>
                      <InputNumber
                        min={0}
                        max={31}
                        value={testConfig.snowflakeConfig?.datacenterId}
                        onChange={(v) => handleSnowflakeConfigChange('datacenterId', v || 0)}
                        style={{ width: '100%' }}
                      />
                    </div>
                  </div>

                  <div className="border-t pt-6">
                    <h4 className="text-md font-semibold text-gray-800 mb-4">⏰ 时钟模拟场景</h4>
                    <p className="text-sm text-gray-500 mb-4">
                      模拟分布式环境中常见的时钟问题，测试雪花算法的容错能力
                    </p>

                    <Radio.Group
                      value={testConfig.snowflakeConfig?.clockMode}
                      onChange={(e) => handleClockModeChange(e.target.value)}
                      className="w-full"
                    >
                      <Row gutter={[16, 16]}>
                        {clockModes.map((mode) => (
                          <Col span={12} key={mode.value}>
                            <Radio.Button value={mode.value} className="h-auto p-4 w-full">
                              <div className="text-left">
                                <div className="font-semibold text-gray-800">{mode.label}</div>
                                <div className="text-xs text-gray-500 mt-1">{mode.desc}</div>
                              </div>
                            </Radio.Button>
                          </Col>
                        ))}
                      </Row>
                    </Radio.Group>

                    {testConfig.snowflakeConfig?.clockMode !== 'NORMAL' && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            时钟偏移量 (ms)
                          </label>
                          <InputNumber
                            min={1}
                            max={1000}
                            value={testConfig.snowflakeConfig?.clockOffsetMs}
                            onChange={(v) => handleSnowflakeConfigChange('clockOffsetMs', v || 10)}
                            style={{ width: '100%' }}
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            回拨概率
                          </label>
                          <Slider
                            min={0.0001}
                            max={0.1}
                            step={0.0001}
                            value={testConfig.snowflakeConfig?.clockBackProbability}
                            onChange={(v) => handleSnowflakeConfigChange('clockBackProbability', v)}
                            tooltip={{ formatter: (value) => `${(value * 100).toFixed(2)}%` }}
                          />
                          <div className="text-right text-xs text-gray-400 mt-1">
                            {(testConfig.snowflakeConfig?.clockBackProbability! * 100).toFixed(2)}%
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {testConfig.algorithm === 'SEGMENT' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    号段大小
                  </label>
                  <InputNumber
                    min={100}
                    max={100000}
                    step={100}
                    value={testConfig.segmentConfig?.segmentSize}
                    onChange={(v) => handleSegmentConfigChange(v || 1000)}
                    style={{ width: '100%' }}
                  />
                </div>
              )}

              {testConfig.algorithm === 'RANDOM' && (
                <p className="text-sm text-gray-500">
                  随机ID算法使用安全随机数生成，无需额外配置
                </p>
              )}
            </div>
          </Panel>

          <Panel header="🔍 唯一性校验配置" key="2" className="px-6">
            <div className="pt-4 space-y-6">
              <Row gutter={16}>
                <Col span={12}>
                  <Card size="small" bordered={false} className="bg-blue-50">
                    <Statistic
                      title="预计生成ID数"
                      value={memoryInfo.estimatedIds.toLocaleString()}
                      suffix="个"
                      className="text-sm"
                    />
                  </Card>
                </Col>
                <Col span={12}>
                  <Card size="small" bordered={false} className="bg-green-50">
                    <Statistic
                      title="预计节省内存"
                      value={memoryInfo.originalMB - memoryInfo.bloomFilterMB - memoryInfo.sampleMB}
                      suffix="MB"
                      className="text-sm"
                    />
                  </Card>
                </Col>
              </Row>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    采样数量
                  </label>
                  <InputNumber
                    min={1000}
                    max={100000}
                    step={1000}
                    value={testConfig.uniquenessConfig?.sampleSize}
                    onChange={(v) => handleUniquenessConfigChange('sampleSize', v || 10000)}
                    style={{ width: '100%' }}
                  />
                  <p className="text-xs text-gray-400 mt-1">
                    从生成的ID中抽样的数量，用于精确校验
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    布隆过滤器误判率
                  </label>
                  <Select
                    value={testConfig.uniquenessConfig?.falsePositiveProbability}
                    onChange={(v) => handleUniquenessConfigChange('falsePositiveProbability', v)}
                    style={{ width: '100%' }}
                  >
                    <Option value={0.0001}>0.01% (推荐)</Option>
                    <Option value={0.001}>0.1%</Option>
                    <Option value={0.01}>1%</Option>
                    <Option value={0.05}>5%</Option>
                  </Select>
                  <p className="text-xs text-gray-400 mt-1">
                    更低的误判率需要更多内存
                  </p>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <span className="text-blue-500">💡</span>
                  <div>
                    <p className="text-sm font-medium text-gray-700">布隆过滤器优势</p>
                    <p className="text-xs text-gray-500 mt-1">
                      布隆过滤器仅需 <span className="font-mono font-bold text-primary">{memoryInfo.bloomFilterMB} MB</span> 内存，
                      相比传统全量存储的 <span className="font-mono font-bold text-orange-500">{memoryInfo.originalMB} MB</span>，
                      节省约 <span className="font-mono font-bold text-green-500">
                        {Math.round((1 - memoryInfo.bloomFilterMB / memoryInfo.originalMB) * 100)}%
                      </span> 的内存。
                      结合 <span className="font-mono font-bold">{memoryInfo.sampleMB} MB</span> 抽样数据，
                      在低内存占用下保证唯一性校验的准确性。
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </Panel>
        </Collapse>
      </div>

      <div className="flex justify-center pt-4">
        <Button
          type="primary"
          size="large"
          loading={loading || isRunning}
          onClick={handleStartTest}
          className="h-12 px-12 text-base font-semibold rounded-lg shadow-lg hover:shadow-xl transition-shadow"
        >
          🚀 开始压力测试
        </Button>
      </div>
    </div>
  );
};

export default ConfigPage;

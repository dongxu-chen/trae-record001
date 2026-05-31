import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Progress, Button, Alert } from 'antd';
import MetricsCard from '../components/MetricsCard';
import QpsChart from '../components/QpsChart';
import LatencyChart from '../components/LatencyChart';
import { useTestStore } from '../store/testStore';
import { TestWebSocketClient } from '../utils/websocket';
import { stopTest } from '../utils/api';

const MonitorPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    currentTestId,
    isRunning,
    currentMetrics,
    metricsHistory,
    testConfig,
    addMetrics,
    setCurrentReport,
    stopTest: setStopTest,
  } = useTestStore();
  const wsClientRef = React.useRef<TestWebSocketClient | null>(null);

  useEffect(() => {
    if (!currentTestId) return;

    wsClientRef.current = new TestWebSocketClient({
      onMetrics: (metrics) => {
        addMetrics(metrics);
      },
      onComplete: (report) => {
        setCurrentReport(report);
        navigate('/report');
      },
    });

    wsClientRef.current.connect(currentTestId);

    return () => {
      wsClientRef.current?.disconnect();
    };
  }, [currentTestId]);

  const handleStopTest = async () => {
    if (currentTestId) {
      await stopTest(currentTestId);
      setStopTest();
    }
  };

  if (!currentTestId) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Alert
          message="没有正在进行的测试"
          description="请先在配置页面启动一个压力测试"
          type="warning"
          showIcon
          className="mb-6"
        />
        <Button type="primary" onClick={() => navigate('/')}>
          去配置测试
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">实时监控</h2>
          <p className="text-gray-500 mt-1">
            测试ID: <span className="font-mono">{currentTestId.slice(0, 8)}...</span>
            <span className="mx-2">|</span>
            算法: {testConfig.algorithm}
          </p>
        </div>
        <Button danger onClick={handleStopTest} disabled={!isRunning} className="h-10 px-6">
          ⏹ 停止测试
        </Button>
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm font-medium text-gray-600">测试进度</span>
          <span className="font-mono text-lg font-bold text-primary">
            {currentMetrics?.progress || 0}%
          </span>
        </div>
        <Progress
          percent={currentMetrics?.progress || 0}
          status={isRunning ? 'active' : 'normal'}
          strokeColor={{
            '0%': '#108ee9',
            '100%': '#87d068',
          }}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricsCard
          title="当前 QPS"
          value={currentMetrics?.qps?.toLocaleString() || 0}
          unit="/s"
          icon="⚡"
          color="text-primary"
        />
        <MetricsCard
          title="平均延迟"
          value={currentMetrics?.avgLatency?.toFixed(2) || 0}
          unit="μs"
          icon="⏱️"
          color="text-emerald-500"
        />
        <MetricsCard
          title="P95 延迟"
          value={currentMetrics?.p95Latency?.toFixed(2) || 0}
          unit="μs"
          icon="📊"
          color="text-amber-500"
        />
        <MetricsCard
          title="已生成 ID"
          value={currentMetrics?.generatedCount?.toLocaleString() || 0}
          icon="🆔"
          color="text-purple-500"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <QpsChart data={metricsHistory} />
        <LatencyChart data={metricsHistory} />
      </div>

      {!isRunning && currentMetrics && (
        <div className="flex justify-center">
          <Button type="primary" size="large" onClick={() => navigate('/report')}>
            📄 查看测试报告
          </Button>
        </div>
      )}
    </div>
  );
};

export default MonitorPage;

import { useState } from 'react';
import axios from 'axios';
import ServiceForm from './components/ServiceForm';
import ResultsDisplay from './components/ResultsDisplay';
import TrafficChart from './components/TrafficChart';
import CostBreakdownChart from './components/CostBreakdownChart';
import type { EvaluationRequest, EvaluationResponse, ServerConfig, Service } from './types';

function App() {
  const [services, setServices] = useState<Service[]>([
    { id: 'api-gateway', name: 'API 网关', dependencies: ['auth-service', 'user-service'] },
    { id: 'auth-service', name: '认证服务', dependencies: [] },
    { id: 'user-service', name: '用户服务', dependencies: ['database'] },
    { id: 'database', name: '数据库', dependencies: [] },
  ]);

  const [serverConfigs, setServerConfigs] = useState<ServerConfig[]>([]);
  const [forecastPeriodDays, setForecastPeriodDays] = useState(30);
  const [targetUtilization, setTargetUtilization] = useState(0.7);
  const [maxLatencyMs, setMaxLatencyMs] = useState(200);
  const [includeDependencies, setIncludeDependencies] = useState(true);

  const [results, setResults] = useState<EvaluationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('input');

  const handleEvaluate = async () => {
    setLoading(true);
    try {
      const request: EvaluationRequest = {
        services,
        performanceData: [],
        loadTestData: [],
        serverConfigs,
        forecastPeriodDays,
        targetUtilization,
        maxLatencyMs,
        includeDependencies,
      };

      const response = await axios.post<EvaluationResponse>('/api/evaluate', request);
      setResults(response.data);
      setActiveTab('results');
    } catch (error) {
      console.error('Evaluation failed:', error);
      alert('评估失败，请检查后端服务是否启动');
    } finally {
      setLoading(false);
    }
  };

  const fetchServerConfigs = async () => {
    try {
      const response = await axios.get<ServerConfig[]>('/api/server-configs');
      setServerConfigs(response.data);
    } catch (error) {
      console.error('Failed to fetch server configs:', error);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🚀 服务性能容量评估工具</h1>
      </header>
      <div className="app-container">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'input' ? 'active' : ''}`}
            onClick={() => setActiveTab('input')}
          >
            参数配置
          </button>
          <button
            className={`tab ${activeTab === 'results' ? 'active' : ''}`}
            onClick={() => setActiveTab('results')}
            disabled={!results}
          >
            评估结果
          </button>
          <button
            className={`tab ${activeTab === 'forecast' ? 'active' : ''}`}
            onClick={() => setActiveTab('forecast')}
            disabled={!results}
          >
            流量预测
          </button>
        </div>

        {activeTab === 'input' && (
          <div>
            <ServiceForm
              services={services}
              setServices={setServices}
              forecastPeriodDays={forecastPeriodDays}
              setForecastPeriodDays={setForecastPeriodDays}
              targetUtilization={targetUtilization}
              setTargetUtilization={setTargetUtilization}
              maxLatencyMs={maxLatencyMs}
              setMaxLatencyMs={setMaxLatencyMs}
              includeDependencies={includeDependencies}
              setIncludeDependencies={setIncludeDependencies}
              serverConfigs={serverConfigs}
              fetchServerConfigs={fetchServerConfigs}
            />

            <div className="card">
              <h3 className="card-title">执行评估</h3>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  className="btn btn-primary"
                  onClick={handleEvaluate}
                  disabled={loading}
                >
                  {loading ? '评估中...' : '开始容量评估'}
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={fetchServerConfigs}
                >
                  加载服务器配置
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'results' && results && (
          <ResultsDisplay results={results} services={services} />
        )}

        {activeTab === 'forecast' && results && (
          <div className="grid grid-2">
            {results.trafficForecasts.map((forecast) => (
              <div key={forecast.serviceId} className="card">
                <h3 className="card-title">
                  {forecast.serviceId} - 流量预测
                  <span
                    className={`tag ${
                      forecast.growthRate > 0.1
                        ? 'tag-orange'
                        : forecast.growthRate > 0
                        ? 'tag-blue'
                        : 'tag-green'
                    }`}
                    style={{ marginLeft: '12px' }}
                  >
                    增长率: {(forecast.growthRate * 100).toFixed(1)}%
                  </span>
                </h3>
                <TrafficChart forecast={forecast} />
              </div>
            ))}
            {results.results.map((result) => (
              <div key={`cost-${result.serviceId}`} className="card">
                <h3 className="card-title">
                  {result.serviceId} - 成本分析
                </h3>
                <CostBreakdownChart result={result} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

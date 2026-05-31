import type { EvaluationResponse, Service } from '../types';

interface ResultsDisplayProps {
  results: EvaluationResponse;
  services: Service[];
}

function ResultsDisplay({ results, services }: ResultsDisplayProps) {
  const getServiceName = (id: string) => {
    const service = services.find(s => s.id === id);
    return service ? service.name : id;
  };

  const getUtilizationColor = (utilization: number) => {
    if (utilization < 0.5) return 'green';
    if (utilization < 0.75) return 'orange';
    return 'red';
  };

  return (
    <div>
      <div className="card">
        <h3 className="card-title">📊 总体评估摘要</h3>
        <div className="grid grid-3">
          <div className="result-card">
            <div className="result-label">评估服务数量</div>
            <div className="result-value">{results.results.length}</div>
          </div>
          <div className="result-card" style={{ borderLeftColor: '#38a169' }}>
            <div className="result-label">总服务器数量</div>
            <div className="result-value green">
              {results.results.reduce((sum, r) => sum + r.recommendedServers, 0)}
            </div>
          </div>
          <div className="result-card" style={{ borderLeftColor: '#dd6b20' }}>
            <div className="result-label">月度总成本</div>
            <div className="result-value orange">
              ${results.totalMonthlyCost.toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">📋 各服务容量评估结果</h3>
        {results.results.map((result) => (
          <div
            key={result.serviceId}
            style={{
              background: '#f7fafc',
              borderRadius: '8px',
              padding: '20px',
              marginBottom: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#2d3748' }}>
                {getServiceName(result.serviceId)}
                <span className="tag tag-blue" style={{ marginLeft: '12px' }}>
                  {result.serviceId}
                </span>
              </h4>
              <span
                className={`tag ${
                  getUtilizationColor(result.utilization) === 'green'
                    ? 'tag-green'
                    : getUtilizationColor(result.utilization) === 'orange'
                    ? 'tag-orange'
                    : 'tag-orange'
                }`}
              >
                利用率: {(result.utilization * 100).toFixed(1)}%
              </span>
            </div>

            <div className="grid grid-3">
              <div>
                <div className="result-label">服务器配置</div>
                <div style={{ fontSize: '14px', fontWeight: 600 }}>
                  {result.serverConfig.name}
                </div>
                <div style={{ fontSize: '12px', color: '#718096' }}>
                  {result.serverConfig.cpuCores} 核 / {result.serverConfig.memoryGB} GB
                </div>
              </div>
              <div>
                <div className="result-label">所需服务器数量</div>
                <div className="result-value" style={{ fontSize: '20px' }}>
                  {result.requiredServers}
                  <span style={{ fontSize: '12px', color: '#718096', marginLeft: '4px' }}>
                    (推荐: {result.recommendedServers})
                  </span>
                </div>
              </div>
              <div>
                <div className="result-label">月度成本</div>
                <div className="result-value orange" style={{ fontSize: '20px' }}>
                  ${result.monthlyCost.toFixed(2)}
                </div>
              </div>
            </div>

            <div className="grid grid-3" style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e2e8f0' }}>
              <div>
                <div className="result-label">预估 CPU 使用率</div>
                <div className={`result-value ${getUtilizationColor(result.estimatedCpuUsage / 100)}`} style={{ fontSize: '18px' }}>
                  {result.estimatedCpuUsage.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="result-label">预估内存使用率</div>
                <div className={`result-value ${getUtilizationColor(result.estimatedMemoryUsage / 100)}`} style={{ fontSize: '18px' }}>
                  {result.estimatedMemoryUsage.toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="result-label">预估延迟</div>
                <div className="result-value" style={{ fontSize: '18px' }}>
                  {result.estimatedLatencyMs.toFixed(2)} ms
                </div>
              </div>
            </div>

            <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e2e8f0' }}>
              <div className="result-label">成本明细</div>
              <div style={{ display: 'flex', gap: '24px', marginTop: '8px', fontSize: '13px' }}>
                <span>计算: ${result.breakdown.computeCost.toFixed(2)}</span>
                <span>存储: ${result.breakdown.storageCost.toFixed(2)}</span>
                <span>网络: ${result.breakdown.networkCost.toFixed(2)}</span>
                <span>人力: ${result.breakdown.laborCost.toFixed(2)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {results.dependencyResults.length > 0 && (
        <div className="card">
          <h3 className="card-title">🔗 服务依赖影响分析</h3>
          {results.dependencyResults.map((dr) => (
            <div
              key={dr.serviceId}
              style={{
                background: '#f7fafc',
                borderRadius: '8px',
                padding: '16px',
                marginBottom: '12px',
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: '12px' }}>
                {getServiceName(dr.serviceId)}
              </div>
              <div style={{ fontSize: '14px', color: '#4a5568' }}>
                <div>入口服务所需服务器: {dr.requiredServers} 台</div>
                <div>整体系统所需服务器: {dr.totalCapacity} 台</div>
                {Object.keys(dr.dependencyImpact).length > 0 && (
                  <div style={{ marginTop: '8px' }}>
                    <div style={{ marginBottom: '4px' }}>依赖影响占比:</div>
                    {Object.entries(dr.dependencyImpact).map(([depId, impact]) => (
                      <div key={depId} style={{ marginLeft: '16px' }}>
                        • {getServiceName(depId)}: {(impact * 100).toFixed(1)}%
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {results.calibrationFactors.length > 0 && (
        <div className="card">
          <h3 className="card-title">🎯 压测数据校准因子</h3>
          <div className="grid grid-3">
            {results.calibrationFactors.map((cf) => (
              <div key={cf.serviceId} className="result-card">
                <div className="result-label">{getServiceName(cf.serviceId)}</div>
                <div style={{ fontSize: '12px', marginTop: '8px' }}>
                  <div>CPU 校正: {(cf.cpuCorrection * 100).toFixed(0)}%</div>
                  <div>内存校正: {(cf.memoryCorrection * 100).toFixed(0)}%</div>
                  <div>延迟校正: {(cf.latencyCorrection * 100).toFixed(0)}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default ResultsDisplay;

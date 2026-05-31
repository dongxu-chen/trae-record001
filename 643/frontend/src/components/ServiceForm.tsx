import type { Service, ServerConfig } from '../types';

interface ServiceFormProps {
  services: Service[];
  setServices: (services: Service[]) => void;
  forecastPeriodDays: number;
  setForecastPeriodDays: (days: number) => void;
  targetUtilization: number;
  setTargetUtilization: (value: number) => void;
  maxLatencyMs: number;
  setMaxLatencyMs: (ms: number) => void;
  includeDependencies: boolean;
  setIncludeDependencies: (value: boolean) => void;
  serverConfigs: ServerConfig[];
  fetchServerConfigs: () => void;
}

function ServiceForm({
  services,
  setServices,
  forecastPeriodDays,
  setForecastPeriodDays,
  targetUtilization,
  setTargetUtilization,
  maxLatencyMs,
  setMaxLatencyMs,
  includeDependencies,
  setIncludeDependencies,
  serverConfigs,
}: ServiceFormProps) {
  const updateService = (index: number, field: keyof Service, value: string | string[]) => {
    const updated = [...services];
    if (field === 'dependencies') {
      updated[index][field] = (value as string).split(',').map(s => s.trim()).filter(Boolean);
    } else {
      updated[index][field] = value as string;
    }
    setServices(updated);
  };

  const addService = () => {
    setServices([
      ...services,
      { id: `service-${services.length + 1}`, name: '新服务', dependencies: [] },
    ]);
  };

  const removeService = (index: number) => {
    const updated = services.filter((_, i) => i !== index);
    setServices(updated);
  };

  return (
    <div>
      <div className="card">
        <h3 className="card-title">服务配置</h3>
        {services.map((service, index) => (
          <div key={service.id} className="service-item">
            <div style={{ flex: 1, marginRight: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 2fr', gap: '12px' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">服务ID</label>
                  <input
                    type="text"
                    className="form-input"
                    value={service.id}
                    onChange={(e) => updateService(index, 'id', e.target.value)}
                  />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">服务名称</label>
                  <input
                    type="text"
                    className="form-input"
                    value={service.name}
                    onChange={(e) => updateService(index, 'name', e.target.value)}
                  />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">依赖服务 (逗号分隔)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={service.dependencies.join(', ')}
                    onChange={(e) => updateService(index, 'dependencies', e.target.value)}
                    placeholder="例如: auth-service, database"
                  />
                </div>
              </div>
            </div>
            <button
              className="btn btn-secondary"
              onClick={() => removeService(index)}
              style={{ padding: '8px 16px' }}
            >
              删除
            </button>
          </div>
        ))}
        <button className="btn btn-secondary" onClick={addService} style={{ marginTop: '12px' }}>
          + 添加服务
        </button>
      </div>

      <div className="card">
        <h3 className="card-title">评估参数</h3>
        <div className="grid grid-3">
          <div className="form-group">
            <label className="form-label">预测周期 (天)</label>
            <input
              type="number"
              className="form-input"
              value={forecastPeriodDays}
              onChange={(e) => setForecastPeriodDays(parseInt(e.target.value) || 30)}
              min={1}
              max={365}
            />
          </div>
          <div className="form-group">
            <label className="form-label">目标利用率</label>
            <input
              type="number"
              className="form-input"
              value={targetUtilization}
              onChange={(e) => setTargetUtilization(parseFloat(e.target.value) || 0.7)}
              step={0.05}
              min={0.1}
              max={1}
            />
          </div>
          <div className="form-group">
            <label className="form-label">最大延迟 (ms)</label>
            <input
              type="number"
              className="form-input"
              value={maxLatencyMs}
              onChange={(e) => setMaxLatencyMs(parseInt(e.target.value) || 200)}
              min={10}
              max={5000}
            />
          </div>
        </div>
        <div className="checkbox-group">
          <input
            type="checkbox"
            id="includeDependencies"
            checked={includeDependencies}
            onChange={(e) => setIncludeDependencies(e.target.checked)}
          />
          <label htmlFor="includeDependencies" style={{ cursor: 'pointer' }}>
            考虑服务依赖影响
          </label>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">服务器配置 {serverConfigs.length > 0 && `(${serverConfigs.length} 种)`}</h3>
        {serverConfigs.length > 0 ? (
          <div className="grid grid-3">
            {serverConfigs.map((config) => (
              <div
                key={config.id}
                className="result-card"
                style={{ borderLeftColor: '#38a169' }}
              >
                <div className="result-label">{config.name}</div>
                <div style={{ fontSize: '12px', color: '#718096', marginTop: '8px' }}>
                  <div>CPU: {config.cpuCores} 核</div>
                  <div>内存: {config.memoryGB} GB</div>
                  <div>最大吞吐: {config.maxRequestsPerSec} req/s</div>
                  <div>成本: ${config.costPerHour}/小时</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: '#718096' }}>点击"加载服务器配置"按钮获取可用配置</p>
        )}
      </div>
    </div>
  );
}

export default ServiceForm;

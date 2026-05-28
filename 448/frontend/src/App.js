import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
} from '@mui/material';
import SpeedIcon from '@mui/icons-material/Speed';
import PoolConfigForm from './components/PoolConfigForm';
import WorkloadForm from './components/WorkloadForm';
import DatabaseConstraintForm from './components/DatabaseConstraintForm';
import SimulationResults from './components/SimulationResults';
import OptimizationResults from './components/OptimizationResults';
import RealTimeMonitor from './components/RealTimeMonitor';
import AutoTuningPanel from './components/AutoTuningPanel';
import SlowSqlPanel from './components/SlowSqlPanel';
import api from './services/api';

function App() {
  const [activeTab, setActiveTab] = useState(0);
  const [poolConfig, setPoolConfig] = useState(null);
  const [workload, setWorkload] = useState(null);
  const [dbConstraint, setDbConstraint] = useState(null);
  const [simulationResult, setSimulationResult] = useState(null);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedPoolType, setSelectedPoolType] = useState('HIKARICP');

  useEffect(() => {
    loadDefaultConfig();
    loadDefaultWorkload();
    loadDefaultConstraint();
  }, [selectedPoolType]);

  const loadDefaultConfig = async () => {
    try {
      const response = await api.getDefaultConfig(selectedPoolType);
      setPoolConfig(response.data);
    } catch (err) {
      console.error('Failed to load default config:', err);
    }
  };

  const loadDefaultWorkload = async () => {
    try {
      const response = await api.getDefaultWorkload();
      setWorkload(response.data);
    } catch (err) {
      console.error('Failed to load default workload:', err);
    }
  };

  const loadDefaultConstraint = async () => {
    try {
      const response = await api.getDefaultConstraint();
      setDbConstraint(response.data);
    } catch (err) {
      console.error('Failed to load default constraint:', err);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.simulate(poolConfig, workload);
      setSimulationResult(response.data);
      setActiveTab(1);
    } catch (err) {
      setError('模拟失败: ' + (err.response?.data?.message || err.message));
    } finally {
      setLoading(false);
    }
  };

  const buildOptimizeRequest = () => ({
    currentConfig: poolConfig,
    workload: workload,
    targetWaitTimeMs: 50,
    maxAllowedUtilization: 0.8,
    enableCostOptimization: true,
    databaseConstraint: dbConstraint,
  });

  const handleOptimize = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.optimize(buildOptimizeRequest());
      setOptimizationResult(response.data);
      setActiveTab(2);
    } catch (err) {
      setError('优化失败: ' + (err.response?.data?.message || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.compare(buildOptimizeRequest());
      setOptimizationResult(response.data);
      setActiveTab(2);
    } catch (err) {
      setError('对比分析失败: ' + (err.response?.data?.message || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 4, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <SpeedIcon color="primary" sx={{ fontSize: 40, mr: 2 }} />
          <Typography variant="h4" component="h1">
            数据库连接池优化工具
          </Typography>
        </Box>
        <Typography variant="body1" color="text.secondary">
          实时监控 + 自动调优 + 慢SQL分析 | MAP排队论 + 混合事务模拟 | HikariCP / Druid / Tomcat JDBC
        </Typography>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      )}

      <Tabs
        value={activeTab}
        onChange={(e, v) => setActiveTab(v)}
        sx={{ mb: 3 }}
        variant="scrollable"
        scrollButtons="auto"
      >
        <Tab label="配置设置" />
        <Tab label="模拟结果" disabled={!simulationResult} />
        <Tab label="优化建议" disabled={!optimizationResult} />
        <Tab label="实时监控" />
        <Tab label="自动调优" />
        <Tab label="慢SQL分析" />
      </Tabs>

      {activeTab === 0 && (
        <Box>
          <PoolConfigForm
            config={poolConfig}
            onChange={setPoolConfig}
            selectedPoolType={selectedPoolType}
            onPoolTypeChange={setSelectedPoolType}
          />
          <DatabaseConstraintForm
            constraint={dbConstraint}
            onChange={setDbConstraint}
          />
          <WorkloadForm
            workload={workload}
            onChange={setWorkload}
            onSimulate={handleSimulate}
            onOptimize={handleOptimize}
            onCompare={handleCompare}
            loading={loading}
          />
        </Box>
      )}

      {activeTab === 1 && simulationResult && (
        <SimulationResults result={simulationResult} />
      )}

      {activeTab === 2 && optimizationResult && (
        <OptimizationResults result={optimizationResult} />
      )}

      {activeTab === 3 && (
        <RealTimeMonitor poolConfig={poolConfig} workload={workload} />
      )}

      {activeTab === 4 && (
        <AutoTuningPanel poolConfig={poolConfig} workload={workload} />
      )}

      {activeTab === 5 && (
        <SlowSqlPanel />
      )}
    </Container>
  );
}

export default App;

import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import StatsPanel from './components/StatsPanel';
import EventList from './components/EventList';
import EventChart from './components/EventChart';
import RedisStatus from './components/RedisStatus';
import LatencyPanel from './components/LatencyPanel';
import HotKeyPanel from './components/HotKeyPanel';
import './App.css';

function App() {
  const [stats, setStats] = useState(null);
  const [events, setEvents] = useState([]);
  const [redisStatus, setRedisStatus] = useState(null);
  const [latency, setLatency] = useState(null);
  const [hotkeys, setHotkeys] = useState([]);
  const [samplingConfig, setSamplingConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchStats = useCallback(async () => {
    try {
      const response = await axios.get('/api/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const response = await axios.get('/api/events?limit=100');
      setEvents(response.data.events);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch events:', error);
    }
  }, []);

  const fetchRedisStatus = useCallback(async () => {
    try {
      const response = await axios.get('/api/redis/status');
      setRedisStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch redis status:', error);
    }
  }, []);

  const fetchLatency = useCallback(async () => {
    try {
      const response = await axios.get('/api/analytics/latency');
      setLatency(response.data.latency);
    } catch (error) {
        console.error('Failed to fetch latency:', error);
    }
  }, []);

  const fetchHotkeys = useCallback(async () => {
    try {
      const response = await axios.get('/api/analytics/hotkeys?limit=20');
      setHotkeys(response.data.hotkeys);
    } catch (error) {
      console.error('Failed to fetch hotkeys:', error);
    }
  }, []);

  const fetchSamplingConfig = useCallback(async () => {
    try {
      const response = await axios.get('/api/analytics/sampling');
      setSamplingConfig(response.data);
    } catch (error) {
      console.error('Failed to fetch sampling config:', error);
    }
  }, []);

  const clearEvents = async () => {
    try {
      await axios.delete('/api/events');
      setEvents([]);
      fetchStats();
    } catch (error) {
      console.error('Failed to clear events:', error);
    }
  };

  const resetAnalytics = async () => {
    try {
      await axios.delete('/api/analytics');
      setLatency(null);
      setHotkeys([]);
      fetchStats();
    } catch (error) {
      console.error('Failed to reset analytics:', error);
    }
  };

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      await Promise.all([
        fetchStats(), fetchEvents(), fetchRedisStatus(),
        fetchLatency(), fetchHotkeys(), fetchSamplingConfig()
      ]);
      setLoading(false);
    };
    fetchAll();

    const interval = setInterval(() => {
      fetchStats();
      fetchEvents();
      fetchRedisStatus();
      fetchLatency();
      fetchHotkeys();
    }, 3000);

    return () => clearInterval(interval);
  }, [fetchStats, fetchEvents, fetchRedisStatus, fetchLatency, fetchHotkeys, fetchSamplingConfig]);

  if (loading) {
    return (
      <div className="container">
        <div className="loading">加载中...</div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>Redis 键空间通知监控</h1>
            <p className="subtitle">实时监控 Redis 键的过期、删除、新增事件</p>
          </div>
          <RedisStatus status={redisStatus} />
        </div>
      </div>

      <StatsPanel stats={stats} />

      <div className="content-grid">
        <div className="card">
          <div className="card-header">
            <h2>事件分布</h2>
          </div>
          <div className="card-body">
            <EventChart stats={stats} />
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2>最近事件</h2>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <span className="refresh-indicator">
                最后更新: {lastUpdate?.toLocaleTimeString()}
              </span>
              <button className="btn btn-danger" onClick={clearEvents}>
                清空
              </button>
            </div>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <EventList events={events} />
          </div>
        </div>
      </div>

      <div className="content-grid">
        <LatencyPanel latency={latency} />
        <HotKeyPanel hotkeys={hotkeys} />
      </div>

      {samplingConfig && (
        <div className="card" style={{ marginTop: '24px' }}>
          <div className="card-header">
            <h2>采样配置</h2>
            <button className="btn btn-primary" onClick={resetAnalytics}>
              重置统计
            </button>
          </div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '4px' }}>
                  过期事件采样率
                </div>
                <div style={{ fontSize: '18px', fontWeight: 600 }}>
                  {(samplingConfig.EventTypeRates?.expired * 100).toFixed(0)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '4px' }}>
                  删除事件采样率
                </div>
                <div style={{ fontSize: '18px', fontWeight: 600 }}>
                  {(samplingConfig.EventTypeRates?.del * 100).toFixed(0)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '4px' }}>
                  新增事件采样率
                </div>
                <div style={{ fontSize: '18px', fontWeight: 600 }}>
                  {(samplingConfig.EventTypeRates?.set * 100).toFixed(0)}%
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#8c8c8c', marginBottom: '4px' }}>
                  动态调整阈值
                </div>
                <div style={{ fontSize: '18px', fontWeight: 600 }}>
                  {samplingConfig.ThresholdPerSec}/秒
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import JanusClient from '../utils/janusClient';

function ProctorPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { examId, userId, name } = location.state || {};
  
  const [isConnected, setIsConnected] = useState(false);
  const [publishers, setPublishers] = useState([]);
  const [activeSubscriptions, setActiveSubscriptions] = useState(new Map());
  const [alerts, setAlerts] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPublisher, setSelectedPublisher] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [viewMode, setViewMode] = useState('grid');
  
  const janusClientRef = useRef(null);
  const videoRefs = useRef(new Map());

  const addAlert = useCallback((alert) => {
    setAlerts(prev => [...prev.slice(-99), {
      ...alert,
      time: new Date().toLocaleTimeString()
    }]);
  }, []);

  const initJanus = useCallback(async () => {
    try {
      const janus = new JanusClient({
        server: 'ws://localhost:8188',
        apiSecret: 'janus-exam-secret-2024',
        roomId: 1234567890,
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' }
        ]
      });

      janus.on('joined', (data) => {
        console.log('[Janus] Joined room:', data);
        setIsConnected(true);
        if (data.publishers) {
          setPublishers(data.publishers);
        }
        addAlert({
          type: 'janus-connected',
          severity: 'success',
          message: '已连接到SFU服务器，开始监考'
        });
      });

      janus.on('publishers', (newPublishers) => {
        console.log('[Janus] New publishers:', newPublishers);
        setPublishers(prev => {
          const existing = new Map(prev.map(p => [p.id, p]));
          newPublishers.forEach(p => existing.set(p.id, p));
          return Array.from(existing.values());
        });
      });

      janus.on('publisherLeft', (publisherId) => {
        console.log('[Janus] Publisher left:', publisherId);
        setPublishers(prev => prev.filter(p => p.id !== publisherId));
        setActiveSubscriptions(prev => {
          const newMap = new Map(prev);
          newMap.delete(publisherId);
          return newMap;
        });
        addAlert({
          type: 'publisher-left',
          severity: 'warning',
          message: `考生 ${publisherId} 已离开`
        });
      });

      janus.on('track', (data) => {
        console.log('[Janus] Received track:', data);
        const videoElement = videoRefs.current.get(data.handleId);
        if (videoElement && data.stream) {
          videoElement.srcObject = data.stream;
        }
      });

      janus.on('error', (error) => {
        console.error('[Janus] Error:', error);
        addAlert({
          type: 'janus-error',
          severity: 'danger',
          message: 'SFU连接错误: ' + error.message
        });
      });

      janus.on('disconnected', () => {
        setIsConnected(false);
        addAlert({
          type: 'janus-disconnected',
          severity: 'warning',
          message: 'SFU连接已断开'
        });
      });

      await janus.connect();
      await janus.joinRoom(Number(userId), name, false);
      
      janusClientRef.current = janus;
    } catch (error) {
      console.error('Janus初始化失败:', error);
      addAlert({
        type: 'janus-init-error',
        severity: 'danger',
        message: 'SFU初始化失败: ' + error.message
      });
    }
  }, [userId, name, addAlert]);

  const subscribeToPublisher = useCallback(async (publisherId) => {
    if (!janusClientRef.current || activeSubscriptions.has(publisherId)) {
      return;
    }

    try {
      console.log(`[Proctor] Subscribing to publisher: ${publisherId}`);
      await janusClientRef.current.subscribe(publisherId);
      
      setActiveSubscriptions(prev => {
        const newMap = new Map(prev);
        newMap.set(publisherId, { subscribedAt: Date.now() });
        return newMap;
      });

      addAlert({
        type: 'subscribed',
        severity: 'info',
        message: `已订阅考生 ${publisherId} 的视频流`
      });
    } catch (error) {
      console.error('订阅失败:', error);
      addAlert({
        type: 'subscribe-error',
        severity: 'warning',
        message: `订阅考生 ${publisherId} 失败: ${error.message}`
      });
    }
  }, [activeSubscriptions, addAlert]);

  const unsubscribeFromPublisher = useCallback(async (publisherId) => {
    if (!janusClientRef.current || !activeSubscriptions.has(publisherId)) {
      return;
    }

    try {
      await janusClientRef.current.unsubscribe(publisherId);
      
      setActiveSubscriptions(prev => {
        const newMap = new Map(prev);
        newMap.delete(publisherId);
        return newMap;
      });

      addAlert({
        type: 'unsubscribed',
        severity: 'info',
        message: `已取消订阅考生 ${publisherId} 的视频流`
      });
    } catch (error) {
      console.error('取消订阅失败:', error);
    }
  }, [activeSubscriptions, addAlert]);

  const viewPublisherDetail = useCallback((publisher) => {
    setSelectedPublisher(publisher);
    setShowDetailModal(true);
    if (!activeSubscriptions.has(publisher.id)) {
      subscribeToPublisher(publisher.id);
    }
  }, [activeSubscriptions, subscribeToPublisher]);

  const closeDetailModal = useCallback(() => {
    setShowDetailModal(false);
    setSelectedPublisher(null);
  }, []);

  const batchSubscribe = useCallback(async (count = 9) => {
    const unsubscribed = publishers.filter(p => !activeSubscriptions.has(p.id));
    const toSubscribe = unsubscribed.slice(0, count);
    
    for (const publisher of toSubscribe) {
      await subscribeToPublisher(publisher.id);
    }
    
    addAlert({
      type: 'batch-subscribe',
      severity: 'info',
      message: `已批量订阅 ${toSubscribe.length} 位考生的视频流`
    });
  }, [publishers, activeSubscriptions, subscribeToPublisher, addAlert]);

  const clearAllSubscriptions = useCallback(async () => {
    for (const publisherId of activeSubscriptions.keys()) {
      await unsubscribeFromPublisher(publisherId);
    }
    addAlert({
      type: 'clear-subscriptions',
      severity: 'info',
      message: '已清除所有订阅'
    });
  }, [activeSubscriptions, unsubscribeFromPublisher, addAlert]);

  const filteredPublishers = useMemo(() => {
    if (!searchTerm) return publishers;
    return publishers.filter(p => 
      String(p.id).includes(searchTerm) ||
      (p.display && p.display.includes(searchTerm))
    );
  }, [publishers, searchTerm]);

  useEffect(() => {
    initJanus();

    return () => {
      if (janusClientRef.current) {
        janusClientRef.current.destroy();
      }
    };
  }, [initJanus]);

  const getSeverityColor = (severity) => {
    const colors = {
      'danger': '#dc3545',
      'warning': '#ffc107',
      'critical': '#dc3545',
      'info': '#17a2b8',
      'success': '#28a745'
    };
    return colors[severity] || '#6c757d';
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8f9fa', padding: '20px' }}>
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '20px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ margin: '0 0 5px 0', color: '#2c3e50' }}>在线考试监考中心</h2>
            <p style={{ margin: 0, color: '#666' }}>
              监考人: {name} | 考试ID: {examId} | 在线考生: {publishers.length} | 已订阅: {activeSubscriptions.size}
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                backgroundColor: isConnected ? '#28a745' : '#dc3545'
              }}></div>
              <span style={{ color: isConnected ? '#28a745' : '#dc3545', fontWeight: 500 }}>
                {isConnected ? 'SFU已连接' : 'SFU未连接'}
              </span>
            </div>
            <button
              onClick={() => navigate('/')}
              style={{
                padding: '8px 16px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
            >
              返回首页
            </button>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '20px' }}>
        <div>
          <div style={{
            background: 'white',
            borderRadius: '12px',
            padding: '20px',
            marginBottom: '20px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0, color: '#2c3e50' }}>考生监控</h3>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '5px' }}>
                  <button
                    onClick={() => setViewMode('grid')}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: viewMode === 'grid' ? '#007bff' : '#e9ecef',
                      color: viewMode === 'grid' ? 'white' : '#495057',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    网格视图
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: viewMode === 'list' ? '#007bff' : '#e9ecef',
                      color: viewMode === 'list' ? 'white' : '#495057',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    列表视图
                  </button>
                </div>
                <input
                  type="text"
                  placeholder="搜索考生ID或名称..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{
                    padding: '8px 12px',
                    border: '1px solid #ddd',
                    borderRadius: '6px',
                    width: '200px'
                  }}
                />
                <button
                  onClick={batchSubscribe}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer'
                  }}
                >
                  批量订阅 (9个)
                </button>
                <button
                  onClick={clearAllSubscriptions}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#dc3545',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer'
                  }}
                >
                  清除所有
                </button>
              </div>
            </div>

            {filteredPublishers.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: '#6c757d' }}>
                <div style={{ fontSize: '48px', marginBottom: '10px' }}>⏳</div>
                <p style={{ fontSize: '16px' }}>暂无考生加入，请等待考生进入考试</p>
              </div>
            ) : viewMode === 'grid' ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px' }}>
                {filteredPublishers.map((publisher) => {
                  const isSubscribed = activeSubscriptions.has(publisher.id);
                  
                  return (
                    <div
                      key={publisher.id}
                      style={{
                        border: `2px solid ${isSubscribed ? '#28a745' : '#ddd'}`,
                        borderRadius: '10px',
                        overflow: 'hidden',
                        backgroundColor: 'white',
                        transition: 'all 0.2s'
                      }}
                    >
                      <div style={{
                        position: 'relative',
                        backgroundColor: '#000',
                        aspectRatio: '4/3'
                      }}>
                        {isSubscribed ? (
                          <video
                            ref={(el) => {
                              if (el) videoRefs.current.set(publisher.id, el);
                            }}
                            autoPlay
                            muted
                            playsInline
                            style={{
                              width: '100%',
                              height: '100%',
                              objectFit: 'cover'
                            }}
                          />
                        ) : (
                          <div style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            height: '100%',
                            color: '#6c757d'
                          }}>
                            <div style={{ fontSize: '32px', marginBottom: '8px' }}>📹</div>
                            <span style={{ fontSize: '12px' }}>点击订阅</span>
                          </div>
                        )}
                        <div style={{
                          position: 'absolute',
                          top: '8px',
                          right: '8px',
                          padding: '4px 8px',
                          backgroundColor: isSubscribed ? 'rgba(40, 167, 69, 0.9)' : 'rgba(108, 117, 125, 0.9)',
                          color: 'white',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 500
                        }}>
                          {isSubscribed ? '● 监控中' : '○ 未订阅'}
                        </div>
                      </div>
                      <div style={{ padding: '12px' }}>
                        <div style={{
                          fontSize: '13px',
                          fontWeight: 600,
                          color: '#2c3e50',
                          marginBottom: '4px',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                        }}>
                          {publisher.display || '未知考生'}
                        </div>
                        <div style={{
                          fontSize: '11px',
                          color: '#6c757d',
                          marginBottom: '10px'
                        }}>
                          ID: {publisher.id}
                        </div>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          {isSubscribed ? (
                            <button
                              onClick={() => unsubscribeFromPublisher(publisher.id)}
                              style={{
                                flex: 1,
                                padding: '6px',
                                backgroundColor: '#dc3545',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '12px',
                                cursor: 'pointer'
                              }}
                            >
                              取消订阅
                            </button>
                          ) : (
                            <button
                              onClick={() => subscribeToPublisher(publisher.id)}
                              style={{
                                flex: 1,
                                padding: '6px',
                                backgroundColor: '#007bff',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '12px',
                                cursor: 'pointer'
                              }}
                            >
                              订阅
                            </button>
                          )}
                          <button
                            onClick={() => viewPublisherDetail(publisher)}
                            style={{
                              flex: 1,
                              padding: '6px',
                              backgroundColor: '#17a2b8',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              fontSize: '12px',
                              cursor: 'pointer'
                            }}
                          >
                            详情
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#f8f9fa' }}>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>考生ID</th>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>考生名称</th>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>状态</th>
                      <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #dee2e6' }}>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPublishers.map((publisher) => {
                      const isSubscribed = activeSubscriptions.has(publisher.id);
                      return (
                        <tr key={publisher.id} style={{ borderBottom: '1px solid #dee2e6' }}>
                          <td style={{ padding: '12px' }}>{publisher.id}</td>
                          <td style={{ padding: '12px' }}>{publisher.display || '未知考生'}</td>
                          <td style={{ padding: '12px' }}>
                            <span style={{
                              padding: '4px 8px',
                              backgroundColor: isSubscribed ? '#d4edda' : '#f8d7da',
                              color: isSubscribed ? '#155724' : '#721c24',
                              borderRadius: '4px',
                              fontSize: '12px'
                            }}>
                              {isSubscribed ? '已订阅' : '未订阅'}
                            </span>
                          </td>
                          <td style={{ padding: '12px' }}>
                            {isSubscribed ? (
                              <button
                                onClick={() => unsubscribeFromPublisher(publisher.id)}
                                style={{
                                  padding: '6px 12px',
                                  backgroundColor: '#dc3545',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  fontSize: '12px',
                                  cursor: 'pointer',
                                  marginRight: '8px'
                                }}
                              >
                                取消订阅
                              </button>
                            ) : (
                              <button
                                onClick={() => subscribeToPublisher(publisher.id)}
                                style={{
                                  padding: '6px 12px',
                                  backgroundColor: '#007bff',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '4px',
                                  fontSize: '12px',
                                  cursor: 'pointer',
                                  marginRight: '8px'
                                }}
                              >
                                订阅
                              </button>
                            )}
                            <button
                              onClick={() => viewPublisherDetail(publisher)}
                              style={{
                                padding: '6px 12px',
                                backgroundColor: '#17a2b8',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                fontSize: '12px',
                                cursor: 'pointer'
                              }}
                            >
                              查看详情
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div>
          <div style={{
            background: 'white',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            maxHeight: 'calc(100vh - 120px)',
            overflowY: 'auto'
          }}>
            <h3 style={{ margin: '0 0 15px 0', color: '#2c3e50' }}>
              告警日志
              <span style={{
                marginLeft: '10px',
                padding: '2px 8px',
                backgroundColor: '#dc3545',
                color: 'white',
                borderRadius: '10px',
                fontSize: '12px'
              }}>
                {alerts.filter(a => a.severity === 'danger' || a.severity === 'critical').length}
              </span>
            </h3>
            {alerts.length === 0 ? (
              <p style={{ color: '#6c757d', textAlign: 'center', padding: '40px 20px' }}>暂无告警</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {[...alerts].reverse().map((alert, index) => (
                  <div
                    key={index}
                    style={{
                      padding: '10px 12px',
                      borderRadius: '6px',
                      fontSize: '13px',
                      backgroundColor: 
                        alert.severity === 'danger' || alert.severity === 'critical' ? '#fff5f5' :
                        alert.severity === 'warning' ? '#fffbf0' :
                        alert.severity === 'success' ? '#f0fff4' : '#f8f9fa',
                      borderLeft: `4px solid ${getSeverityColor(alert.severity)}`
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <strong style={{ color: '#2c3e50' }}>{alert.type}</strong>
                      <span style={{ color: '#6c757d', fontSize: '11px' }}>{alert.time}</span>
                    </div>
                    <div style={{ color: '#495057' }}>{alert.message}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {showDetailModal && selectedPublisher && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'white',
            borderRadius: '12px',
            width: '90%',
            maxWidth: '900px',
            maxHeight: '90vh',
            overflow: 'auto'
          }}>
            <div style={{
              padding: '20px',
              borderBottom: '1px solid #eee',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <h3 style={{ margin: 0, color: '#2c3e50' }}>
                考生详情: {selectedPublisher.display || selectedPublisher.id}
              </h3>
              <button
                onClick={closeDetailModal}
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  border: 'none',
                  backgroundColor: '#e9ecef',
                  cursor: 'pointer',
                  fontSize: '18px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                ×
              </button>
            </div>
            <div style={{ padding: '20px' }}>
              <div style={{
                backgroundColor: '#000',
                borderRadius: '8px',
                aspectRatio: '16/9',
                marginBottom: '20px',
                overflow: 'hidden'
              }}>
                {activeSubscriptions.has(selectedPublisher.id) ? (
                  <video
                    ref={(el) => {
                      if (el) videoRefs.current.set(`detail_${selectedPublisher.id}`, el);
                    }}
                    autoPlay
                    muted
                    playsInline
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'contain'
                    }}
                  />
                ) : (
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    height: '100%',
                    color: '#6c757d'
                  }}>
                    <div style={{ fontSize: '48px', marginBottom: '10px' }}>⏳</div>
                    <span>正在加载视频流...</span>
                  </div>
                )}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div>
                  <h4 style={{ margin: '0 0 10px 0', color: '#2c3e50' }}>基本信息</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#6c757d' }}>考生ID:</span>
                      <span style={{ fontWeight: 500 }}>{selectedPublisher.id}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#6c757d' }}>考生名称:</span>
                      <span style={{ fontWeight: 500 }}>{selectedPublisher.display || '-'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#6c757d' }}>订阅状态:</span>
                      <span style={{
                        fontWeight: 500,
                        color: activeSubscriptions.has(selectedPublisher.id) ? '#28a745' : '#dc3545'
                      }}>
                        {activeSubscriptions.has(selectedPublisher.id) ? '已订阅' : '未订阅'}
                      </span>
                    </div>
                  </div>
                </div>
                <div>
                  <h4 style={{ margin: '0 0 10px 0', color: '#2c3e50' }}>操作</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {activeSubscriptions.has(selectedPublisher.id) ? (
                      <button
                        onClick={() => unsubscribeFromPublisher(selectedPublisher.id)}
                        style={{
                          padding: '10px',
                          backgroundColor: '#dc3545',
                          color: 'white',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '14px'
                        }}
                      >
                        取消订阅
                      </button>
                    ) : (
                      <button
                        onClick={() => subscribeToPublisher(selectedPublisher.id)}
                        style={{
                          padding: '10px',
                          backgroundColor: '#007bff',
                          color: 'white',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          fontSize: '14px'
                        }}
                      >
                        订阅视频流
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProctorPage;

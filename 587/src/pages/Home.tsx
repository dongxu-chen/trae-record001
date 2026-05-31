import React, { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import Toolbar from '../components/Toolbar';
import ChartWithAnnotations from '../components/ChartWithAnnotations';
import AnnotationPanel from '../components/AnnotationPanel';
import CollaborationBar from '../components/CollaborationBar';
import ShareDialog from '../components/ShareDialog';
import AIRecommendationPanel from '../components/AIRecommendationPanel';
import { useStore } from '../store/useStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { USER_COLORS } from '../../shared/types';
import { User } from '../../shared/types';
import { analyzeChartData } from '../utils/aiAnalysis';

const sampleChartData = {
  xAxis: {
    type: 'category',
    data: ['一月', '二月', '三月', '四月', '五月', '六月', '七月'],
  },
  yAxis: {
    type: 'value',
  },
  series: [
    {
      data: [820, 932, 901, 934, 1290, 1330, 1320],
      type: 'line',
      smooth: true,
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(59, 130, 246, 0.4)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.05)' },
          ],
        },
      },
      lineStyle: {
        color: '#3b82f6',
        width: 3,
      },
      itemStyle: {
        color: '#3b82f6',
      },
    },
  ],
};

const Home: React.FC = () => {
  const [showNameInput, setShowNameInput] = useState(true);
  const [userName, setUserName] = useState('');
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const {
    sessionId,
    chartData,
    currentUser,
    permissions,
    setSessionId,
    setCurrentUser,
    setChartData,
    reset,
    setAIRecommendations,
    setIsAnalyzing,
    isAnalyzing,
    aiRecommendations,
  } = useStore();

  const { connect, disconnect } = useWebSocket();

  const createSession = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ chartData: sampleChartData, chartType: 'line' }),
      });
      const data = await response.json();
      
      if (data.sessionId) {
        setSessionId(data.sessionId);
        setChartData(sampleChartData);

        const user: User = {
          id: uuidv4(),
          name: userName,
          color: USER_COLORS[Math.floor(Math.random() * USER_COLORS.length)],
        };
        setCurrentUser(user);
        
        connect(data.sessionId, user);
        setShowNameInput(false);
      }
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setIsLoading(false);
    }
  }, [userName, setSessionId, setChartData, setCurrentUser, connect]);

  const handleDisconnect = useCallback(() => {
    disconnect();
    reset();
    setShowNameInput(true);
    setUserName('');
  }, [disconnect, reset]);

  const handleExportImage = useCallback(() => {
    alert('导出图片功能 - 图表与注释将合并为图片');
  }, []);

  const handleExportJSON = useCallback(() => {
    const { annotations } = useStore.getState();
    const dataStr = JSON.stringify(annotations, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'annotations.json';
    link.click();
    URL.revokeObjectURL(url);
  }, []);

  const handleAIAnalysis = useCallback(() => {
    if (!chartData) return;

    setIsAnalyzing(true);
    
    setTimeout(() => {
      const result = analyzeChartData(chartData);
      setAIRecommendations(result.recommendations);
      setIsAnalyzing(false);
      setAiPanelOpen(true);
    }, 800);
  }, [chartData, setIsAnalyzing, setAIRecommendations]);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const shareId = urlParams.get('share');
    
    if (shareId) {
      fetch(`/api/share/${shareId}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.sessionId) {
            setSessionId(data.sessionId);
          }
        })
        .catch(console.error);
    }
  }, [setSessionId]);

  if (showNameInput) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">ChartAnnotate</h1>
            <p className="text-gray-500">在图表上添加注释，与团队实时协作</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                输入你的名字
              </label>
              <input
                type="text"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                placeholder="例如：张三"
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && userName.trim()) {
                    createSession();
                  }
                }}
              />
            </div>

            <button
              onClick={createSession}
              disabled={!userName.trim() || isLoading}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-xl font-medium hover:from-blue-700 hover:to-cyan-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/30"
            >
              {isLoading ? '创建中...' : '开始协作'}
            </button>
          </div>

          <div className="mt-8 pt-6 border-t border-gray-100">
            <p className="text-xs text-gray-400 text-center">
              支持文本、箭头、高亮三种注释类型 · 实时多人协作 · 一键导出分享
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <Toolbar
        onExportImage={handleExportImage}
        onExportJSON={handleExportJSON}
        onShare={() => setShareDialogOpen(true)}
        onDisconnect={handleDisconnect}
        onAIAnalysis={handleAIAnalysis}
      />

      {permissions === 'read' && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center justify-center gap-2">
          <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <span className="text-sm text-amber-700">
            只读模式 - 您可以查看注释，但无法编辑。如需编辑请联系分享者获取可编辑权限。
          </span>
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 p-6 relative">
          {chartData ? (
            <>
              <ChartWithAnnotations chartData={chartData} chartType="line" />
              <CollaborationBar />
            </>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-400">
                <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <p>加载图表数据中...</p>
              </div>
            </div>
          )}
        </div>

        <AnnotationPanel onAIAnalysis={handleAIAnalysis} />
      </div>

      {sessionId && (
        <ShareDialog
          isOpen={shareDialogOpen}
          onClose={() => setShareDialogOpen(false)}
          sessionId={sessionId}
        />
      )}

      <AIRecommendationPanel
        isOpen={aiPanelOpen}
        onClose={() => setAiPanelOpen(false)}
      />
    </div>
  );
};

export default Home;

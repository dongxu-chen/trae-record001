import { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  FileText,
  AlertTriangle,
  TrendingUp,
  Users,
  Target,
  Award,
  BarChart3,
  CheckCircle2,
  GitMerge,
} from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';
import { useStore } from '../stores/useStore';
import type { Annotation } from '../types';
import { calculateKappa, getKappaColor, getKappaLabel, type KappaResult } from '../utils/kappa';

export const StatisticsPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentProject, setCurrentProject, projects, annotations } = useStore();
  const [userStats, setUserStats] = useState<
    Map<string, { name: string; count: number; color: string }>
  >(new Map());

  useEffect(() => {
    const project = projects.find((p) => p.id === id);
    if (project) {
      setCurrentProject(project);
    } else {
      navigate('/');
    }
  }, [id]);

  useEffect(() => {
    const stats = new Map<string, { name: string; count: number; color: string }>();
    projectAnnotations.forEach((a) => {
      const existing = stats.get(a.createdBy) || {
        name: a.createdBy,
        count: 0,
        color: '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0'),
      };
      stats.set(a.createdBy, { ...existing, count: existing.count + 1 });
    });
    setUserStats(stats);
  }, [annotations, id]);

  if (!currentProject) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  const projectAnnotations = annotations.filter((a) => a.projectId === currentProject.id);

  const kappaResult: KappaResult = useMemo(() => {
    return calculateKappa(projectAnnotations, currentProject.dataPoints.length);
  }, [projectAnnotations, currentProject.dataPoints.length]);

  const stats = {
    total: projectAnnotations.length,
    classification: projectAnnotations.filter((a) => a.type === 'classification').length,
    anomaly: projectAnnotations.filter((a) => a.type === 'anomaly').length,
    trend: projectAnnotations.filter((a) => a.type === 'trend').length,
    coverage:
      currentProject.dataPoints.length > 0
        ? (
            (new Set(projectAnnotations.map((a) => a.dataPointIndex)).size /
              currentProject.dataPoints.length) *
            100
          ).toFixed(1)
        : 0,
  };

  const typeChartOption: EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(30, 41, 59, 0.95)',
      borderColor: '#475569',
      textStyle: { color: '#e2e8f0' },
    },
    legend: {
      orient: 'horizontal',
      bottom: 0,
      textStyle: { color: '#94a3b8' },
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#1e293b',
          borderWidth: 2,
        },
        label: { show: false },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
            color: '#fff',
          },
        },
        labelLine: { show: false },
        data: [
          { value: stats.classification, name: '分类标注', itemStyle: { color: '#3b82f6' } },
          { value: stats.anomaly, name: '异常标记', itemStyle: { color: '#ef4444' } },
          { value: stats.trend, name: '趋势标注', itemStyle: { color: '#22c55e' } },
        ],
      },
    ],
  };

  const sortedUsers = Array.from(userStats.entries())
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 10);

  const userChartOption: EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(30, 41, 59, 0.95)',
      borderColor: '#475569',
      textStyle: { color: '#e2e8f0' },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#334155' } },
    },
    yAxis: {
      type: 'category',
      data: sortedUsers.map(([name]) => name),
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#94a3b8' },
    },
    series: [
      {
        type: 'bar',
        data: sortedUsers.map(([_, data]) => ({
          value: data.count,
          itemStyle: { color: data.color },
        })),
        barWidth: '60%',
        itemStyle: {
          borderRadius: [0, 4, 4, 0],
        },
      },
    ],
  };

  const kappaChartOption: EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(30, 41, 59, 0.95)',
      borderColor: '#475569',
      textStyle: { color: '#e2e8f0' },
      formatter: '{b}: {c} ({d}%)',
    },
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 1,
        splitNumber: 5,
        radius: '90%',
        axisLine: {
          lineStyle: {
            width: 20,
            color: [
              [0.2, '#ef4444'],
              [0.4, '#f97316'],
              [0.6, '#eab308'],
              [0.8, '#84cc16'],
              [1, '#10b981'],
            ],
          },
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '60%',
          width: 12,
          offsetCenter: [0, '-20%'],
          itemStyle: {
            color: 'auto',
          },
        },
        axisTick: {
          length: 8,
          lineStyle: {
            color: 'auto',
            width: 2,
          },
        },
        splitLine: {
          length: 15,
          lineStyle: {
            color: 'auto',
            width: 3,
          },
        },
        axisLabel: {
          color: '#94a3b8',
          fontSize: 12,
          distance: 25,
          formatter: (value: number) => value.toFixed(1),
        },
        title: {
          offsetCenter: [0, '20%'],
          fontSize: 14,
          color: '#94a3b8',
        },
        detail: {
          fontSize: 24,
          offsetCenter: [0, 0],
          valueAnimation: true,
          formatter: (value: number) => value.toFixed(2),
          color: 'auto',
        },
        data: [
          {
            value: Math.max(0, kappaResult.kappa),
            name: getKappaLabel(kappaResult.kappa),
          },
        ],
      },
    ],
  };

  const recentAnnotations = [...projectAnnotations]
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, 10);

  return (
    <div className="p-8">
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => navigate(`/project/${id}`)}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          返回标注
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">标注统计</h1>
          <p className="text-slate-400">{currentProject.name}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
        <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center">
              <FileText className="w-6 h-6 text-blue-400" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white">{stats.total}</p>
          <p className="text-slate-400 text-sm">总标注数</p>
        </div>

        <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-red-600/20 rounded-xl flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-red-400" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white">{stats.anomaly}</p>
          <p className="text-slate-400 text-sm">异常标记</p>
        </div>

        <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-green-600/20 rounded-xl flex items-center justify-center">
              <Target className="w-6 h-6 text-green-400" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white">{stats.coverage}%</p>
          <p className="text-slate-400 text-sm">数据点覆盖率</p>
        </div>

        <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-cyan-600/20 rounded-xl flex items-center justify-center">
              <Users className="w-6 h-6 text-cyan-400" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white">{userStats.size}</p>
          <p className="text-slate-400 text-sm">参与用户</p>
        </div>

        <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-purple-600/20 rounded-xl flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6 text-purple-400" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white" style={{ color: getKappaColor(kappaResult.kappa) }}>
            {kappaResult.kappa.toFixed(2)}
          </p>
          <p className="text-slate-400 text-sm">Kappa 一致性系数</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-6">标注类型分布</h3>
          <ReactECharts
            option={typeChartOption}
            style={{ height: '300px' }}
            opts={{ renderer: 'canvas' }}
          />
        </div>

        <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-6">标注员一致性 (Cohen's Kappa)</h3>
          <ReactECharts
            option={kappaChartOption}
            style={{ height: '250px' }}
            opts={{ renderer: 'canvas' }}
          />
          <div className="mt-4 text-center">
            <p
              className="text-lg font-semibold"
              style={{ color: getKappaColor(kappaResult.kappa) }}
            >
              {kappaResult.interpretation}
            </p>
            <p className="text-sm text-slate-400 mt-1">
              观察一致率: {(kappaResult.agreement * 100).toFixed(1)}% | 机遇一致率:{' '}
              {(kappaResult.chanceAgreement * 100).toFixed(1)}%
            </p>
          </div>
        </div>

        <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-6">用户贡献排行</h3>
          <ReactECharts
            option={userChartOption}
            style={{ height: '300px' }}
            opts={{ renderer: 'canvas' }}
          />
        </div>
      </div>

      {kappaResult.pairResults.length > 0 && (
        <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700 mb-8">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <GitMerge className="w-5 h-5" />
            成对一致性分析
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">
                    标注员 1
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">
                    标注员 2
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">
                    Kappa 系数
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">
                    一致程度
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">
                    观察一致率
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">
                    机遇一致率
                  </th>
                </tr>
              </thead>
              <tbody>
                {kappaResult.pairResults.map((pair, index) => (
                  <tr key={index} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="py-3 px-4 text-sm text-white">{pair.user1}</td>
                    <td className="py-3 px-4 text-sm text-white">{pair.user2}</td>
                    <td className="py-3 px-4">
                      <span
                        className="font-mono font-bold"
                        style={{ color: getKappaColor(pair.kappa) }}
                      >
                        {pair.kappa.toFixed(3)}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className="px-2 py-1 text-xs font-medium rounded-full"
                        style={{
                          backgroundColor: getKappaColor(pair.kappa) + '30',
                          color: getKappaColor(pair.kappa),
                        }}
                      >
                        {getKappaLabel(pair.kappa)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-300">
                      {(pair.agreement * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-300">
                      {(pair.chanceAgreement * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-6">最近标注</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">时间</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">类型</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">标签</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">数据点</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">标注者</th>
              </tr>
            </thead>
            <tbody>
              {recentAnnotations.map((annotation) => (
                <tr
                  key={annotation.id}
                  className="border-b border-slate-700/50 hover:bg-slate-700/30"
                >
                  <td className="py-3 px-4 text-sm text-slate-300">
                    {new Date(annotation.createdAt).toLocaleString()}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className="px-2 py-1 text-xs font-medium rounded-full"
                      style={{
                        backgroundColor: (annotation.color || '#6b7280') + '30',
                        color: annotation.color || '#6b7280',
                      }}
                    >
                      {annotation.type === 'classification'
                        ? '分类'
                        : annotation.type === 'anomaly'
                          ? '异常'
                          : '趋势'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-white">{annotation.label}</td>
                  <td className="py-3 px-4 text-sm text-slate-400">#{annotation.dataPointIndex}</td>
                  <td className="py-3 px-4 text-sm text-slate-300">{annotation.createdBy}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

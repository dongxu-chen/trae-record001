import { useEffect } from 'react';
import ChartDrill from '@/components/ChartDrill';
import Breadcrumb from '@/components/Breadcrumb';
import StatusPanel from '@/components/StatusPanel';
import {
  useDrillStore,
  useIsLoading,
  useRelatedCharts,
  useLinkRelatedCharts,
} from '@/hooks/useDrillStore';
import { useDrillUrlSync } from '@/hooks/useDrillUrlSync';
import { getDataByPath } from '@/data/mockData';
import { pathToNames } from '@/utils/drillUtils';
import {
  BarChart3,
  Zap,
  Target,
  Eye,
  Link,
  Shield,
  TrendingUp,
  Users,
} from 'lucide-react';
import {
  PageSkeleton,
  BreadcrumbSkeleton,
  StatusPanelSkeleton,
  ChartSkeleton,
} from '@/components/Skeleton';

export default function Home() {
  useDrillUrlSync();

  const { path, setCurrentData } = useDrillStore();
  const isLoading = useIsLoading();
  const relatedCharts = useRelatedCharts();
  const linkRelatedCharts = useLinkRelatedCharts();

  useEffect(() => {
    const names = pathToNames(path);
    const data = getDataByPath(names);
    if (data) {
      setCurrentData(data);
    }
  }, [path]);

  const features = [
    {
      icon: BarChart3,
      title: '多图表支持',
      desc: '柱状图、饼图、折线图自由切换',
    },
    {
      icon: Zap,
      title: '多级钻取',
      desc: '全国→省份→城市→区县逐层探索',
    },
    {
      icon: Target,
      title: '状态快照',
      desc: '撤销/重做，历史快照任意跳转',
    },
    {
      icon: Eye,
      title: '预测钻取',
      desc: '智能预测下一层级数据趋势',
    },
    {
      icon: Link,
      title: '关联钻取',
      desc: '多图表同步下钻分析',
    },
    {
      icon: Shield,
      title: '权限控制',
      desc: '角色级数据访问权限管理',
    },
  ];

  const activeRelatedCharts = relatedCharts.filter((c) => c.isActive && c.id !== 'chart-sales');

  if (isLoading) {
    return <PageSkeleton />;
  }

  return (
    <div className="relative z-10 min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <header className="text-center mb-10 animate-fade-in">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-500/10 border border-cyan-500/20 rounded-full text-cyan-400 text-sm font-medium mb-6">
            <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
            交互式数据可视化
          </div>

          <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4 font-display tracking-tight">
            图表
            <span className="bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 bg-clip-text text-transparent">
              钻取分析
            </span>
            平台
          </h1>

          <p className="text-slate-400 text-lg max-w-2xl mx-auto mb-8">
            点击图表元素逐层深入，从宏观到微观，探索数据背后的洞察。支持预测钻取、关联钻取、权限控制。
          </p>

          <div className="flex flex-wrap justify-center gap-4">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div
                  key={feature.title}
                  className="flex items-center gap-3 px-5 py-3 bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl animate-stagger"
                >
                  <div className="w-10 h-10 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-lg flex items-center justify-center">
                    <Icon className="w-5 h-5 text-cyan-400" />
                  </div>
                  <div className="text-left">
                    <div className="text-white font-semibold text-sm">
                      {feature.title}
                    </div>
                    <div className="text-slate-400 text-xs">{feature.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </header>

        <main className="space-y-6">
          <div className="animate-stagger" style={{ animationDelay: '0.5s' }}>
            <Breadcrumb />
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 animate-stagger" style={{ animationDelay: '0.6s' }}>
              <div className="bg-slate-800/60 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50 h-full">
                <ChartDrill dimension="sales" chartId="chart-sales" />
              </div>
            </div>

            <div className="lg:col-span-1 animate-stagger" style={{ animationDelay: '0.7s' }}>
              <StatusPanel />
            </div>
          </div>

          {activeRelatedCharts.length > 0 && (
            <div
              className="animate-stagger"
              style={{ animationDelay: '0.75s' }}
            >
              <div className="flex items-center gap-2 mb-4">
                <Link
                  className={`w-5 h-5 ${
                    linkRelatedCharts ? 'text-purple-400' : 'text-slate-500'
                  }`}
                />
                <h3 className="text-lg font-semibold text-white">
                  关联图表
                  {linkRelatedCharts && (
                    <span className="ml-2 text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded-full">
                      同步中
                    </span>
                  )}
                </h3>
              </div>
              <div className="grid md:grid-cols-2 gap-6">
                {activeRelatedCharts.map((chart, index) => (
                  <div
                    key={chart.id}
                    className="bg-slate-800/60 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50 animate-stagger"
                    style={{ animationDelay: `${0.8 + index * 0.1}s` }}
                  >
                    <ChartDrill
                      dimension={chart.dimension}
                      chartId={chart.id}
                      title={`${chart.title} - ${chart.currentLevel > 0 ? path[path.length - 1]?.name || '全国' : '全国'}`}
                      showControls={false}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="animate-stagger" style={{ animationDelay: '0.9s' }}>
            <div className="bg-slate-800/40 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <span className="w-1.5 h-6 bg-gradient-to-b from-emerald-400 to-green-500 rounded-full" />
                使用说明
              </h3>
              <div className="grid md:grid-cols-3 gap-4">
                {[
                  {
                    step: '01',
                    title: '选择图表类型',
                    desc: '在图表右上角切换柱状图、饼图或折线图',
                    icon: BarChart3,
                  },
                  {
                    step: '02',
                    title: '点击下钻',
                    desc: '点击有"可下钻"标记的数据项，进入下一层级',
                    icon: Zap,
                  },
                  {
                    step: '03',
                    title: '预测分析',
                    desc: '开启预测功能，查看下一层级数据预测',
                    icon: Eye,
                  },
                  {
                    step: '04',
                    title: '关联钻取',
                    desc: '开启关联同步，多图表同时下钻分析',
                    icon: Link,
                  },
                  {
                    step: '05',
                    title: '角色切换',
                    desc: '切换不同角色，体验权限控制效果',
                    icon: Users,
                  },
                  {
                    step: '06',
                    title: '撤销重做',
                    desc: '使用撤销重做按钮或历史快照快速回退',
                    icon: Target,
                  },
                ].map((item) => {
                  const Icon = item.icon;
                  return (
                    <div key={item.step} className="flex gap-4">
                      <div className="text-3xl font-bold font-display bg-gradient-to-br from-cyan-400 to-blue-500 bg-clip-text text-transparent shrink-0">
                        {item.step}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 text-white font-medium mb-1">
                          <Icon className="w-4 h-4 text-cyan-400" />
                          {item.title}
                        </div>
                        <div className="text-slate-400 text-sm">
                          {item.desc}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="animate-stagger" style={{ animationDelay: '1s' }}>
            <div className="bg-gradient-to-r from-purple-500/10 via-blue-500/10 to-cyan-500/10 backdrop-blur-sm rounded-2xl p-6 border border-purple-500/20">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5 text-purple-400" />
                权限等级说明
              </h3>
              <div className="grid md:grid-cols-3 gap-4">
                {[
                  {
                    role: '管理员',
                    level: 'Lv.3',
                    desc: '可钻取至区县层级，可查看所有敏感数据',
                    color: 'from-purple-500 to-pink-500',
                    features: ['全国', '省份', '城市', '区县', '敏感数据'],
                  },
                  {
                    role: '经理',
                    level: 'Lv.2',
                    desc: '可钻取至城市层级，可查看敏感数据',
                    color: 'from-blue-500 to-cyan-500',
                    features: ['全国', '省份', '城市', '敏感数据'],
                  },
                  {
                    role: '查看者',
                    level: 'Lv.1',
                    desc: '仅可查看省级数据，不可查看敏感数据',
                    color: 'from-slate-500 to-slate-600',
                    features: ['全国', '省份'],
                  },
                ].map((item) => (
                  <div
                    key={item.role}
                    className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/50"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-8 h-8 rounded-lg bg-gradient-to-br ${item.color} flex items-center justify-center`}
                        >
                          <Users className="w-4 h-4 text-white" />
                        </div>
                        <span className="text-white font-semibold">
                          {item.role}
                        </span>
                      </div>
                      <span className="text-xs px-2 py-1 bg-slate-700/50 text-slate-300 rounded">
                        {item.level}
                      </span>
                    </div>
                    <p className="text-slate-400 text-sm mb-3">{item.desc}</p>
                    <div className="flex flex-wrap gap-1">
                      {item.features.map((feature) => (
                        <span
                          key={feature}
                          className="text-xs px-2 py-0.5 bg-slate-700/30 text-slate-300 rounded"
                        >
                          {feature}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>

        <footer className="mt-12 pt-8 border-t border-slate-700/50 text-center text-slate-500 text-sm animate-fade-in">
          <p>图表钻取分析组件 · React + ECharts + Zustand + React Router</p>
          <p className="mt-2 text-xs">
            支持多级钻取 · 预测分析 · 关联钻取 · 权限控制 · 状态快照 · URL短码压缩 ·
            本地存储持久化
          </p>
        </footer>
      </div>
    </div>
  );
}

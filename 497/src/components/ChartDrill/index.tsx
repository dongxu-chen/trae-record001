import { useCallback, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import {
  useDrillStore,
  useCurrentData,
  useChartType,
  useCurrentLevel,
  useIsDrilling,
  useIsLoading,
  useShowPrediction,
  usePredictionData,
  useCurrentRole,
  useBlockedByPermission,
  useLinkRelatedCharts,
  useRelatedCharts,
} from '@/hooks/useDrillStore';
import {
  createDrillNode,
  canDrillDown,
  pathToNames,
  getLevelName,
} from '@/utils/drillUtils';
import { getDataByPath, getDimensionName, isSensitiveData } from '@/data/mockData';
import { DataPoint, EChartsOption, PredictionData } from '@/types/drill';
import {
  Loader2,
  BarChart3,
  PieChart,
  TrendingUp,
  Eye,
  EyeOff,
  Link,
  Link2,
  Shield,
  AlertTriangle,
  Lock,
  Unlock,
} from 'lucide-react';
import { ChartSkeleton } from '@/components/Skeleton';
import {
  formatPredictionDisplay,
  getPredictionMethodLabel,
} from '@/utils/prediction';
import './ChartDrill.css';

type ChartType = 'bar' | 'pie' | 'line';

interface ChartDrillProps {
  dimension?: string;
  chartId?: string;
  title?: string;
  showControls?: boolean;
}

export default function ChartDrill({
  dimension = 'sales',
  chartId = 'main',
  title,
  showControls = true,
}: ChartDrillProps) {
  const currentData = useCurrentData();
  const predictionData = usePredictionData();
  const showPrediction = useShowPrediction();
  const chartType = useChartType();
  const currentLevel = useCurrentLevel();
  const isDrilling = useIsDrilling();
  const isLoading = useIsLoading();
  const currentRole = useCurrentRole();
  const blockedByPermission = useBlockedByPermission();
  const linkRelatedCharts = useLinkRelatedCharts();
  const relatedCharts = useRelatedCharts();

  const {
    path,
    drillDown,
    setDrilling,
    setCurrentData,
    setChartType,
    togglePrediction,
    toggleLinkRelatedCharts,
    setBlockedByPermission,
    checkDrillPermission,
  } = useDrillStore();

  const colors = [
    '#06b6d4',
    '#3b82f6',
    '#8b5cf6',
    '#f97316',
    '#10b981',
    '#ef4444',
    '#f59e0b',
    '#6366f1',
  ];

  const sensitiveColors = {
    fill: '#ef4444',
    stroke: '#991b1b',
  };

  const predictionColors = {
    fill: 'rgba(16, 185, 129, 0.6)',
    border: '#10b981',
  };

  const getChartOption = useCallback((): EChartsOption => {
    if (!currentData) {
      return {};
    }

    const { data } = currentData;
    const xAxisData = data.map((item) => item.name);
    const values = data.map((item) => item.value);

    const baseOption: EChartsOption = {
      color: colors,
      tooltip: {
        trigger: chartType === 'pie' ? 'item' : 'axis',
        axisPointer: {
          type: chartType === 'line' ? 'shadow' : 'cross',
        },
        formatter: (params: any) => {
          const param = Array.isArray(params) ? params[0] : params;
          const dataPoint = data.find((d) => d.name === param.name);
          const canDrill = dataPoint
            ? canDrillDown(dataPoint, currentLevel)
            : false;
          const isSensitive = dataPoint?.isSensitive;
          const prediction = dataPoint?.prediction;

          let html = `
            <div style="font-weight: 600; margin-bottom: 8px;">${param.name}</div>
            <div>数值: <strong>${param.value?.toLocaleString() || 0}</strong></div>
          `;

          if (isSensitive) {
            html += `<div style="color: #ef4444; margin-top: 4px;">🔒 敏感数据</div>`;
          }

          if (prediction && showPrediction) {
            const predDisplay = formatPredictionDisplay(prediction);
            html += `
              <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #334155;">
                <div style="color: #10b981; font-weight: 600; margin-bottom: 4px;">
                  📊 预测数据
                </div>
                <div>预测值: <strong>${predDisplay.value}</strong></div>
                <div>置信区间: ${predDisplay.range}</div>
                <div>置信度: ${predDisplay.confidence}</div>
                <div class="${predDisplay.color}">趋势: ${predDisplay.trend}</div>
                <div style="color: #64748b; font-size: 11px; margin-top: 4px;">
                  算法: ${getPredictionMethodLabel(prediction.method)}
                </div>
              </div>
            `;
          }

          if (canDrill) {
            const targetLevel = currentLevel + 1;
            const hasPermission = checkDrillPermission(
              targetLevel,
              isSensitive
            );
            if (hasPermission) {
              html += '<div style="color: #06b6d4; margin-top: 8px;">点击可下钻 →</div>';
            } else {
              html += '<div style="color: #ef4444; margin-top: 8px;">🔒 权限不足，无法下钻</div>';
            }
          }

          return html;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10%',
        containLabel: true,
      },
      animationDuration: 600,
      animationEasingUpdate: 'quinticInOut',
    };

    if (chartType === 'bar') {
      const seriesData = values.map((value, index) => {
        const item = data[index];
        const isSensitive = item?.isSensitive;
        const hasPrediction = showPrediction && item?.prediction;

        let colorValue: any;
        if (isSensitive && !currentRole.canViewSensitive) {
          colorValue = sensitiveColors.fill;
        } else if (hasPrediction) {
          colorValue = {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: colors[index % colors.length] },
              { offset: 1, color: colors[index % colors.length] + '80' },
            ],
          };
        } else {
          colorValue = {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: colors[index % colors.length] },
              { offset: 1, color: colors[index % colors.length] + '80' },
            ],
          };
        }

        return {
          value,
          itemStyle: {
            color: colorValue,
            borderRadius: [6, 6, 0, 0],
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 20,
              shadowColor: isSensitive
                ? 'rgba(239, 68, 68, 0.5)'
                : 'rgba(6, 182, 212, 0.5)',
            },
          },
          markPoint: hasPrediction
            ? {
                symbol: 'circle',
                symbolSize: 10,
                itemStyle: {
                  color: predictionColors.fill,
                  borderColor: predictionColors.border,
                  borderWidth: 2,
                },
                data: [
                  {
                    name: '预测',
                    value: item.prediction!.predictedValue,
                    xAxis: index,
                    yAxis: item.prediction!.predictedValue,
                  },
                ],
              }
            : undefined,
        };
      });

      if (showPrediction) {
        const predictionSeries = {
          type: 'bar',
          data: data.map((item) => item.prediction?.predictedValue || null),
          itemStyle: {
            color: 'rgba(16, 185, 129, 0.3)',
            borderColor: '#10b981',
            borderType: 'dashed' as const,
            borderWidth: 2,
            borderRadius: [6, 6, 0, 0],
          },
          barGap: '-100%',
          z: -1,
          tooltip: {
            show: false,
          },
        };
        return {
          ...baseOption,
          xAxis: {
            type: 'category',
            data: xAxisData,
            axisLine: {
              lineStyle: { color: '#475569' },
            },
            axisLabel: {
              color: '#94a3b8',
              fontSize: 12,
              rotate: data.length > 6 ? 30 : 0,
              formatter: (value: string) => {
                const item = data.find((d) => d.name === value);
                if (item?.isSensitive && !currentRole.canViewSensitive) {
                  return '🔒 ' + value;
                }
                return value;
              },
            },
          },
          yAxis: {
            type: 'value',
            axisLine: {
              lineStyle: { color: '#475569' },
            },
            axisLabel: {
              color: '#94a3b8',
              fontSize: 12,
            },
            splitLine: {
              lineStyle: { color: '#334155', type: 'dashed' },
            },
          },
          series: [
            {
              type: 'bar',
              data: seriesData,
              barWidth: '50%',
              cursor: 'pointer',
            },
            predictionSeries,
          ],
        };
      }

      return {
        ...baseOption,
        xAxis: {
          type: 'category',
          data: xAxisData,
          axisLine: {
            lineStyle: { color: '#475569' },
          },
          axisLabel: {
            color: '#94a3b8',
            fontSize: 12,
            rotate: data.length > 6 ? 30 : 0,
            formatter: (value: string) => {
              const item = data.find((d) => d.name === value);
              if (item?.isSensitive && !currentRole.canViewSensitive) {
                return '🔒 ' + value;
              }
              return value;
            },
          },
        },
        yAxis: {
          type: 'value',
          axisLine: {
            lineStyle: { color: '#475569' },
          },
          axisLabel: {
            color: '#94a3b8',
            fontSize: 12,
          },
          splitLine: {
            lineStyle: { color: '#334155', type: 'dashed' },
          },
        },
        series: [
          {
            type: 'bar',
            data: seriesData,
            barWidth: '50%',
            cursor: 'pointer',
          },
        ],
      };
    }

    if (chartType === 'pie') {
      return {
        ...baseOption,
        legend: {
          orient: 'vertical',
          right: '5%',
          top: 'center',
          textStyle: {
            color: '#94a3b8',
            fontSize: 12,
          },
          formatter: (name: string) => {
            const item = data.find((d) => d.name === name);
            if (item?.isSensitive && !currentRole.canViewSensitive) {
              return '🔒 ' + name;
            }
            return name;
          },
        },
        series: [
          {
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['35%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 8,
              borderColor: '#1e293b',
              borderWidth: 2,
            },
            label: {
              show: true,
              color: '#e2e8f0',
              fontSize: 12,
              formatter: (params: any) => {
                const item = data.find((d) => d.name === params.name);
                if (item?.isSensitive && !currentRole.canViewSensitive) {
                  return '🔒 {b}: {d}%';
                }
                return '{b}: {d}%';
              },
            },
            emphasis: {
              label: {
                show: true,
                fontSize: 14,
                fontWeight: 'bold',
              },
              itemStyle: {
                shadowBlur: 20,
                shadowColor: 'rgba(6, 182, 212, 0.5)',
              },
            },
            data: data.map((item, index) => {
              const isSensitive = item.isSensitive;
              return {
                value: item.value,
                name: item.name,
                itemStyle: {
                  color:
                    isSensitive && !currentRole.canViewSensitive
                      ? sensitiveColors.fill
                      : colors[index % colors.length],
                },
              };
            }),
            cursor: 'pointer',
          },
        ],
      };
    }

    const seriesData: any[] = [
      {
        type: 'line',
        name: '实际值',
        data: values,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: {
          width: 3,
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: '#06b6d4' },
              { offset: 1, color: '#3b82f6' },
            ],
          },
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(6, 182, 212, 0.4)' },
              { offset: 1, color: 'rgba(6, 182, 212, 0.05)' },
            ],
          },
        },
        itemStyle: {
          color: '#06b6d4',
          borderWidth: 2,
          borderColor: '#1e293b',
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 15,
            shadowColor: '#06b6d4',
          },
        },
        cursor: 'pointer',
      },
    ];

    if (showPrediction) {
      seriesData.push({
        type: 'line',
        name: '预测值',
        data: data.map((item) => item.prediction?.predictedValue || null),
        smooth: true,
        symbol: 'diamond',
        symbolSize: 10,
        lineStyle: {
          width: 3,
          type: 'dashed',
          color: '#10b981',
        },
        itemStyle: {
          color: '#10b981',
          borderWidth: 2,
          borderColor: '#1e293b',
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 15,
            shadowColor: '#10b981',
          },
        },
      });
    }

    return {
      ...baseOption,
      legend: {
        show: showPrediction,
        top: 0,
        textStyle: {
          color: '#94a3b8',
        },
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: xAxisData,
        axisLine: {
          lineStyle: { color: '#475569' },
        },
        axisLabel: {
          color: '#94a3b8',
          fontSize: 12,
          formatter: (value: string) => {
            const item = data.find((d) => d.name === value);
            if (item?.isSensitive && !currentRole.canViewSensitive) {
              return '🔒 ' + value;
            }
            return value;
          },
        },
      },
      yAxis: {
        type: 'value',
        axisLine: {
          lineStyle: { color: '#475569' },
        },
        axisLabel: {
          color: '#94a3b8',
          fontSize: 12,
        },
        splitLine: {
          lineStyle: { color: '#334155', type: 'dashed' },
        },
      },
      series: seriesData,
    };
  }, [currentData, chartType, currentLevel, showPrediction, currentRole]);

  const chartEvents = useMemo(
    () => ({
      click: (params: { name: string; dataIndex: number }) => {
        if (!currentData) return;

        const dataPoint = currentData.data.find(
          (item: DataPoint) => item.name === params.name
        );

        if (!dataPoint) return;

        if (!canDrillDown(dataPoint, currentLevel)) {
          return;
        }

        const targetLevel = currentLevel + 1;
        const isSensitive = dataPoint.isSensitive;

        if (!checkDrillPermission(targetLevel, isSensitive)) {
          return;
        }

        setDrilling(true);

        const newNode = createDrillNode(
          dataPoint.name,
          currentLevel,
          path.length > 0 ? path[path.length - 1].id : null
        );

        const newPath = [...pathToNames(path), dataPoint.name];
        const nextLevelData = getDataByPath(newPath, dimension);

        setTimeout(() => {
          drillDown(newNode, nextLevelData!);
        }, 300);
      },
    }),
    [
      currentData,
      currentLevel,
      path,
      drillDown,
      setDrilling,
      dimension,
      checkDrillPermission,
    ]
  );

  const handleChartTypeChange = (type: ChartType) => {
    setChartType(type);
  };

  const permissionWarning = useMemo(() => {
    if (!blockedByPermission) return null;
    return (
      <div className="absolute top-4 left-4 z-20">
        <div className="flex items-center gap-2 px-4 py-2 bg-red-500/20 border border-red-500/50 rounded-xl text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4" />
          <span>权限不足，无法访问该层级数据</span>
        </div>
      </div>
    );
  }, [blockedByPermission]);

  if (isLoading) {
    return <ChartSkeleton />;
  }

  if (!currentData) {
    return (
      <div className="flex items-center justify-center h-96 bg-slate-800/50 rounded-2xl">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-500" />
      </div>
    );
  }

  const displayTitle = title || `${currentData.levelName} ${getDimensionName(dimension)}`;

  return (
    <div className="relative">
      {permissionWarning}

      {showControls && (
        <div className="absolute top-4 right-4 z-10 flex flex-wrap gap-2">
          <div className="flex gap-1 bg-slate-800/80 p-1 rounded-xl">
            {(['bar', 'pie', 'line'] as ChartType[]).map((type) => (
              <button
                key={type}
                onClick={() => handleChartTypeChange(type)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-1.5 ${
                  chartType === type
                    ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-500/30'
                    : 'text-slate-300 hover:bg-slate-700/50'
                }`}
              >
                {type === 'bar' ? (
                  <BarChart3 className="w-4 h-4" />
                ) : type === 'pie' ? (
                  <PieChart className="w-4 h-4" />
                ) : (
                  <TrendingUp className="w-4 h-4" />
                )}
                <span className="hidden sm:inline">
                  {type === 'bar' ? '柱状' : type === 'pie' ? '饼图' : '折线'}
                </span>
              </button>
            ))}
          </div>

          <button
            onClick={togglePrediction}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-1.5 ${
              showPrediction
                ? 'bg-green-600 text-white shadow-lg shadow-green-500/30'
                : 'bg-slate-700/80 text-slate-300 hover:bg-slate-600/80'
            }`}
            title={showPrediction ? '隐藏预测数据' : '显示预测数据'}
          >
            {showPrediction ? (
              <Eye className="w-4 h-4" />
            ) : (
              <EyeOff className="w-4 h-4" />
            )}
            <span className="hidden sm:inline">预测</span>
          </button>

          <button
            onClick={toggleLinkRelatedCharts}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-1.5 ${
              linkRelatedCharts
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/30'
                : 'bg-slate-700/80 text-slate-300 hover:bg-slate-600/80'
            }`}
            title={
              linkRelatedCharts
                ? '取消关联图表同步'
                : '开启关联图表同步'
            }
          >
            {linkRelatedCharts ? (
              <Link className="w-4 h-4" />
            ) : (
              <Link2 className="w-4 h-4" />
            )}
            <span className="hidden sm:inline">关联</span>
          </button>

          <div className="px-3 py-1.5 bg-slate-700/80 rounded-lg text-sm font-medium flex items-center gap-1.5 text-slate-300">
            {currentRole.canViewSensitive ? (
              <Unlock className="w-4 h-4 text-green-400" />
            ) : (
              <Lock className="w-4 h-4 text-red-400" />
            )}
            <span className="hidden sm:inline">{currentRole.name}</span>
          </div>
        </div>
      )}

      <div className="mb-4">
        <h3 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
          {displayTitle}
          {showPrediction && (
            <span className="text-xs px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full">
              含预测
            </span>
          )}
          {linkRelatedCharts && (
            <span className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded-full">
              已关联
            </span>
          )}
        </h3>
        <p className="text-slate-400 text-sm flex items-center gap-2">
          <span>
            当前层级: {getLevelName(currentLevel)} · 共{' '}
            {currentData.data.length} 个数据项
          </span>
          {currentData.data.some((d) => d.isSensitive) && (
            <span className="flex items-center gap-1 text-red-400">
              <Shield className="w-3 h-3" />
              含敏感数据
            </span>
          )}
        </p>
      </div>

      <div
        className={`transition-all duration-300 ${
          isDrilling ? 'opacity-50 scale-[0.99]' : 'opacity-100 scale-100'
        }`}
      >
        <ReactECharts
          option={getChartOption()}
          style={{ height: '480px', width: '100%' }}
          opts={{ renderer: 'canvas' }}
          onEvents={chartEvents}
          notMerge={true}
        />
      </div>

      {isDrilling && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50 rounded-2xl backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3 text-cyan-400">
            <Loader2 className="w-8 h-8 animate-spin" />
            <span className="font-medium">正在钻取...</span>
          </div>
        </div>
      )}

      <div className="mt-4 flex items-center gap-4 text-sm text-slate-400 flex-wrap">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
          <span>点击可下钻的数据项进行钻取分析</span>
        </div>
        {showPrediction && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span>绿色虚线为预测数据</span>
          </div>
        )}
        {linkRelatedCharts && (
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-purple-500" />
            <span>关联图表同步下钻中</span>
          </div>
        )}
      </div>
    </div>
  );
}

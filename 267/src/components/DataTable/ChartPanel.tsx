import { useState, useMemo } from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { BarChart3, LineChart as LineChartIcon, PieChart as PieChartIcon, Activity, Target, Sparkles } from 'lucide-react'
import type { DataRow, ChartConfig, ChartRecommendation, CellRange } from '@/types/table'
import { analyzeDataForChart, prepareChartData, getChartTypeLabel, getFieldLabel } from '@/utils/chartUtils'

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16']

interface ChartPanelProps {
  data: DataRow[]
  selectedRange?: CellRange | null
}

export function ChartPanel({ data, selectedRange }: ChartPanelProps) {
  const [activeChartType, setActiveChartType] = useState<ChartConfig['type']>('bar')
  const [selectedRecommendation, setSelectedRecommendation] = useState<number>(0)

  const recommendations = useMemo(() => {
    return analyzeDataForChart(data, selectedRange)
  }, [data, selectedRange])

  const currentRecommendation = recommendations[selectedRecommendation]

  const chartData = useMemo(() => {
    if (!currentRecommendation) return []
    return prepareChartData(data, currentRecommendation.config)
  }, [data, currentRecommendation])

  const renderChart = () => {
    if (!currentRecommendation || chartData.length === 0) {
      return (
        <div className="flex items-center justify-center h-64 text-gray-500">
          暂无图表数据
        </div>
      )
    }

    const { config } = currentRecommendation
    const type = activeChartType || config.type

    const commonProps = {
      data: chartData,
      margin: { top: 20, right: 30, left: 20, bottom: 20 },
    }

    switch (type) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={config.xField} tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value: number) => value.toLocaleString()} />
              <Legend />
              <Bar dataKey={config.yField} fill="#3B82F6" name={getFieldLabel(config.yField)} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={config.xField} tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value: number) => value.toLocaleString()} />
              <Legend />
              <Line type="monotone" dataKey={config.yField} stroke="#10B981" strokeWidth={2} dot={{ fill: '#10B981' }} name={getFieldLabel(config.yField)} />
            </LineChart>
          </ResponsiveContainer>
        )

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={true}
                label={({ name, percent }: { name: string; percent: number }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
                nameKey="name"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => value.toLocaleString()} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        )

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={config.xField} tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value: number) => value.toLocaleString()} />
              <Legend />
              <Area type="monotone" dataKey={config.yField} stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.3} name={getFieldLabel(config.yField)} />
            </AreaChart>
          </ResponsiveContainer>
        )

      case 'scatter':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={config.xField} name={getFieldLabel(config.xField)} tick={{ fontSize: 12 }} />
              <YAxis dataKey={config.yField} name={getFieldLabel(config.yField)} tick={{ fontSize: 12 }} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} formatter={(value: number) => value.toLocaleString()} />
              <Legend />
              <Scatter name="数据点" data={chartData} fill="#F59E0B" />
            </ScatterChart>
          </ResponsiveContainer>
        )

      default:
        return null
    }
  }

  const ChartIcon = ({ type }: { type: ChartConfig['type'] }) => {
    const icons = {
      bar: BarChart3,
      line: LineChartIcon,
      pie: PieChartIcon,
      area: Activity,
      scatter: Target,
    }
    const Icon = icons[type]
    return <Icon size={16} />
  }

  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">图表分析</h3>
        {selectedRange && (
          <span className="text-sm text-gray-500 bg-blue-50 px-2 py-1 rounded">
            已选中 {selectedRange.endRow - selectedRange.startRow + 1} 行数据
          </span>
        )}
      </div>

      {recommendations.length > 0 && (
        <div className="mb-4">
          <div className="text-sm font-medium text-gray-600 mb-2 flex items-center gap-1">
            <Sparkles size={14} className="text-yellow-500" />
            推荐图表
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
            {recommendations.slice(0, 5).map((rec, index) => (
              <button
                key={index}
                onClick={() => {
                  setSelectedRecommendation(index)
                  setActiveChartType(rec.type)
                }}
                className={`p-2 border rounded text-left transition-all ${
                  selectedRecommendation === index
                    ? 'border-blue-500 bg-blue-50'
                    : 'hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
                  <ChartIcon type={rec.type} />
                  <span>{getChartTypeLabel(rec.type)}</span>
                </div>
                <div className="text-xs truncate font-medium">{rec.config.title}</div>
                <div className="text-xs text-green-600 mt-1">
                  置信度 {(rec.confidence * 100).toFixed(0)}%
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {currentRecommendation && (
        <div className="mb-4 flex flex-wrap gap-2">
          {(['bar', 'line', 'pie', 'area', 'scatter'] as ChartConfig['type'][]).map(type => (
            <button
              key={type}
              onClick={() => setActiveChartType(type)}
              className={`flex items-center gap-1 px-3 py-1.5 rounded text-sm transition-colors ${
                activeChartType === type
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <ChartIcon type={type} />
              <span>{getChartTypeLabel(type)}</span>
            </button>
          ))}
        </div>
      )}

      {currentRecommendation && (
        <div className="mb-3 p-2 bg-gray-50 rounded text-sm text-gray-600">
          <span className="font-medium">推荐理由：</span>
          {currentRecommendation.reason}
        </div>
      )}

      <div className="border rounded bg-gray-50 p-2">
        {renderChart()}
      </div>

      {chartData.length > 0 && (
        <div className="mt-4">
          <div className="text-sm font-medium text-gray-600 mb-2">数据明细</div>
          <div className="max-h-32 overflow-auto border rounded">
            <table className="min-w-full text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  {chartData.length > 0 && Object.keys(chartData[0]).map(key => (
                    <th key={key} className="px-2 py-1.5 text-left border-b">
                      {key === 'name' ? '名称' : getFieldLabel(key)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {chartData.slice(0, 10).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    {Object.values(row).map((val, j) => (
                      <td key={j} className="px-2 py-1 border-b">
                        {typeof val === 'number' ? val.toLocaleString() : String(val)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {chartData.length > 10 && (
              <div className="text-center py-1 text-xs text-gray-500">
                还有 {chartData.length - 10} 条数据...
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

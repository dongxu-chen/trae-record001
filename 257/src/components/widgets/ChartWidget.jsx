import React, { useMemo, useState, useEffect } from 'react'
import ReactECharts from 'echarts-for-react'
import { mockSalesData, mockUserGrowthData, mockRevenueData } from '../../data/mockData'
import { eventBus, EVENTS } from '../../utils/eventBus'

export default function ChartWidget({ config }) {
  const { chartType = 'line', dataKey = 'sales' } = config
  const [localFilters, setLocalFilters] = useState({})

  useEffect(() => {
    const handleFilterChanged = ({ key, value }) => {
      setLocalFilters(prev => ({ ...prev, [key]: value }))
    }

    const handleFilterCleared = () => {
      setLocalFilters({})
    }

    const unsubscribeFilter = eventBus.on(EVENTS.FILTER_CHANGED, handleFilterChanged)
    const unsubscribeClear = eventBus.on(EVENTS.FILTER_CLEARED, handleFilterCleared)

    return () => {
      unsubscribeFilter()
      unsubscribeClear()
    }
  }, [])

  const option = useMemo(() => {
    let data = []
    let xAxisData = []
    let seriesData = []

    if (dataKey === 'sales') {
      data = mockSalesData
      xAxisData = data.map((d) => d.month)
      seriesData = data.map((d) => d.sales)
    } else if (dataKey === 'users') {
      data = mockUserGrowthData
      xAxisData = data.map((d) => d.month)
      seriesData = data.map((d) => d.activeUsers)
    } else if (dataKey === 'category') {
      data = mockRevenueData
    }

    const categoryFilter = localFilters.category
    if (categoryFilter && categoryFilter !== '全部' && dataKey === 'category') {
      data = data.filter((d) => d.category === categoryFilter)
    }

    if (chartType === 'pie') {
      return {
        tooltip: { trigger: 'item' },
        legend: { bottom: '0', left: 'center' },
        series: [
          {
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
            label: { show: false, position: 'center' },
            emphasis: { label: { show: true, fontSize: 20, fontWeight: 'bold' } },
            labelLine: { show: false },
            data: data.map((d) => ({ value: d.value, name: d.category, itemStyle: { color: d.color } })),
          },
        ],
      }
    }

    return {
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: xAxisData },
      yAxis: { type: 'value' },
      series: [
        {
          type: chartType,
          data: seriesData,
          smooth: chartType === 'line',
          areaStyle: chartType === 'line' ? { opacity: 0.3 } : undefined,
          itemStyle: {
            color: chartType === 'bar' ? '#5470c6' : undefined,
          },
          lineStyle: chartType === 'line' ? { width: 3, color: '#5470c6' } : undefined,
        },
      ],
    }
  }, [chartType, dataKey, localFilters])

  return (
    <div className="chart-widget">
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  )
}

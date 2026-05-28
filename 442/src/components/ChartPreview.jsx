import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'

function ChartPreview({ chartType, colors, categoryCount, sampleData }) {
  const option = useMemo(() => {
    const categories = ['类别A', '类别B', '类别C', '类别D', '类别E', '类别F', '类别G', '类别H', '类别I', '类别J', '类别K', '类别L'].slice(0, categoryCount)
    const values = (sampleData && sampleData.length === categoryCount)
      ? sampleData
      : categories.map((_, i) => Math.floor(Math.random() * 80 + 20))

    const baseOption = {
      tooltip: { trigger: 'item' },
      grid: { top: 30, right: 30, bottom: 40, left: 50 }
    }

    switch (chartType) {
      case 'bar':
        return {
          ...baseOption,
          tooltip: { trigger: 'axis' },
          xAxis: {
            type: 'category',
            data: categories,
            axisLabel: { rotate: 30 }
          },
          yAxis: { type: 'value' },
          series: [{
            type: 'bar',
            data: values.map((v, i) => ({
              value: v,
              itemStyle: {
                color: colors[i % colors.length],
                borderRadius: [4, 4, 0, 0]
              }
            })),
            barWidth: '60%'
          }]
        }

      case 'line':
        return {
          ...baseOption,
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: categories },
          yAxis: { type: 'value' },
          series: [{
            type: 'line',
            data: values,
            smooth: true,
            lineStyle: { color: colors[0], width: 3 },
            itemStyle: { color: colors[0] },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: colors[0] + '60' },
                  { offset: 1, color: colors[0] + '10' }
                ]
              }
            }
          }]
        }

      case 'pie':
        return {
          tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
          series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 8,
              borderColor: '#fff',
              borderWidth: 2
            },
            label: { show: false },
            emphasis: {
              label: { show: true, fontSize: 14, fontWeight: 'bold' }
            },
            data: categories.map((name, i) => ({
              name,
              value: values[i],
              itemStyle: { color: colors[i % colors.length] }
            }))
          }]
        }

      case 'scatter':
        return {
          ...baseOption,
          tooltip: { trigger: 'item' },
          xAxis: { type: 'value', name: 'X轴' },
          yAxis: { type: 'value', name: 'Y轴' },
          series: categories.slice(0, Math.min(6, categories.length)).map((name, i) => ({
            name,
            type: 'scatter',
            symbolSize: 15,
            data: Array.from({ length: 15 }, () => [
              Math.random() * 100,
              Math.random() * 100
            ]),
            itemStyle: { color: colors[i % colors.length] }
          }))
        }

      case 'area':
        return {
          ...baseOption,
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: categories },
          yAxis: { type: 'value' },
          series: [{
            type: 'line',
            data: values,
            smooth: true,
            lineStyle: { width: 0 },
            stack: 'total',
            showSymbol: false,
            areaStyle: {
              opacity: 0.8,
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: colors[0] },
                { offset: 1, color: colors[colors.length - 1] }
              ])
            }
          }]
        }

      case 'heatmap':
        const xData = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'].slice(0, categoryCount)
        const yData = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'].slice(0, categoryCount)
        const heatData = []
        for (let i = 0; i < xData.length; i++) {
          for (let j = 0; j < yData.length; j++) {
            heatData.push([i, j, Math.floor(Math.random() * 100)])
          }
        }
        return {
          tooltip: { position: 'top' },
          grid: { top: 40, right: 40, bottom: 50, left: 50 },
          xAxis: { type: 'category', data: xData, splitArea: { show: true } },
          yAxis: { type: 'category', data: yData, splitArea: { show: true } },
          visualMap: {
            min: 0,
            max: 100,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: 0,
            inRange: { color: colors }
          },
          series: [{
            type: 'heatmap',
            data: heatData,
            label: { show: false },
            emphasis: {
              itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
            }
          }]
        }

      case 'radar':
        const indicators = categories.map(name => ({ name, max: 100 }))
        return {
          tooltip: {},
          radar: {
            indicator: indicators,
            shape: 'circle',
            splitArea: { areaStyle: { color: ['#fff', '#f8f8f8'] } }
          },
          series: [{
            type: 'radar',
            data: [{
              value: values,
              name: '数据系列',
              areaStyle: { color: colors[0] + '40' },
              lineStyle: { color: colors[0], width: 2 },
              itemStyle: { color: colors[0] }
            }]
          }]
        }

      case 'treemap':
        return {
          tooltip: { formatter: '{b}: {c}' },
          series: [{
            type: 'treemap',
            breadcrumb: { show: false },
            label: { show: true, formatter: '{b}' },
            levels: [{
              itemStyle: {
                borderColor: '#fff',
                borderWidth: 2,
                gapWidth: 2
              }
            }],
            data: categories.map((name, i) => ({
              name,
              value: values[i],
              itemStyle: { color: colors[i % colors.length] }
            }))
          }]
        }

      default:
        return {
          tooltip: {},
          series: []
        }
    }
  }, [chartType, colors, categoryCount])

  return (
    <div className="chart-preview">
      <div className="preview-header">
        <h3>📊 图表预览</h3>
        <span className="preview-hint">图表类型：{chartType}</span>
      </div>
      <div className="chart-container">
        <ReactECharts
          option={option}
          style={{ height: '350px', width: '100%' }}
          opts={{ renderer: 'svg' }}
        />
      </div>
    </div>
  )
}

export default ChartPreview

import React, { useMemo, useRef, useCallback, useEffect } from 'react'
import ReactECharts from 'echarts-for-react'

function ColorComparison({ schemes, chartType, categoryCount, sampleData, onRemove }) {
  const chartRefs = useRef({})
  const groupId = useRef(`comparison-group-${Date.now()}`)
  const isSyncing = useRef(false)

  const sharedData = useMemo(() => {
    const categories = ['类别A', '类别B', '类别C', '类别D', '类别E', '类别F', '类别G', '类别H', '类别I', '类别J', '类别K', '类别L'].slice(0, categoryCount)

    let values
    if (sampleData && sampleData.length === categoryCount) {
      values = [...sampleData]
    } else {
      const seed = 42
      let s = seed
      const seededRandom = () => {
        s = (s * 16807) % 2147483647
        return s / 2147483647
      }
      values = categories.map(() => Math.floor(seededRandom() * 80 + 20))
    }

    return { categories, values }
  }, [categoryCount, sampleData])

  const allValues = useMemo(() => sharedData.values, [sharedData])
  const maxValue = Math.max(...allValues)
  const minValue = Math.min(...allValues)
  const yAxisMax = Math.ceil(maxValue * 1.1)
  const yAxisMin = 0

  const getChartOption = useCallback((colors) => {
    const { categories, values } = sharedData

    switch (chartType) {
      case 'bar':
        return {
          tooltip: { trigger: 'axis', group: groupId.current },
          dataZoom: [{ type: 'inside' }],
          grid: { left: 50, right: 20, top: 20, bottom: 40, containLabel: true },
          xAxis: {
            type: 'category',
            data: categories,
            axisLabel: { rotate: 30, fontSize: 10 },
            axisTick: { alignWithLabel: true }
          },
          yAxis: {
            type: 'value',
            min: yAxisMin,
            max: yAxisMax,
            axisLabel: { fontSize: 10 }
          },
          series: [{
            type: 'bar',
            data: values.map((v, i) => ({
              value: v,
              itemStyle: {
                color: colors[i % colors.length],
                borderRadius: [4, 4, 0, 0]
              }
            })),
            barWidth: '60%',
            animation: false
          }]
        }
      case 'line':
        return {
          tooltip: { trigger: 'axis', group: groupId.current },
          dataZoom: [{ type: 'inside' }],
          grid: { left: 50, right: 20, top: 20, bottom: 40, containLabel: true },
          xAxis: {
            type: 'category',
            data: categories,
            boundaryGap: false,
            axisLabel: { rotate: 30, fontSize: 10 }
          },
          yAxis: {
            type: 'value',
            min: yAxisMin,
            max: yAxisMax,
            axisLabel: { fontSize: 10 }
          },
          series: [{
            type: 'line',
            data: values,
            smooth: true,
            itemStyle: { color: colors[0] },
            lineStyle: { width: 3 },
            animation: false,
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
          tooltip: { trigger: 'item', group: groupId.current, formatter: '{b}: {c} ({d}%)' },
          legend: { show: false },
          series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['50%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 6,
              borderColor: '#fff',
              borderWidth: 2
            },
            label: { show: false },
            emphasis: {
              label: { show: true, fontSize: 12, fontWeight: 'bold' }
            },
            data: categories.map((name, i) => ({
              name,
              value: values[i],
              itemStyle: { color: colors[i % colors.length] }
            })),
            animation: false
          }]
        }
      case 'scatter':
        const scatterData = categories.slice(0, Math.min(6, categories.length)).map((_, catIdx) => {
          const seed = catIdx * 100 + 1
          let s = seed
          const seededRandom = () => {
            s = (s * 16807) % 2147483647
            return s / 2147483647
          }
          return Array.from({ length: 12 }, () => [
            Math.round(seededRandom() * 100),
            Math.round(seededRandom() * 100)
          ])
        })
        return {
          tooltip: { trigger: 'item', group: groupId.current },
          dataZoom: [{ type: 'inside' }, { type: 'inside', yAxisIndex: 0 }],
          grid: { left: 50, right: 20, top: 20, bottom: 40, containLabel: true },
          xAxis: { type: 'value', name: 'X', nameLocation: 'middle', nameGap: 25, min: 0, max: 100 },
          yAxis: { type: 'value', name: 'Y', nameLocation: 'middle', nameGap: 30, min: 0, max: 100 },
          series: scatterData.map((data, i) => ({
            name: categories[i],
            type: 'scatter',
            symbolSize: 12,
            data,
            itemStyle: { color: colors[i % colors.length] },
            animation: false
          }))
        }
      case 'radar':
        const indicators = categories.map(name => ({ name, max: yAxisMax }))
        return {
          tooltip: { group: groupId.current },
          radar: {
            indicator: indicators,
            shape: 'circle',
            radius: '65%',
            splitArea: { areaStyle: { color: ['#fff', '#f8f8f8'] } }
          },
          series: [{
            type: 'radar',
            data: [{
              value: values,
              name: '数据',
              areaStyle: { color: colors[0] + '40' },
              lineStyle: { color: colors[0], width: 2 },
              itemStyle: { color: colors[0] }
            }],
            animation: false
          }]
        }
      default:
        return {
          tooltip: { trigger: 'axis', group: groupId.current },
          dataZoom: [{ type: 'inside' }],
          grid: { left: 50, right: 20, top: 20, bottom: 40, containLabel: true },
          xAxis: { type: 'category', data: categories },
          yAxis: { type: 'value', min: yAxisMin, max: yAxisMax },
          series: [{
            type: 'bar',
            data: values.map((v, i) => ({
              value: v,
              itemStyle: { color: colors[i % colors.length] }
            }))
          }]
        }
    }
  }, [chartType, sharedData, yAxisMax, yAxisMin])

  const handleEvents = useMemo(() => {
    return schemes.reduce((acc, scheme) => {
      const key = `${scheme.name}-${scheme.type}`
      acc[key] = {
        dataZoom: (params) => {
          if (isSyncing.current) return
          isSyncing.current = true
          Object.entries(chartRefs.current).forEach(([k, ref]) => {
            if (k !== key && ref?.current) {
              const instance = ref.current.getEchartsInstance()
              if (instance) {
                instance.dispatchAction({
                  type: 'dataZoom',
                  start: params.start,
                  end: params.end
                })
              }
            }
          })
          setTimeout(() => { isSyncing.current = false }, 50)
        }
      }
      return acc
    }, {})
  }, [schemes])

  const registerChart = useCallback((key, ref) => {
    chartRefs.current[key] = ref
  }, [])

  useEffect(() => {
    return () => {
      Object.values(chartRefs.current).forEach(ref => {
        if (ref?.current) {
          try {
            ref.current.getEchartsInstance().dispose()
          } catch (e) {}
        }
      })
    }
  }, [])

  return (
    <div className="color-comparison">
      <div className="comparison-header">
        <h2>方案对比</h2>
        <div className="comparison-info">
          <span className="comparison-count">已选择 {schemes.length} 个方案</span>
          <span className="sync-indicator" title="缩放联动已启用">🔗 同步缩放</span>
        </div>
      </div>

      <div className="shared-data-info">
        <span className="data-label">共享数据：</span>
        <span className="data-values">
          {sharedData.categories.map((cat, i) => (
            <span key={i} className="data-pair">
              <strong>{cat}</strong>: {sharedData.values[i]}
            </span>
          ))}
        </span>
      </div>

      <div className={`comparison-grid comparison-count-${schemes.length}`}>
        {schemes.map(scheme => {
          const key = `${scheme.name}-${scheme.type}`
          return (
            <div key={key} className="comparison-card">
              <div className="comparison-card-header">
                <div>
                  <h4>{scheme.name}</h4>
                  <div className="scheme-badges">
                    <span className="scheme-type-label">{scheme.typeLabel}</span>
                    {scheme.reasonTags?.map((tag, i) => (
                      <span key={i} className="scheme-reason-tag">{tag}</span>
                    ))}
                  </div>
                </div>
                <button
                  className="remove-btn"
                  onClick={() => onRemove(scheme)}
                  title="移除"
                >
                  ✕
                </button>
              </div>

              <div className="comparison-colors">
                {scheme.colors.map((color, i) => (
                  <div
                    key={i}
                    className="comparison-swatch"
                    style={{ backgroundColor: color }}
                    title={color}
                  />
                ))}
              </div>

              <div className="comparison-chart">
                <ReactECharts
                  ref={(e) => registerChart(key, e)}
                  option={getChartOption(scheme.colors)}
                  style={{ height: '220px', width: '100%' }}
                  opts={{ renderer: 'svg' }}
                  onEvents={handleEvents[key] || {}}
                  notMerge={true}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ColorComparison

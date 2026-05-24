import React from 'react'

export default function CustomWidget({ config, title }) {
  const marketId = config.marketId

  switch (marketId) {
    case 'market-1':
      return <KPIProgressWidget config={config} />
    case 'market-2':
      return <MiniTrendWidget config={config} />
    case 'market-3':
      return <HeatmapWidget config={config} />
    case 'market-4':
      return <GaugeWidget config={config} />
    default:
      return <DefaultCustomWidget config={config} title={title} />
  }
}

function KPIProgressWidget({ config }) {
  const { value = 75, target = 100, color = '#52c41a' } = config
  const percentage = Math.min(100, (value / target) * 100)
  const radius = 45
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  return (
    <div className="custom-widget kpi-progress">
      <div className="kpi-circle">
        <svg width="120" height="120" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke="#f0f0f0"
            strokeWidth="8"
          />
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            transform="rotate(-90 60 60)"
            style={{ transition: 'stroke-dashoffset 0.5s ease' }}
          />
          <text
            x="60"
            y="60"
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="20"
            fontWeight="bold"
            fill="#333"
          >
            {percentage.toFixed(0)}%
          </text>
        </svg>
      </div>
      <div className="kpi-info">
        <div className="kpi-value">当前: {value}</div>
        <div className="kpi-target">目标: {target}</div>
      </div>
    </div>
  )
}

function MiniTrendWidget({ config }) {
  const { data = [10, 20, 15, 25, 30, 28, 35], color = '#1890ff' } = config
  const width = 100
  const height = 40
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1

  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * width
    const y = height - ((value - min) / range) * height
    return `${x},${y}`
  }).join(' ')

  const areaPoints = `0,${height} ${points} ${width},${height}`

  return (
    <div className="custom-widget mini-trend">
      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height + 10}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={areaPoints} fill="url(#gradient)" />
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <div className="trend-value">
        最新: {data[data.length - 1]}
      </div>
    </div>
  )
}

function HeatmapWidget({ config }) {
  const {
    rows = ['周一', '周二', '周三'],
    cols = ['上午', '下午', '晚上'],
    data = [[10, 20, 30], [15, 25, 35], [20, 30, 40]]
  } = config

  const maxValue = Math.max(...data.flat())

  const getColor = (value) => {
    const intensity = value / maxValue
    const green = Math.floor(255 - intensity * 200)
    const blue = Math.floor(255 - intensity * 200)
    return `rgb(255, ${green}, ${blue})`
  }

  return (
    <div className="custom-widget heatmap">
      <table className="heatmap-table">
        <thead>
          <tr>
            <th></th>
            {cols.map(col => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr key={rowIndex}>
              <th>{rows[rowIndex]}</th>
              {row.map((value, colIndex) => (
                <td
                  key={colIndex}
                  className="heatmap-cell"
                  style={{ backgroundColor: getColor(value) }}
                  title={value}
                >
                  {value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function GaugeWidget({ config }) {
  const { value = 65, min = 0, max = 100, unit = '%' } = config
  const percentage = ((value - min) / (max - min)) * 100
  const angle = (percentage / 100) * 180 - 90

  return (
    <div className="custom-widget gauge">
      <svg width="140" height="90" viewBox="0 0 140 90">
        <path
          d="M 20 80 A 50 50 0 0 1 120 80"
          fill="none"
          stroke="#f0f0f0"
          strokeWidth="12"
          strokeLinecap="round"
        />
        <path
          d="M 20 80 A 50 50 0 0 1 120 80"
          fill="none"
          stroke="#52c41a"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${(percentage / 100) * 157} 157`}
        />
        <line
          x1="70"
          y1="80"
          x2={70 + 35 * Math.cos(angle * Math.PI / 180)}
          y2={80 + 35 * Math.sin(angle * Math.PI / 180)}
          stroke="#333"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx="70" cy="80" r="6" fill="#333" />
        <text x="70" y="50" textAnchor="middle" fontSize="24" fontWeight="bold" fill="#333">
          {value}{unit}
        </text>
      </svg>
    </div>
  )
}

function DefaultCustomWidget({ config, title }) {
  return (
    <div className="custom-widget default">
      <div className="default-icon">✨</div>
      <div className="default-title">{title || '自定义组件'}</div>
      <div className="default-desc">自定义组件内容区域</div>
    </div>
  )
}

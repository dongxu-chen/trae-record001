import ReactECharts from 'echarts-for-react';

const LineChart = ({ data }) => {
  const option = {
    backgroundColor: 'transparent',
    title: {
      text: '实时流量趋势',
      left: 'left',
      textStyle: {
        color: '#fff',
        fontSize: 18
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(10, 22, 40, 0.9)',
      borderColor: '#00b3ff',
      textStyle: {
        color: '#fff'
      },
      formatter: function(params) {
        return `${params[0].axisValue}<br/>流量: ${params[0].value}`;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map(item => item.time),
      axisLine: {
        lineStyle: {
          color: '#00b3ff'
        }
      },
      axisLabel: {
        color: '#fff'
      }
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: {
          color: 'rgba(0, 179, 255, 0.2)'
        }
      },
      axisLine: {
        show: false
      },
      axisLabel: {
        color: '#fff'
      }
    },
    series: [
      {
        name: '流量',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        data: data.map(item => item.value),
        lineStyle: {
          color: '#00b3ff',
          width: 3
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0, 179, 255, 0.6)' },
              { offset: 1, color: 'rgba(0, 179, 255, 0.05)' }
            ]
          }
        },
        itemStyle: {
          color: '#00b3ff'
        }
      }
    ]
  };

  return (
    <ReactECharts
      option={option}
      style={{ width: '100%', height: '100%' }}
      opts={{ renderer: 'canvas' }}
    />
  );
};

export default LineChart;

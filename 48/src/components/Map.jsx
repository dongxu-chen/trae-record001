import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { chinaGeoData, provinceCenters } from '../utils/chinaMap';

const Map = ({ data }) => {
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);

  useEffect(() => {
    if (chartRef.current) {
      echarts.registerMap('china', chinaGeoData);
      chartInstanceRef.current = echarts.init(chartRef.current);

      const handleResize = () => {
        chartInstanceRef.current?.resize();
      };

      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        chartInstanceRef.current?.dispose();
      };
    }
  }, []);

  useEffect(() => {
    if (chartInstanceRef.current && data) {
      const scatterData = data
        .filter(item => provinceCenters[item.name])
        .map(item => ({
          name: item.name,
          value: [...provinceCenters[item.name], item.value]
        }));

      const mapData = data.map(item => ({
        name: item.name,
        value: item.value
      }));

      const option = {
        backgroundColor: 'transparent',
        title: {
          text: '全国区域分布',
          left: 'left',
          textStyle: {
            color: '#fff',
            fontSize: 18
          }
        },
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(10, 22, 40, 0.9)',
          borderColor: '#00b3ff',
          textStyle: {
            color: '#fff'
          },
          formatter: function(params) {
            if (params.seriesType === 'effectScatter') {
              const value = params.value[2] || 0;
              return `${params.name}<br/>用户数量: ${value}`;
            }
            return `${params.name}<br/>用户数量: ${params.value || 0}`;
          }
        },
        visualMap: {
          min: 0,
          max: 5000,
          left: 'left',
          top: 'bottom',
          text: ['高', '低'],
          calculable: true,
          inRange: {
            color: ['#0e2c4e', '#00b3ff', '#00ff88']
          },
          textStyle: {
            color: '#fff'
          }
        },
        geo: {
          map: 'china',
          roam: true,
          scaleLimit: {
            min: 1,
            max: 5
          },
          zoom: 1.2,
          label: {
            show: true,
            color: '#fff',
            fontSize: 10
          },
          emphasis: {
            label: {
              color: '#fff',
              fontSize: 12
            },
            itemStyle: {
              areaColor: 'rgba(0, 179, 255, 0.3)'
            }
          },
          itemStyle: {
            areaColor: 'rgba(0, 179, 255, 0.1)',
            borderColor: 'rgba(0, 179, 255, 0.5)',
            borderWidth: 1
          }
        },
        series: [
          {
            name: '用户数量',
            type: 'map',
            map: 'china',
            geoIndex: 0,
            data: mapData
          },
          {
            name: '热点城市',
            type: 'effectScatter',
            coordinateSystem: 'geo',
            data: scatterData,
            symbolSize: function(val) {
              return Math.max(8, Math.sqrt(val[2]) / 2);
            },
            showEffectOn: 'render',
            rippleEffect: {
              brushType: 'stroke',
              scale: 3
            },
            hoverAnimation: true,
            label: {
              show: true,
              formatter: '{b}',
              position: 'right',
              color: '#fff',
              fontSize: 12
            },
            itemStyle: {
              color: '#00ff88',
              shadowBlur: 10,
              shadowColor: '#00ff88'
            },
            zlevel: 1
          }
        ]
      };

      chartInstanceRef.current.setOption(option, true);
    }
  }, [data]);

  return (
    <div 
      ref={chartRef} 
      style={{ width: '100%', height: '100%' }}
    />
  );
};

export default Map;

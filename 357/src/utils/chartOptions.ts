import type { EChartsOption } from 'echarts';
import type { ChartTheme, ChartType } from '@/types/theme';
import { generateSeriesColors } from './themeUtils';

const categories = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const seriesNames = ['销售数据', '访问数据', '咨询数据'];
const seriesCount = seriesNames.length;

function getMockData(type: ChartType): number[][] {
  const baseData: Record<ChartType, number[][]> = {
    line: [
      [120, 132, 101, 134, 90, 230, 210],
      [220, 182, 191, 234, 290, 330, 310],
      [150, 232, 201, 154, 190, 330, 410],
    ],
    bar: [
      [120, 132, 101, 134, 90, 230, 210],
      [220, 182, 191, 234, 290, 330, 310],
      [150, 232, 201, 154, 190, 330, 410],
    ],
    area: [
      [120, 132, 101, 134, 90, 230, 210],
      [220, 182, 191, 234, 290, 330, 310],
      [150, 232, 201, 154, 190, 330, 410],
    ],
    pie: [[35, 30, 35]],
    scatter: [
      [120, 132, 101, 134, 90, 230, 210],
      [220, 182, 191, 234, 290, 330, 310],
      [150, 232, 201, 154, 190, 330, 410],
    ],
  };
  return baseData[type];
}

function createLineSeries(theme: ChartTheme, data: number[], name: string, colorIndex: number): EChartsOption {
  const colors = generateSeriesColors(theme.color, seriesCount);
  return {
    name,
    type: 'line',
    data,
    smooth: theme.line?.smooth,
    symbol: theme.line?.symbol,
    symbolSize: theme.line?.symbolSize,
    itemStyle: {
      color: colors[colorIndex],
      borderWidth: theme.line?.itemStyle?.borderWidth,
    },
    lineStyle: {
      color: colors[colorIndex],
      width: theme.line?.lineStyle?.width,
    },
  };
}

function createBarSeries(theme: ChartTheme, data: number[], name: string, colorIndex: number): EChartsOption {
  const colors = generateSeriesColors(theme.color, seriesCount);
  return {
    name,
    type: 'bar',
    data,
    itemStyle: {
      color: colors[colorIndex],
      borderWidth: theme.bar?.itemStyle?.borderWidth,
      borderRadius: [4, 4, 0, 0],
    },
  };
}

function createAreaSeries(theme: ChartTheme, data: number[], name: string, colorIndex: number): EChartsOption {
  const colors = generateSeriesColors(theme.color, seriesCount);
  return {
    name,
    type: 'line',
    data,
    smooth: theme.line?.smooth,
    symbol: theme.line?.symbol,
    symbolSize: theme.line?.symbolSize,
    areaStyle: {
      color: {
        type: 'linear',
        x: 0,
        y: 0,
        x2: 0,
        y2: 1,
        colorStops: [
          { offset: 0, color: colors[colorIndex] + '80' },
          { offset: 1, color: colors[colorIndex] + '10' },
        ],
      },
    },
    itemStyle: {
      color: colors[colorIndex],
    },
    lineStyle: {
      color: colors[colorIndex],
      width: theme.line?.lineStyle?.width,
    },
  };
}

function createPieSeries(theme: ChartTheme, data: number[]): EChartsOption {
  const colors = generateSeriesColors(theme.color, seriesCount);
  const pieData = data.map((value, index) => ({
    value,
    name: seriesNames[index],
    itemStyle: {
      color: colors[index],
      borderWidth: theme.pie?.itemStyle?.borderWidth,
    },
  }));
  return {
    type: 'pie',
    radius: ['40%', '70%'],
    avoidLabelOverlap: false,
    itemStyle: {
      borderRadius: 8,
      borderColor: theme.backgroundColor || '#fff',
      borderWidth: 2,
    },
    label: {
      show: true,
      color: theme.pie?.label?.color,
      fontSize: theme.pie?.label?.fontSize,
    },
    emphasis: {
      label: {
        show: true,
        fontSize: 16,
        fontWeight: 'bold',
      },
    },
    data: pieData,
  };
}

function createScatterSeries(theme: ChartTheme, data: number[], name: string, colorIndex: number): EChartsOption {
  const colors = generateSeriesColors(theme.color, seriesCount);
  const scatterData = data.map((value, index) => [index, value, Math.random() * 30 + 10]);
  return {
    name,
    type: 'scatter',
    data: scatterData,
    symbolSize: (data: number[]) => data[2] / 3,
    itemStyle: {
      color: colors[colorIndex],
      opacity: 0.8,
    },
  };
}

export function generateChartOption(theme: ChartTheme, chartType: ChartType): EChartsOption {
  const mockData = getMockData(chartType);
  const colors = generateSeriesColors(theme.color, seriesCount);

  let series: EChartsOption[];

  if (chartType === 'pie') {
    series = [createPieSeries(theme, mockData[0])];
  } else {
    series = mockData.map((data, index) => {
      switch (chartType) {
        case 'bar':
          return createBarSeries(theme, data, seriesNames[index], index);
        case 'area':
          return createAreaSeries(theme, data, seriesNames[index], index);
        case 'scatter':
          return createScatterSeries(theme, data, seriesNames[index], index);
        case 'line':
        default:
          return createLineSeries(theme, data, seriesNames[index], index);
      }
    });
  }

  const baseOption: EChartsOption = {
    backgroundColor: theme.backgroundColor,
    color: colors,
    title: {
      text: '图表主题预览',
      subtext: `当前类型: ${chartType}`,
      left: 'center',
      textStyle: theme.title?.textStyle as EChartsOption['title'] extends { textStyle?: infer T } ? T : never,
      subtextStyle: theme.title?.subtextStyle as EChartsOption['title'] extends { subtextStyle?: infer T } ? T : never,
    },
    tooltip: {
      trigger: chartType === 'pie' ? 'item' : 'axis',
      backgroundColor: theme.tooltip?.backgroundColor,
      borderColor: theme.tooltip?.borderColor,
      borderWidth: theme.tooltip?.borderWidth,
      textStyle: theme.tooltip?.textStyle as EChartsOption['tooltip'] extends { textStyle?: infer T } ? T : never,
    },
    legend: {
      show: theme.legend?.show,
      bottom: 10,
      textStyle: theme.legend?.textStyle as EChartsOption['legend'] extends { textStyle?: infer T } ? T : never,
      data: seriesNames,
    },
    grid: {
      show: theme.grid?.show,
      borderColor: theme.grid?.borderColor,
      borderWidth: theme.grid?.borderWidth,
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '18%',
      containLabel: true,
    },
  };

  if (chartType !== 'pie') {
    baseOption.xAxis = {
      type: 'category',
      data: categories,
      axisLine: theme.categoryAxis?.axisLine,
      axisTick: theme.categoryAxis?.axisTick,
      axisLabel: theme.categoryAxis?.axisLabel,
      splitLine: theme.categoryAxis?.splitLine,
    };
    baseOption.yAxis = {
      type: 'value',
      axisLine: theme.valueAxis?.axisLine,
      axisTick: theme.valueAxis?.axisTick,
      axisLabel: theme.valueAxis?.axisLabel,
      splitLine: theme.valueAxis?.splitLine,
    };
  }

  baseOption.series = series as EChartsOption['series'];

  return baseOption;
}

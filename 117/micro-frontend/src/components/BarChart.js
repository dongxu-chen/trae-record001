import { BaseChart } from '../core/BaseChart.js';

export class BarChart extends BaseChart {
  constructor() {
    super();
  }

  static get observedAttributes() {
    return [...super.observedAttributes, 'horizontal', 'stacked'];
  }

  get chartType() {
    return 'bar';
  }

  getChartOption() {
    const title = this.getAttribute('title') || '柱状图';
    const horizontal = this.hasAttribute('horizontal');
    const stacked = this.hasAttribute('stacked');
    
    const defaultData = {
      xAxis: ['1月', '2月', '3月', '4月', '5月', '6月'],
      series: [
        {
          name: '销售额',
          data: [8200, 9320, 9010, 9340, 12900, 13300]
      ]
    };

    const data = this._data || defaultData;

    if (horizontal) {
      return {
        title: { text: title, show: false },
        tooltip: { trigger: 'axis' },
        legend: { bottom: 10 },
        grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
        xAxis: { type: 'value' },
        yAxis: { type: 'category', data: data.xAxis },
        series: data.series.map((item) => ({
          ...item,
          type: 'bar',
          stack: stacked ? 'total' : undefined,
          itemStyle: { borderRadius: [0, 4, 4, 0] }
        })),
        ...this._options
      };
    }

    return {
      title: { text: title, show: false },
      tooltip: { trigger: 'axis' },
      legend: { bottom: 10 },
      grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
      xAxis: { type: 'category', data: data.xAxis },
      yAxis: { type: 'value' },
      series: data.series.map((item) => ({
        ...item,
        type: 'bar',
        stack: stacked ? 'total' : undefined,
        itemStyle: { borderRadius: [4, 4, 0, 0] }
      })),
      ...this._options
    };
  }
}

if (!customElements.get('bar-chart')) {
  customElements.define('bar-chart', BarChart);
}

export default BarChart;

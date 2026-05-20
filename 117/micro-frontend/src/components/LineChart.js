import { BaseChart } from '../core/BaseChart.js';

export class LineChart extends BaseChart {
  constructor() {
    super();
  }

  static get observedAttributes() {
    return [...super.observedAttributes, 'smooth', 'show-legend'];
  }

  get chartType() {
    return 'line';
  }

  getChartOption() {
    const title = this.getAttribute('title') || '折线图';
    const smooth = this.hasAttribute('smooth');
    const showLegend = this.hasAttribute('show-legend');
    
    const defaultData = {
      xAxis: ['1月', '2月', '3月', '4月', '5月', '6月'],
      series: [
        {
          name: '销售额',
          data: [8200, 9320, 9010, 9340, 12900, 13300]
      ]
    };

    const data = this._data || defaultData;

    return {
      title: { text: title, left: 'center', top: 10, show: false },
      tooltip: { trigger: 'axis' },
      legend: { show: showLegend, bottom: 10 },
      grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: data.xAxis
      },
      yAxis: { type: 'value' },
      series: data.series.map((item) => ({
        ...item,
        type: 'line',
        smooth: smooth,
        areaStyle: item.areaStyle || {}
      })),
      ...this._options
    };
  }
}

if (!customElements.get('line-chart')) {
  customElements.define('line-chart', LineChart);
}

export default LineChart;

import { BaseChart } from '../core/BaseChart.js';

export class PieChart extends BaseChart {
  constructor() {
    super();
  }

  static get observedAttributes() {
    return [...super.observedAttributes, 'doughnut', 'rose-type'];
  }

  get chartType() {
    return 'pie';
  }

  getChartOption() {
    const title = this.getAttribute('title') || '饼图';
    const doughnut = this.hasAttribute('doughnut');
    const roseType = this.getAttribute('rose-type');
    
    const defaultData = [
      { value: 1048, name: '搜索引擎' },
      { value: 735, name: '直接访问' },
      { value: 580, name: '邮件营销' },
      { value: 484, name: '联盟广告' },
      { value: 300, name: '视频广告' }
    ];

    const data = this._data?.data || defaultData;

    return {
      title: { text: title, show: false },
      tooltip: { trigger: 'item' },
      legend: { bottom: 10, left: 'center' },
      series: [
        {
          name: title,
          type: 'pie',
          radius: doughnut ? ['40%', '70%'] : '70%',
          roseType: roseType || false,
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: this._theme === 'dark' ? '#141414' : '#fff',
            borderWidth: 2
          },
          label: { show: false, position: 'center' },
          emphasis: {
            label: { show: true, fontSize: 16, fontWeight: 'bold' }
          },
          labelLine: { show: false },
          data: data
        }
      ],
      ...this._options
    };
  }
}

if (!customElements.get('pie-chart')) {
  customElements.define('pie-chart', PieChart);
}

export default PieChart;

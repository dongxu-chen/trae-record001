export const generateMockData = (chartType) => {
  const baseData = {
    xAxis: ['1月', '2月', '3月', '4月', '5月', '6月'],
    series: [
      {
        name: '销售额',
        data: Array.from({ length: 6 }, () => Math.floor(Math.random() * 10000) + 1000)
      },
      {
        name: '利润',
        data: Array.from({ length: 6 }, () => Math.floor(Math.random() * 5000) + 500)
      }
    ]
  };

  if (chartType === 'pie') {
    return {
      data: [
        { value: Math.floor(Math.random() * 1000) + 200, name: '直接访问' },
        { value: Math.floor(Math.random() * 800) + 100, name: '邮件营销' },
        { value: Math.floor(Math.random() * 600) + 100, name: '联盟广告' },
        { value: Math.floor(Math.random() * 400) + 100, name: '视频广告' },
        { value: Math.floor(Math.random() * 300) + 100, name: '搜索引擎' }
      ]
    };
  }

  return baseData;
};

export const fetchMockAPI = async (chartType) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(generateMockData(chartType));
    }, 300);
  });
};

export const staticData = {
  line: {
    xAxis: ['1月', '2月', '3月', '4月', '5月', '6月'],
    series: [
      { name: '销售额', data: [8200, 9320, 9010, 9340, 12900, 13300] },
      { name: '利润', data: [3200, 4320, 4010, 4340, 5900, 6300] }
    ]
  },
  bar: {
    xAxis: ['1月', '2月', '3月', '4月', '5月', '6月'],
    series: [
      { name: '销售额', data: [8200, 9320, 9010, 9340, 12900, 13300] },
      { name: '利润', data: [3200, 4320, 4010, 4340, 5900, 6300] }
    ]
  },
  pie: {
    data: [
      { value: 1048, name: '搜索引擎' },
      { value: 735, name: '直接访问' },
      { value: 580, name: '邮件营销' },
      { value: 484, name: '联盟广告' },
      { value: 300, name: '视频广告' }
    ]
  }
};

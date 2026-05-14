const chinaGeoData = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: '北京', adcode: '110000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[116.46, 39.92], [116.46, 41.06], [117.44, 41.06], [117.44, 39.92], [116.46, 39.92]]]
      }
    },
    {
      type: 'Feature',
      properties: { name: '上海', adcode: '310000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[121.48, 31.22], [121.48, 31.88], [122.12, 31.88], [122.12, 31.22], [121.48, 31.22]]]
      }
    },
    {
      type: 'Feature',
      properties: { name: '广东', adcode: '440000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[113.23, 23.16], [109.75, 20.23], [117.12, 20.5], [117.03, 25.51], [113.23, 23.16]]]
      }
    },
    {
      type: 'Feature',
      properties: { name: '浙江', adcode: '330000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[120.19, 30.26], [118.01, 27.48], [122.72, 30.07], [122.11, 31.18], [120.19, 30.26]]]
      }
    },
    {
      type: 'Feature',
      properties: { name: '四川', adcode: '510000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[104.06, 30.67], [97.35, 26.05], [108.43, 32.15], [101.52, 34.33], [104.06, 30.67]]]
      }
    },
    {
      type: 'Feature',
      properties: { name: '湖北', adcode: '420000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[114.31, 30.52], [108.38, 29.15], [116.46, 31.22], [111.28, 32.75], [114.31, 30.52]]]
      }
    },
    {
      type: 'Feature',
      properties: { name: '陕西', adcode: '610000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[108.95, 34.27], [105.59, 32.73], [111.15, 39.78], [107.53, 39.33], [108.95, 34.27]]]
      }
    },
    {
      type: 'Feature',
      properties: { name: '江苏', adcode: '320000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[118.78, 32.04], [116.41, 31.88], [121.55, 32.12], [119.49, 34.76], [118.78, 32.04]]]
      }
    },
    {
      type: 'Feature',
      properties: { name: '山东', adcode: '370000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[117, 36.65], [114.83, 34.76], [122.38, 37.64], [117.82, 38.36], [117, 36.65]]]
      }
    },
    {
      type: 'Feature',
      properties: { name: '河南', adcode: '410000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[113.65, 34.76], [110.35, 31.72], [116.38, 35.56], [114.43, 36.35], [113.65, 34.76]]]
      }
    },
    {
      type: 'Feature',
      properties: { name: '河北', adcode: '130000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[114.48, 38.03], [113.5, 36.06], [117.45, 40.25], [115.25, 42.5], [114.48, 38.03]]]
      }
    },
    {
      type: 'Feature',
      properties: { name: '辽宁', adcode: '210000' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[123.38, 41.8], [119.53, 38.84], [125.71, 42.58], [123.54, 43.17], [123.38, 41.8]]]
      }
    }
  ]
};

const provinceCenters = {
  '北京': [116.46, 39.92],
  '上海': [121.48, 31.22],
  '广东': [113.23, 23.16],
  '浙江': [120.19, 30.26],
  '四川': [104.06, 30.67],
  '湖北': [114.31, 30.52],
  '陕西': [108.95, 34.27],
  '江苏': [118.78, 32.04],
  '山东': [117, 36.65],
  '河南': [113.65, 34.76],
  '河北': [114.48, 38.03],
  '辽宁': [123.38, 41.8]
};

export { chinaGeoData, provinceCenters };

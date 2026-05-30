import { LevelData, RelatedChart, ROLE_CONFIG } from '@/types/drill';

interface ProvinceData {
  [key: string]: LevelData;
}

interface CityData {
  [key: string]: LevelData;
}

interface DimensionData {
  [dimension: string]: {
    country: LevelData;
    province: ProvinceData;
    city: CityData;
  };
}

const DIMENSIONS = ['sales', 'users', 'orders'];
const DIMENSION_NAMES: Record<string, string> = {
  sales: '销售额',
  users: '用户量',
  orders: '订单量',
};

const SENSITIVE_REGIONS = ['深圳市', '海淀区', '浦东新区'];
const SENSITIVE_PROVINCES = ['广东省', '北京市', '上海市'];

function createDataPoint(
  name: string,
  value: number,
  hasChildren: boolean,
  level: number
) {
  const isSensitive =
    (level >= 1 && SENSITIVE_PROVINCES.includes(name)) ||
    (level >= 2 && SENSITIVE_REGIONS.includes(name));

  const relatedDimensions = DIMENSIONS.filter((d) => d !== 'sales');

  return {
    name,
    value,
    hasChildren,
    isSensitive,
    relatedDimensions,
  };
}

function generateDimensionData(baseMultiplier: number): {
  country: LevelData;
  province: ProvinceData;
  city: CityData;
} {
  const countryData: LevelData = {
    level: 0,
    levelName: '全国',
    parentId: null,
    dimension: 'sales',
    data: [
      createDataPoint('北京市', Math.round(12500 * baseMultiplier), true, 0),
      createDataPoint('上海市', Math.round(11800 * baseMultiplier), true, 0),
      createDataPoint('广东省', Math.round(15600 * baseMultiplier), true, 0),
      createDataPoint('浙江省', Math.round(9800 * baseMultiplier), true, 0),
      createDataPoint('江苏省', Math.round(10200 * baseMultiplier), true, 0),
      createDataPoint('四川省', Math.round(8600 * baseMultiplier), true, 0),
      createDataPoint('山东省', Math.round(9200 * baseMultiplier), true, 0),
      createDataPoint('湖北省', Math.round(7500 * baseMultiplier), true, 0),
    ],
  };

  const provinceData: ProvinceData = {
    北京市: {
      level: 1,
      levelName: '北京市',
      parentId: 'country',
      dimension: 'sales',
      data: [
        createDataPoint('朝阳区', Math.round(4200 * baseMultiplier), true, 1),
        createDataPoint('海淀区', Math.round(3800 * baseMultiplier), true, 1),
        createDataPoint('西城区', Math.round(2500 * baseMultiplier), false, 1),
        createDataPoint('东城区', Math.round(2000 * baseMultiplier), false, 1),
      ],
    },
    上海市: {
      level: 1,
      levelName: '上海市',
      parentId: 'country',
      dimension: 'sales',
      data: [
        createDataPoint('浦东新区', Math.round(5200 * baseMultiplier), true, 1),
        createDataPoint('黄浦区', Math.round(2800 * baseMultiplier), false, 1),
        createDataPoint('徐汇区', Math.round(2200 * baseMultiplier), false, 1),
        createDataPoint('静安区', Math.round(1600 * baseMultiplier), false, 1),
      ],
    },
    广东省: {
      level: 1,
      levelName: '广东省',
      parentId: 'country',
      dimension: 'sales',
      data: [
        createDataPoint('广州市', Math.round(5200 * baseMultiplier), true, 1),
        createDataPoint('深圳市', Math.round(6800 * baseMultiplier), true, 1),
        createDataPoint('东莞市', Math.round(2100 * baseMultiplier), false, 1),
        createDataPoint('佛山市', Math.round(1500 * baseMultiplier), false, 1),
      ],
    },
    浙江省: {
      level: 1,
      levelName: '浙江省',
      parentId: 'country',
      dimension: 'sales',
      data: [
        createDataPoint('杭州市', Math.round(4500 * baseMultiplier), true, 1),
        createDataPoint('宁波市', Math.round(2800 * baseMultiplier), false, 1),
        createDataPoint('温州市', Math.round(1500 * baseMultiplier), false, 1),
        createDataPoint('绍兴市', Math.round(1000 * baseMultiplier), false, 1),
      ],
    },
    江苏省: {
      level: 1,
      levelName: '江苏省',
      parentId: 'country',
      dimension: 'sales',
      data: [
        createDataPoint('南京市', Math.round(4200 * baseMultiplier), true, 1),
        createDataPoint('苏州市', Math.round(3800 * baseMultiplier), true, 1),
        createDataPoint('无锡市', Math.round(1400 * baseMultiplier), false, 1),
        createDataPoint('常州市', Math.round(800 * baseMultiplier), false, 1),
      ],
    },
    四川省: {
      level: 1,
      levelName: '四川省',
      parentId: 'country',
      dimension: 'sales',
      data: [
        createDataPoint('成都市', Math.round(5600 * baseMultiplier), true, 1),
        createDataPoint('绵阳市', Math.round(1800 * baseMultiplier), false, 1),
        createDataPoint('德阳市', Math.round(1200 * baseMultiplier), false, 1),
      ],
    },
    山东省: {
      level: 1,
      levelName: '山东省',
      parentId: 'country',
      dimension: 'sales',
      data: [
        createDataPoint('济南市', Math.round(3800 * baseMultiplier), true, 1),
        createDataPoint('青岛市', Math.round(3600 * baseMultiplier), true, 1),
        createDataPoint('烟台市', Math.round(1800 * baseMultiplier), false, 1),
      ],
    },
    湖北省: {
      level: 1,
      levelName: '湖北省',
      parentId: 'country',
      dimension: 'sales',
      data: [
        createDataPoint('武汉市', Math.round(5200 * baseMultiplier), true, 1),
        createDataPoint('宜昌市', Math.round(1300 * baseMultiplier), false, 1),
        createDataPoint('襄阳市', Math.round(1000 * baseMultiplier), false, 1),
      ],
    },
  };

  const cityData: CityData = {
    朝阳区: {
      level: 2,
      levelName: '朝阳区',
      parentId: '北京市',
      dimension: 'sales',
      data: [
        createDataPoint('国贸商圈', Math.round(1800 * baseMultiplier), false, 2),
        createDataPoint('望京区域', Math.round(1500 * baseMultiplier), false, 2),
        createDataPoint('三里屯', Math.round(900 * baseMultiplier), false, 2),
      ],
    },
    海淀区: {
      level: 2,
      levelName: '海淀区',
      parentId: '北京市',
      dimension: 'sales',
      data: [
        createDataPoint('中关村', Math.round(1600 * baseMultiplier), false, 2),
        createDataPoint('上地', Math.round(1200 * baseMultiplier), false, 2),
        createDataPoint('五道口', Math.round(1000 * baseMultiplier), false, 2),
      ],
    },
    浦东新区: {
      level: 2,
      levelName: '浦东新区',
      parentId: '上海市',
      dimension: 'sales',
      data: [
        createDataPoint('陆家嘴', Math.round(2200 * baseMultiplier), false, 2),
        createDataPoint('张江', Math.round(1800 * baseMultiplier), false, 2),
        createDataPoint('金桥', Math.round(1200 * baseMultiplier), false, 2),
      ],
    },
    广州市: {
      level: 2,
      levelName: '广州市',
      parentId: '广东省',
      dimension: 'sales',
      data: [
        createDataPoint('天河区', Math.round(2200 * baseMultiplier), false, 2),
        createDataPoint('越秀区', Math.round(1500 * baseMultiplier), false, 2),
        createDataPoint('海珠区', Math.round(1500 * baseMultiplier), false, 2),
      ],
    },
    深圳市: {
      level: 2,
      levelName: '深圳市',
      parentId: '广东省',
      dimension: 'sales',
      data: [
        createDataPoint('南山区', Math.round(2800 * baseMultiplier), false, 2),
        createDataPoint('福田区', Math.round(1800 * baseMultiplier), false, 2),
        createDataPoint('龙岗区', Math.round(1200 * baseMultiplier), false, 2),
        createDataPoint('宝安区', Math.round(1000 * baseMultiplier), false, 2),
      ],
    },
    杭州市: {
      level: 2,
      levelName: '杭州市',
      parentId: '浙江省',
      dimension: 'sales',
      data: [
        createDataPoint('西湖区', Math.round(2000 * baseMultiplier), false, 2),
        createDataPoint('滨江区', Math.round(1500 * baseMultiplier), false, 2),
        createDataPoint('余杭区', Math.round(1000 * baseMultiplier), false, 2),
      ],
    },
    南京市: {
      level: 2,
      levelName: '南京市',
      parentId: '江苏省',
      dimension: 'sales',
      data: [
        createDataPoint('鼓楼区', Math.round(1800 * baseMultiplier), false, 2),
        createDataPoint('建邺区', Math.round(1400 * baseMultiplier), false, 2),
        createDataPoint('玄武区', Math.round(1000 * baseMultiplier), false, 2),
      ],
    },
    苏州市: {
      level: 2,
      levelName: '苏州市',
      parentId: '江苏省',
      dimension: 'sales',
      data: [
        createDataPoint('工业园区', Math.round(2000 * baseMultiplier), false, 2),
        createDataPoint('姑苏区', Math.round(1000 * baseMultiplier), false, 2),
        createDataPoint('虎丘区', Math.round(800 * baseMultiplier), false, 2),
      ],
    },
    成都市: {
      level: 2,
      levelName: '成都市',
      parentId: '四川省',
      dimension: 'sales',
      data: [
        createDataPoint('高新区', Math.round(2500 * baseMultiplier), false, 2),
        createDataPoint('锦江区', Math.round(1600 * baseMultiplier), false, 2),
        createDataPoint('武侯区', Math.round(1500 * baseMultiplier), false, 2),
      ],
    },
    济南市: {
      level: 2,
      levelName: '济南市',
      parentId: '山东省',
      dimension: 'sales',
      data: [
        createDataPoint('历下区', Math.round(1800 * baseMultiplier), false, 2),
        createDataPoint('市中区', Math.round(1200 * baseMultiplier), false, 2),
        createDataPoint('槐荫区', Math.round(800 * baseMultiplier), false, 2),
      ],
    },
    青岛市: {
      level: 2,
      levelName: '青岛市',
      parentId: '山东省',
      dimension: 'sales',
      data: [
        createDataPoint('市南区', Math.round(1600 * baseMultiplier), false, 2),
        createDataPoint('崂山区', Math.round(1200 * baseMultiplier), false, 2),
        createDataPoint('黄岛区', Math.round(800 * baseMultiplier), false, 2),
      ],
    },
    武汉市: {
      level: 2,
      levelName: '武汉市',
      parentId: '湖北省',
      dimension: 'sales',
      data: [
        createDataPoint('江汉区', Math.round(2200 * baseMultiplier), false, 2),
        createDataPoint('武昌区', Math.round(1800 * baseMultiplier), false, 2),
        createDataPoint('洪山区', Math.round(1200 * baseMultiplier), false, 2),
      ],
    },
  };

  return { country: countryData, province: provinceData, city: cityData };
}

const dimensionData: DimensionData = {
  sales: generateDimensionData(1),
  users: generateDimensionData(0.85),
  orders: generateDimensionData(1.2),
};

DIMENSIONS.forEach((dim) => {
  dimensionData[dim].country.dimension = dim;
  Object.values(dimensionData[dim].province).forEach((data) => {
    data.dimension = dim;
  });
  Object.values(dimensionData[dim].city).forEach((data) => {
    data.dimension = dim;
  });
});

export function getRelatedCharts(): RelatedChart[] {
  return [
    {
      id: 'chart-sales',
      title: '销售额',
      dimension: 'sales',
      chartType: 'bar',
      path: [],
      currentLevel: 0,
      isActive: true,
      isLinked: true,
    },
    {
      id: 'chart-users',
      title: '用户量',
      dimension: 'users',
      chartType: 'line',
      path: [],
      currentLevel: 0,
      isActive: true,
      isLinked: true,
    },
    {
      id: 'chart-orders',
      title: '订单量',
      dimension: 'orders',
      chartType: 'pie',
      path: [],
      currentLevel: 0,
      isActive: false,
      isLinked: false,
    },
  ];
}

export function getCountryData(dimension: string = 'sales'): LevelData {
  return dimensionData[dimension]?.country || dimensionData.sales.country;
}

export function getProvinceData(
  provinceName: string,
  dimension: string = 'sales'
): LevelData | null {
  return dimensionData[dimension]?.province[provinceName] || null;
}

export function getCityData(
  cityName: string,
  dimension: string = 'sales'
): LevelData | null {
  return dimensionData[dimension]?.city[cityName] || null;
}

export function getDataByPath(
  path: string[],
  dimension: string = 'sales'
): LevelData | null {
  if (path.length === 0) {
    return getCountryData(dimension);
  }
  if (path.length === 1) {
    return getProvinceData(path[0], dimension);
  }
  if (path.length >= 2) {
    return getCityData(path[path.length - 1], dimension);
  }
  return null;
}

export function hasNextLevel(path: string[]): boolean {
  const data = getDataByPath(path);
  if (!data) return false;
  return data.data.some((item) => item.hasChildren);
}

export function getDimensionName(dimension: string): string {
  return DIMENSION_NAMES[dimension] || dimension;
}

export function getAvailableDimensions(): string[] {
  return DIMENSIONS;
}

export function isSensitiveData(
  path: string[],
  itemName?: string
): boolean {
  if (path.length === 1) {
    return SENSITIVE_PROVINCES.includes(path[0]);
  }
  if (path.length >= 2) {
    return SENSITIVE_REGIONS.includes(path[path.length - 1]);
  }
  if (itemName) {
    return (
      SENSITIVE_PROVINCES.includes(itemName) ||
      SENSITIVE_REGIONS.includes(itemName)
    );
  }
  return false;
}

export { ROLE_CONFIG };

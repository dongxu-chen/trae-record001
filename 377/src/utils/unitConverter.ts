export interface UnitCategory {
  id: string;
  name: string;
  units: Unit[];
}

export interface Unit {
  id: string;
  name: string;
  symbol: string;
  toBase: (value: number) => number;
  fromBase: (value: number) => number;
}

const LENGTH_UNITS: Unit[] = [
  { id: 'm', name: '米', symbol: 'm', toBase: (v) => v, fromBase: (v) => v },
  { id: 'km', name: '千米', symbol: 'km', toBase: (v) => v * 1000, fromBase: (v) => v / 1000 },
  { id: 'cm', name: '厘米', symbol: 'cm', toBase: (v) => v * 0.01, fromBase: (v) => v / 0.01 },
  { id: 'mm', name: '毫米', symbol: 'mm', toBase: (v) => v * 0.001, fromBase: (v) => v / 0.001 },
  { id: 'mi', name: '英里', symbol: 'mi', toBase: (v) => v * 1609.344, fromBase: (v) => v / 1609.344 },
  { id: 'yd', name: '码', symbol: 'yd', toBase: (v) => v * 0.9144, fromBase: (v) => v / 0.9144 },
  { id: 'ft', name: '英尺', symbol: 'ft', toBase: (v) => v * 0.3048, fromBase: (v) => v / 0.3048 },
  { id: 'in', name: '英寸', symbol: 'in', toBase: (v) => v * 0.0254, fromBase: (v) => v / 0.0254 },
  { id: 'nm', name: '海里', symbol: 'nm', toBase: (v) => v * 1852, fromBase: (v) => v / 1852 },
];

const WEIGHT_UNITS: Unit[] = [
  { id: 'kg', name: '千克', symbol: 'kg', toBase: (v) => v, fromBase: (v) => v },
  { id: 'g', name: '克', symbol: 'g', toBase: (v) => v * 0.001, fromBase: (v) => v / 0.001 },
  { id: 'mg', name: '毫克', symbol: 'mg', toBase: (v) => v * 1e-6, fromBase: (v) => v / 1e-6 },
  { id: 't', name: '吨', symbol: 't', toBase: (v) => v * 1000, fromBase: (v) => v / 1000 },
  { id: 'lb', name: '磅', symbol: 'lb', toBase: (v) => v * 0.45359237, fromBase: (v) => v / 0.45359237 },
  { id: 'oz', name: '盎司', symbol: 'oz', toBase: (v) => v * 0.028349523125, fromBase: (v) => v / 0.028349523125 },
  { id: 'st', name: '英石', symbol: 'st', toBase: (v) => v * 6.35029318, fromBase: (v) => v / 6.35029318 },
];

const TEMPERATURE_UNITS: Unit[] = [
  {
    id: 'c',
    name: '摄氏度',
    symbol: '°C',
    toBase: (v) => v,
    fromBase: (v) => v,
  },
  {
    id: 'f',
    name: '华氏度',
    symbol: '°F',
    toBase: (v) => (v - 32) * 5 / 9,
    fromBase: (v) => (v * 9 / 5) + 32,
  },
  {
    id: 'k',
    name: '开尔文',
    symbol: 'K',
    toBase: (v) => v - 273.15,
    fromBase: (v) => v + 273.15,
  },
];

const AREA_UNITS: Unit[] = [
  { id: 'm2', name: '平方米', symbol: 'm²', toBase: (v) => v, fromBase: (v) => v },
  { id: 'km2', name: '平方千米', symbol: 'km²', toBase: (v) => v * 1e6, fromBase: (v) => v / 1e6 },
  { id: 'cm2', name: '平方厘米', symbol: 'cm²', toBase: (v) => v * 1e-4, fromBase: (v) => v / 1e-4 },
  { id: 'ha', name: '公顷', symbol: 'ha', toBase: (v) => v * 10000, fromBase: (v) => v / 10000 },
  { id: 'acre', name: '英亩', symbol: 'ac', toBase: (v) => v * 4046.8564224, fromBase: (v) => v / 4046.8564224 },
  { id: 'ft2', name: '平方英尺', symbol: 'ft²', toBase: (v) => v * 0.09290304, fromBase: (v) => v / 0.09290304 },
];

const VOLUME_UNITS: Unit[] = [
  { id: 'l', name: '升', symbol: 'L', toBase: (v) => v, fromBase: (v) => v },
  { id: 'ml', name: '毫升', symbol: 'mL', toBase: (v) => v * 0.001, fromBase: (v) => v / 0.001 },
  { id: 'm3', name: '立方米', symbol: 'm³', toBase: (v) => v * 1000, fromBase: (v) => v / 1000 },
  { id: 'gal', name: '加仑(美)', symbol: 'gal', toBase: (v) => v * 3.785411784, fromBase: (v) => v / 3.785411784 },
  { id: 'qt', name: '夸脱', symbol: 'qt', toBase: (v) => v * 0.946352946, fromBase: (v) => v / 0.946352946 },
  { id: 'pt', name: '品脱', symbol: 'pt', toBase: (v) => v * 0.473176473, fromBase: (v) => v / 0.473176473 },
  { id: 'floz', name: '液盎司', symbol: 'fl oz', toBase: (v) => v * 0.0295735295625, fromBase: (v) => v / 0.0295735295625 },
];

const DATA_UNITS: Unit[] = [
  { id: 'b', name: '比特', symbol: 'b', toBase: (v) => v, fromBase: (v) => v },
  { id: 'B', name: '字节', symbol: 'B', toBase: (v) => v * 8, fromBase: (v) => v / 8 },
  { id: 'KB', name: '千字节', symbol: 'KB', toBase: (v) => v * 8 * 1024, fromBase: (v) => v / (8 * 1024) },
  { id: 'MB', name: '兆字节', symbol: 'MB', toBase: (v) => v * 8 * 1024 * 1024, fromBase: (v) => v / (8 * 1024 * 1024) },
  { id: 'GB', name: '吉字节', symbol: 'GB', toBase: (v) => v * 8 * 1024 * 1024 * 1024, fromBase: (v) => v / (8 * 1024 * 1024 * 1024) },
  { id: 'TB', name: '太字节', symbol: 'TB', toBase: (v) => v * 8 * Math.pow(1024, 4), fromBase: (v) => v / (8 * Math.pow(1024, 4)) },
];

export const UNIT_CATEGORIES: UnitCategory[] = [
  { id: 'length', name: '长度', units: LENGTH_UNITS },
  { id: 'weight', name: '重量', units: WEIGHT_UNITS },
  { id: 'temperature', name: '温度', units: TEMPERATURE_UNITS },
  { id: 'area', name: '面积', units: AREA_UNITS },
  { id: 'volume', name: '体积', units: VOLUME_UNITS },
  { id: 'data', name: '数据', units: DATA_UNITS },
];

export function convert(
  value: number,
  fromUnitId: string,
  toUnitId: string,
  categoryId: string,
): number {
  const category = UNIT_CATEGORIES.find((c) => c.id === categoryId);
  if (!category) throw new Error(`未知类别: ${categoryId}`);
  const fromUnit = category.units.find((u) => u.id === fromUnitId);
  const toUnit = category.units.find((u) => u.id === toUnitId);
  if (!fromUnit || !toUnit) throw new Error('未知单位');
  const baseValue = fromUnit.toBase(value);
  return toUnit.fromBase(baseValue);
}

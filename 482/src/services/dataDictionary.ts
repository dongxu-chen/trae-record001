import { FieldDictionary, EnumValue } from '@/types';

const FIELD_DICTIONARIES: Record<string, Partial<FieldDictionary>> = {
  'user_id': {
    dataType: 'BIGINT',
    nullable: false,
    description: '用户唯一标识ID，系统自动生成',
    businessMeaning: '标识系统中的唯一用户，是用户维度的主键',
    enumValues: undefined,
    sampleValues: ['100001', '100002', '100003'],
    valueRange: { min: 1, max: 999999999 },
    patterns: ['纯数字', '自增序列'],
    relatedFields: ['dim_user.user_id', 'dwd_order.user_id', 'dws_user_behavior.user_id'],
  },
  'user_name': {
    dataType: 'VARCHAR(128)',
    nullable: true,
    description: '用户注册时填写的显示名称',
    businessMeaning: '用户在系统中的展示名称，可用于个性化推荐和用户画像',
    sampleValues: ['张三', 'John_Doe', 'user_2024'],
    patterns: ['中英文混合', '2-32个字符'],
    relatedFields: [],
  },
  'order_id': {
    dataType: 'BIGINT',
    nullable: false,
    description: '订单唯一标识ID，按时间戳+序列号生成',
    businessMeaning: '标识每笔交易订单的唯一编号',
    sampleValues: ['202605300001', '202605300002'],
    valueRange: { min: 202600000000, max: 202699999999 },
    patterns: ['年月日+序号', '12-14位数字'],
    relatedFields: [],
  },
  'amount': {
    dataType: 'DECIMAL(12,2)',
    nullable: false,
    description: '订单交易金额，精确到分',
    businessMeaning: '订单的实际支付金额，是财务统计和销售分析的核心指标',
    sampleValues: ['99.00', '158.50', '2999.00'],
    valueRange: { min: 0.01, max: 9999999.99 },
    patterns: ['两位小数', '正数'],
    relatedFields: ['sales_summary.total_amount'],
  },
  'total_amount': {
    dataType: 'DECIMAL(15,2)',
    nullable: false,
    description: '按日汇总的销售总金额',
    businessMeaning: '每日销售总额，用于经营日报和趋势分析',
    sampleValues: ['52800.00', '125600.50'],
    valueRange: { min: 0, max: 99999999.99 },
    patterns: ['SUM聚合', '两位小数'],
    relatedFields: ['dwd_order.amount'],
  },
  'behavior_count': {
    dataType: 'INT',
    nullable: false,
    description: '用户行为次数汇总',
    businessMeaning: '统计周期内用户的行为总次数，用于用户活跃度分析',
    sampleValues: ['15', '42', '128'],
    valueRange: { min: 0, max: 999999 },
    patterns: ['COUNT聚合', '非负整数'],
    relatedFields: [],
  },
  'status': {
    dataType: 'TINYINT',
    nullable: false,
    description: '订单状态码',
    businessMeaning: '标识订单当前所处的处理阶段',
    enumValues: [
      { value: '0', label: '待支付', description: '订单已创建但未支付', frequency: 15 },
      { value: '1', label: '已支付', description: '用户已完成支付', frequency: 60 },
      { value: '2', label: '已发货', description: '商家已发货', frequency: 15 },
      { value: '3', label: '已完成', description: '订单交易完成', frequency: 8 },
      { value: '-1', label: '已取消', description: '订单已取消', frequency: 2 },
    ],
    sampleValues: ['0', '1', '2', '3', '-1'],
    patterns: ['枚举值', '整数编码'],
    relatedFields: [],
  },
  'product_category': {
    dataType: 'VARCHAR(64)',
    nullable: true,
    description: '商品分类编码',
    businessMeaning: '标识商品所属的业务分类',
    enumValues: [
      { value: 'electronics', label: '电子产品', frequency: 35 },
      { value: 'clothing', label: '服装', frequency: 25 },
      { value: 'food', label: '食品', frequency: 20 },
      { value: 'home', label: '家居', frequency: 15 },
      { value: 'sports', label: '运动', frequency: 5 },
    ],
    sampleValues: ['electronics', 'clothing', 'food'],
    patterns: ['英文枚举', '小写字母'],
    relatedFields: [],
  },
};

export const getFieldDictionary = (fieldId: string, fieldName: string, table: string, database: string): FieldDictionary => {
  const partial = FIELD_DICTIONARIES[fieldName] || {};

  return {
    fieldId,
    fieldName,
    table,
    database,
    dataType: partial.dataType || 'VARCHAR(255)',
    nullable: partial.nullable ?? true,
    defaultValue: partial.defaultValue,
    description: partial.description || `${table}表的${fieldName}字段`,
    businessMeaning: partial.businessMeaning || `用于存储${fieldName}相关业务数据`,
    enumValues: partial.enumValues,
    sampleValues: partial.sampleValues || ['示例值1', '示例值2'],
    valueRange: partial.valueRange,
    patterns: partial.patterns || ['待识别'],
    relatedFields: partial.relatedFields || [],
    lastUpdated: new Date().toISOString().split('T')[0],
    updatedBy: '数据治理平台',
  };
};

export const getAllFieldDictionaries = (): FieldDictionary[] => {
  return Object.entries(FIELD_DICTIONARIES).map(([fieldName, partial]) => ({
    fieldId: `dict-${fieldName}`,
    fieldName,
    table: partial.sampleValues ? '' : '',
    database: '',
    dataType: partial.dataType || 'VARCHAR(255)',
    nullable: partial.nullable ?? true,
    defaultValue: partial.defaultValue,
    description: partial.description || `${fieldName}字段`,
    businessMeaning: partial.businessMeaning || `用于存储${fieldName}相关业务数据`,
    enumValues: partial.enumValues,
    sampleValues: partial.sampleValues || [],
    valueRange: partial.valueRange,
    patterns: partial.patterns || [],
    relatedFields: partial.relatedFields || [],
    lastUpdated: new Date().toISOString().split('T')[0],
    updatedBy: '数据治理平台',
  }));
};

export const hasEnumValues = (fieldName: string): boolean => {
  return !!FIELD_DICTIONARIES[fieldName]?.enumValues;
};

export const getFieldEnumValues = (fieldName: string): EnumValue[] => {
  return FIELD_DICTIONARIES[fieldName]?.enumValues || [];
};

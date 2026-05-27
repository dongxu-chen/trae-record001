import { Triple } from '@/types';

export const sampleTriples: Triple[] = [
  { subject: '任正非', predicate: '创立', object: '华为', subjectType: '人物', objectType: '公司', timestamp: 915148800000, startDate: '1999-01-01' },
  { subject: '华为', predicate: '总部在', object: '深圳', subjectType: '公司', objectType: '城市', timestamp: 915148800000, startDate: '1999-01-01' },
  { subject: '清华大学', predicate: '位于', object: '北京', subjectType: '学校', objectType: '城市', timestamp: 915148800000, startDate: '1999-01-01' },
  { subject: '马云', predicate: '创立', object: '阿里巴巴', subjectType: '人物', objectType: '公司', timestamp: 946684800000, startDate: '2000-01-01' },
  { subject: '阿里巴巴', predicate: '总部在', object: '杭州', subjectType: '公司', objectType: '城市', timestamp: 946684800000, startDate: '2000-01-01' },
  { subject: '腾讯', predicate: '总部在', object: '深圳', subjectType: '公司', objectType: '城市', timestamp: 978307200000, startDate: '2001-01-01' },
  { subject: '张三', predicate: '毕业于', object: '清华大学', subjectType: '人物', objectType: '学校', timestamp: 1262304000000, startDate: '2010-01-01' },
  { subject: '张三', predicate: '专业是', object: '计算机科学', subjectType: '人物', objectType: '学科', timestamp: 1262304000000, startDate: '2010-01-01' },
  { subject: '李四', predicate: '同学', object: '张三', subjectType: '人物', objectType: '人物', timestamp: 1262304000000, startDate: '2010-01-01' },
  { subject: '王五', predicate: '毕业于', object: '清华大学', subjectType: '人物', objectType: '学校', timestamp: 1262304000000, startDate: '2010-01-01' },
  { subject: '张三', predicate: '就职于', object: '华为', subjectType: '人物', objectType: '公司', timestamp: 1388534400000, startDate: '2014-01-01' },
  { subject: '赵六', predicate: '同事', object: '张三', subjectType: '人物', objectType: '人物', timestamp: 1388534400000, startDate: '2014-01-01' },
  { subject: '李四', predicate: '就职于', object: '阿里巴巴', subjectType: '人物', objectType: '公司', timestamp: 1388534400000, startDate: '2014-01-01' },
  { subject: '王五', predicate: '就职于', object: '腾讯', subjectType: '人物', objectType: '公司', timestamp: 1388534400000, startDate: '2014-01-01' },
  { subject: '腾讯', predicate: '产品有', object: '微信', subjectType: '公司', objectType: '产品', timestamp: 1420070400000, startDate: '2015-01-01' },
  { subject: '微信', predicate: '用户', object: '张三', subjectType: '产品', objectType: '人物', timestamp: 1451606400000, startDate: '2016-01-01' },
  { subject: '微信', predicate: '用户', object: '李四', subjectType: '产品', objectType: '人物', timestamp: 1451606400000, startDate: '2016-01-01' },
  { subject: '华为', predicate: '产品有', object: 'Mate60', subjectType: '公司', objectType: '产品', timestamp: 1693526400000, startDate: '2023-09-01' },
  { subject: 'Mate60', predicate: '芯片', object: '麒麟9000S', subjectType: '产品', objectType: '芯片', timestamp: 1693526400000, startDate: '2023-09-01' },
  { subject: '麒麟9000S', predicate: '生产于', object: '中芯国际', subjectType: '芯片', objectType: '公司', timestamp: 1693526400000, startDate: '2023-09-01' },
  { subject: '华为', predicate: '创始人', object: '任正非', subjectType: '公司', objectType: '人物', timestamp: 915148800000, startDate: '1999-01-01' },
  { subject: '阿里巴巴', predicate: '创始人', object: '马云', subjectType: '公司', objectType: '人物', timestamp: 946684800000, startDate: '2000-01-01' },
];

export const MIN_TIMESTAMP = 915148800000;
export const MAX_TIMESTAMP = 1735689600000;

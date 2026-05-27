require('dotenv').config();
const mongoose = require('mongoose');
const { MongoMemoryServer } = require('mongodb-memory-server');
const User = require('../models/User');
const Template = require('../models/Template');
const Comment = require('../models/Comment');

const mockUsers = [
  {
    username: 'admin',
    email: 'admin@example.com',
    password: '123456',
    role: 'admin',
    avatar: '',
    bio: '平台管理员'
  },
  {
    username: 'creator1',
    email: 'creator1@example.com',
    password: '123456',
    role: 'creator',
    avatar: '',
    bio: '数据可视化设计师，专注于企业级仪表板设计'
  },
  {
    username: 'user1',
    email: 'user1@example.com',
    password: '123456',
    role: 'user',
    avatar: '',
    bio: ''
  }
];

const mockTemplates = [
  {
    title: '企业运营数据总览',
    description: '全面展示企业核心运营指标，包括用户增长、活跃度、转化率等关键数据，帮助管理层快速了解业务整体状况。',
    category: 'operation',
    price: 0,
    tags: ['运营', '总览', 'KPI'],
    complexity: 'complex',
    thumbnail: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=dashboard%20operation%20overview%20dark%20theme&image_size=square_hd',
    previewImages: [
      'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=dashboard%20operation%20overview%20dark%20theme&image_size=square_hd'
    ],
    fileUrl: '',
    components: [
      {
        id: '1',
        type: 'metric',
        title: '日活用户',
        position: { x: 0, y: 0 },
        size: { w: 3, h: 1 },
        config: { value: '12,580', trend: '+12.5%', color: '#10B981' },
        dataSource: { type: 'static', data: [] }
      },
      {
        id: '2',
        type: 'chart',
        chartType: 'line',
        title: '用户增长趋势',
        position: { x: 0, y: 1 },
        size: { w: 8, h: 3 },
        config: {},
        dataSource: { type: 'static', data: [] }
      },
      {
        id: '3',
        type: 'chart',
        chartType: 'bar',
        title: '渠道分布',
        position: { x: 8, y: 1 },
        size: { w: 4, h: 3 },
        config: {},
        dataSource: { type: 'static', data: [] }
      }
    ],
    layout: {
      gridCols: 12,
      gridRows: 8,
      gutter: 16,
      backgroundColor: '#0F172A'
    }
  },
  {
    title: '销售业绩分析仪表板',
    description: '深度分析销售数据，包括销售额趋势、区域分布、产品销量排行、销售员业绩对比等功能。',
    category: 'sales',
    price: 99,
    tags: ['销售', '业绩', '分析'],
    complexity: 'medium',
    thumbnail: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=sales%20dashboard%20analytics%20dark%20theme&image_size=square_hd',
    previewImages: [
      'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=sales%20dashboard%20analytics%20dark%20theme&image_size=square_hd'
    ],
    fileUrl: '',
    components: [],
    layout: {
      gridCols: 12,
      gridRows: 8,
      gutter: 16,
      backgroundColor: '#0F172A'
    }
  },
  {
    title: '财务收支管理面板',
    description: '实时监控企业财务状况，包括收入、支出、利润、现金流等核心财务指标的可视化展示。',
    category: 'finance',
    price: 199,
    tags: ['财务', '收支', '利润'],
    complexity: 'complex',
    thumbnail: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=finance%20dashboard%20money%20chart%20dark%20theme&image_size=square_hd',
    previewImages: [
      'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=finance%20dashboard%20money%20chart%20dark%20theme&image_size=square_hd'
    ],
    fileUrl: '',
    components: [],
    layout: {
      gridCols: 12,
      gridRows: 8,
      gutter: 16,
      backgroundColor: '#0F172A'
    }
  },
  {
    title: '系统运维监控中心',
    description: '全方位监控服务器状态、网络流量、CPU、内存、磁盘使用率等运维关键指标，支持告警通知。',
    category: 'ops',
    price: 149,
    tags: ['运维', '监控', '服务器'],
    complexity: 'complex',
    thumbnail: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=devops%20monitoring%20dashboard%20server%20dark%20theme&image_size=square_hd',
    previewImages: [
      'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=devops%20monitoring%20dashboard%20server%20dark%20theme&image_size=square_hd'
    ],
    fileUrl: '',
    components: [],
    layout: {
      gridCols: 12,
      gridRows: 8,
      gutter: 16,
      backgroundColor: '#0F172A'
    }
  },
  {
    title: '电商运营数据看板',
    description: '专注电商场景，展示GMV、订单量、转化率、客单价、复购率等核心电商指标。',
    category: 'operation',
    price: 0,
    tags: ['电商', '运营', 'GMV'],
    complexity: 'medium',
    thumbnail: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=ecommerce%20dashboard%20shopping%20dark%20theme&image_size=square_hd',
    previewImages: [
      'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=ecommerce%20dashboard%20shopping%20dark%20theme&image_size=square_hd'
    ],
    fileUrl: '',
    components: [],
    layout: {
      gridCols: 12,
      gridRows: 8,
      gutter: 16,
      backgroundColor: '#0F172A'
    }
  },
  {
    title: '销售漏斗分析模板',
    description: '可视化展示销售漏斗各阶段转化情况，帮助销售团队识别瓶颈，优化销售流程。',
    category: 'sales',
    price: 59,
    tags: ['销售', '漏斗', '转化'],
    complexity: 'simple',
    thumbnail: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=sales%20funnel%20chart%20dashboard%20dark%20theme&image_size=square_hd',
    previewImages: [
      'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=sales%20funnel%20chart%20dashboard%20dark%20theme&image_size=square_hd'
    ],
    fileUrl: '',
    components: [],
    layout: {
      gridCols: 12,
      gridRows: 8,
      gutter: 16,
      backgroundColor: '#0F172A'
    }
  },
  {
    title: '预算执行跟踪仪表板',
    description: '追踪各部门预算执行情况，对比预算与实际支出，分析预算偏差原因。',
    category: 'finance',
    price: 79,
    tags: ['预算', '财务', '跟踪'],
    complexity: 'medium',
    thumbnail: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=budget%20tracking%20finance%20dashboard%20dark%20theme&image_size=square_hd',
    previewImages: [
      'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=budget%20tracking%20finance%20dashboard%20dark%20theme&image_size=square_hd'
    ],
    fileUrl: '',
    components: [],
    layout: {
      gridCols: 12,
      gridRows: 8,
      gutter: 16,
      backgroundColor: '#0F172A'
    }
  },
  {
    title: '应用性能监控面板',
    description: '实时监控Web应用性能指标，包括响应时间、错误率、APM、QPS等关键性能数据。',
    category: 'ops',
    price: 129,
    tags: ['APM', '性能', '监控'],
    complexity: 'medium',
    thumbnail: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=application%20performance%20monitoring%20dashboard%20dark%20theme&image_size=square_hd',
    previewImages: [
      'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=application%20performance%20monitoring%20dashboard%20dark%20theme&image_size=square_hd'
    ],
    fileUrl: '',
    components: [],
    layout: {
      gridCols: 12,
      gridRows: 8,
      gutter: 16,
      backgroundColor: '#0F172A'
    }
  }
];

const mockComments = [
  {
    content: '模板设计非常专业，组件丰富，大大提高了我们的开发效率！',
    rating: 5
  },
  {
    content: '界面美观，数据展示清晰，值得推荐。',
    rating: 4
  },
  {
    content: '布局合理，配色舒服，已经用到了项目中。',
    rating: 5
  }
];

const seedDatabase = async () => {
  try {
    const mongod = await MongoMemoryServer.create();
    const uri = mongod.getUri();
    console.log('使用内存 MongoDB:', uri);
    await mongoose.connect(uri);
    
    await User.deleteMany({});
    await Template.deleteMany({});
    await Comment.deleteMany({});

    const users = await User.create(mockUsers);
    console.log('用户数据插入成功');

    const templatesWithAuthor = mockTemplates.map(template => ({
      ...template,
      author: users[1]._id,
      downloadCount: Math.floor(Math.random() * 1000),
      viewCount: Math.floor(Math.random() * 5000),
      rating: 4 + Math.random(),
      ratingCount: Math.floor(Math.random() * 100)
    }));

    const templates = await Template.create(templatesWithAuthor);
    console.log('模板数据插入成功');

    for (let i = 0; i < 5; i++) {
      const template = templates[i % templates.length];
      const user = users[2];
      
      await Comment.create({
        ...mockComments[i % mockComments.length],
        templateId: template._id,
        userId: user._id
      });
    }
    console.log('评论数据插入成功');

    console.log('Mock 数据初始化完成');
    process.exit(0);
  } catch (error) {
    console.error('数据初始化失败:', error);
    process.exit(1);
  }
};

seedDatabase();

export const DOCUMENT_TEMPLATES = [
  {
    id: 'meeting-minutes',
    name: '会议纪要',
    icon: '📋',
    category: '办公',
    description: '记录会议内容、决议和行动计划',
    content: [
      {
        type: 'heading-one',
        children: [{ text: '会议纪要' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '会议时间：', bold: true }, { text: '________________' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '会议地点：', bold: true }, { text: '________________' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '参会人员：', bold: true }, { text: '________________' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '一、会议议题' }],
      },
      {
        type: 'bulleted-list',
        children: [
          {
            type: 'list-item',
            children: [{ text: '议题一' }],
          },
          {
            type: 'list-item',
            children: [{ text: '议题二' }],
          },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '二、讨论内容' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '在此记录会议讨论的主要内容...' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '三、决议事项' }],
      },
      {
        type: 'numbered-list',
        children: [
          {
            type: 'list-item',
            children: [{ text: '决议一：' }],
          },
          {
            type: 'list-item',
            children: [{ text: '决议二：' }],
          },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '四、行动计划' }],
      },
      {
        type: 'paragraph',
        children: [
          { text: '| 任务 | 负责人 | 截止日期 | 状态 |', bold: true },
        ],
      },
      {
        type: 'paragraph',
        children: [{ text: '| --- | --- | --- | --- |' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '| 任务1 |  |  | 待办 |' }],
      },
    ],
  },
  {
    id: 'project-proposal',
    name: '项目提案',
    icon: '📊',
    category: '办公',
    description: '正式的项目立项和审批文档',
    content: [
      {
        type: 'heading-one',
        children: [{ text: '项目提案' }],
      },
      {
        type: 'block-quote',
        children: [
          { text: '项目名称：', bold: true },
          { text: '________________' },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '一、项目背景' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '阐述项目发起的背景和原因...' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '二、项目目标' }],
      },
      {
        type: 'bulleted-list',
        children: [
          {
            type: 'list-item',
            children: [{ text: '目标一：' }],
          },
          {
            type: 'list-item',
            children: [{ text: '目标二：' }],
          },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '三、项目范围' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '说明项目的涵盖范围和边界...' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '四、实施计划' }],
      },
      {
        type: 'numbered-list',
        children: [
          {
            type: 'list-item',
            children: [{ text: '第一阶段：' }],
          },
          {
            type: 'list-item',
            children: [{ text: '第二阶段：' }],
          },
          {
            type: 'list-item',
            children: [{ text: '第三阶段：' }],
          },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '五、资源需求' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '人力、预算、设备等资源需求...' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '六、风险评估' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '潜在风险及应对措施...' }],
      },
    ],
  },
  {
    id: 'weekly-report',
    name: '周报',
    icon: '📅',
    category: '办公',
    description: '周工作总结和下周计划',
    content: [
      {
        type: 'heading-one',
        children: [{ text: '周工作报告' }],
      },
      {
        type: 'paragraph',
        children: [
          { text: '报告周期：', bold: true },
          { text: '____年____月____日 - ____年____月____日' },
        ],
      },
      {
        type: 'paragraph',
        children: [
          { text: '报告人：', bold: true },
          { text: '________' },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '一、本周工作完成情况' }],
      },
      {
        type: 'numbered-list',
        children: [
          {
            type: 'list-item',
            children: [{ text: '工作项一：完成度 ____%' }],
          },
          {
            type: 'list-item',
            children: [{ text: '工作项二：完成度 ____%' }],
          },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '二、遇到的问题' }],
      },
      {
        type: 'bulleted-list',
        children: [
          {
            type: 'list-item',
            children: [{ text: '问题一：' }],
          },
          {
            type: 'list-item',
            children: [{ text: '问题二：' }],
          },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '三、下周工作计划' }],
      },
      {
        type: 'numbered-list',
        children: [
          {
            type: 'list-item',
            children: [{ text: '计划一：' }],
          },
          {
            type: 'list-item',
            children: [{ text: '计划二：' }],
          },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '四、需要的支持' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '资源、协调等方面的需求...' }],
      },
    ],
  },
  {
    id: 'resume',
    name: '个人简历',
    icon: '👤',
    category: '个人',
    description: '专业的求职简历模板',
    content: [
      {
        type: 'heading-one',
        children: [{ text: '个人简历' }],
      },
      {
        type: 'paragraph',
        children: [
          { text: '姓名：', bold: true },
          { text: '________' },
          { text: '  电话：', bold: true },
          { text: '________' },
          { text: '  邮箱：', bold: true },
          { text: '________' },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '个人简介' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '简要介绍个人背景、专业领域和核心优势...' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '工作经历' }],
      },
      {
        type: 'paragraph',
        children: [
          { text: '公司名称 - 职位', bold: true },
          { text: ' （20XX.XX - 至今）' },
        ],
      },
      {
        type: 'bulleted-list',
        children: [
          {
            type: 'list-item',
            children: [{ text: '主要职责和业绩...' }],
          },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '教育背景' }],
      },
      {
        type: 'paragraph',
        children: [
          { text: '学校名称 - 专业', bold: true },
          { text: ' （20XX.XX - 20XX.XX）' },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '专业技能' }],
      },
      {
        type: 'paragraph',
        children: [
          { text: '• 技术栈：' },
          { text: '\n• 语言能力：' },
          { text: '\n• 其他技能：' },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '项目经验' }],
      },
      {
        type: 'paragraph',
        children: [
          { text: '项目名称', bold: true },
          { text: ' - 项目描述' },
        ],
      },
    ],
  },
  {
    id: 'business-letter',
    name: '商务信函',
    icon: '✉️',
    category: '办公',
    description: '正式的商务沟通信函',
    content: [
      {
        type: 'paragraph',
        children: [{ text: '发件人：' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '日期：________年____月____日' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '收件人：' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '地址：' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '尊敬的________：' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '您好！' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '在此处写明信函的主要内容...' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '期待您的回复。' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '此致' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '敬礼！' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '________（签名）' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '________年____月____日' }],
      },
    ],
  },
  {
    id: 'technical-doc',
    name: '技术文档',
    icon: '💻',
    category: '技术',
    description: '产品技术说明和API文档',
    content: [
      {
        type: 'heading-one',
        children: [{ text: '技术文档' }],
      },
      {
        type: 'block-quote',
        children: [
          { text: '版本：', bold: true },
          { text: 'v1.0' },
          { text: '  最后更新：', bold: true },
          { text: '________' },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '1. 概述' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '介绍项目的背景、目标和适用范围...' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '2. 系统架构' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '描述系统的整体架构、模块划分...' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '3. API 接口' }],
      },
      {
        type: 'code-block',
        children: [
          { text: 'GET /api/v1/users\n' },
          { text: '描述：获取用户列表\n' },
          { text: '参数：\n' },
          { text: '  - page: 页码\n' },
          { text: '  - size: 每页数量\n' },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '4. 部署说明' }],
      },
      {
        type: 'numbered-list',
        children: [
          {
            type: 'list-item',
            children: [{ text: '环境要求' }],
          },
          {
            type: 'list-item',
            children: [{ text: '部署步骤' }],
          },
          {
            type: 'list-item',
            children: [{ text: '配置说明' }],
          },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '5. 常见问题' }],
      },
      {
        type: 'paragraph',
        children: [{ text: 'Q: 问题描述？' }],
      },
      {
        type: 'paragraph',
        children: [{ text: 'A: 解答...' }],
      },
    ],
  },
  {
    id: 'personal-note',
    name: '个人笔记',
    icon: '📝',
    category: '个人',
    description: '简洁的笔记和学习记录模板',
    content: [
      {
        type: 'heading-one',
        children: [{ text: '笔记标题' }],
      },
      {
        type: 'paragraph',
        children: [
          { text: '日期：', italic: true },
          { text: '________', italic: true },
          { text: '  标签：', italic: true },
          { text: '#标签1 #标签2', italic: true },
        ],
      },
      {
        type: 'thematic-break',
        children: [{ text: '' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '📌 核心要点' }],
      },
      {
        type: 'bulleted-list',
        children: [
          {
            type: 'list-item',
            children: [{ text: '要点一' }],
          },
          {
            type: 'list-item',
            children: [{ text: '要点二' }],
          },
        ],
      },
      {
        type: 'heading-two',
        children: [{ text: '📝 详细内容' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '在此记录详细内容...' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '💡 思考与启发' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '记录你的思考和感悟...' }],
      },
      {
        type: 'heading-two',
        children: [{ text: '🔗 参考资料' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '相关链接和参考...' }],
      },
    ],
  },
  {
    id: 'blank',
    name: '空白文档',
    icon: '📄',
    category: '基础',
    description: '从零开始创建文档',
    content: [
      {
        type: 'heading-one',
        children: [{ text: '文档标题' }],
      },
      {
        type: 'paragraph',
        children: [{ text: '开始编写你的内容...' }],
      },
    ],
  },
];

export const TEMPLATE_CATEGORIES = [
  { id: 'all', name: '全部', icon: '📁' },
  { id: '办公', name: '办公', icon: '💼' },
  { id: '个人', name: '个人', icon: '👤' },
  { id: '技术', name: '技术', icon: '💻' },
  { id: '基础', name: '基础', icon: '📄' },
];

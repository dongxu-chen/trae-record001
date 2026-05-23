export const flowchartTemplates = [
  {
    id: 'leave-approval',
    name: '请假审批',
    description: '企业员工请假审批流程',
    thumbnail: '📋',
    nodes: [
      { id: 1, nodeType: 'start', name: '开始', description: '', x: 150, y: 150 },
      { id: 2, nodeType: 'process', name: '填写请假单', description: '员工填写请假申请单', x: 350, y: 100 },
      { id: 3, nodeType: 'decision', name: '审批天数', description: '判断请假天数', x: 550, y: 150 },
      { id: 4, nodeType: 'process', name: '部门经理审批', description: '3天以内部门经理审批', x: 750, y: 80 },
      { id: 5, nodeType: 'process', name: '总经理审批', description: '3天以上需要总经理审批', x: 750, y: 220 },
      { id: 6, nodeType: 'decision', name: '是否批准', description: '判断审批结果', x: 950, y: 150 },
      { id: 7, nodeType: 'process', name: '通知结果', description: '通知员工审批结果', x: 1150, y: 100 },
      { id: 8, nodeType: 'end', name: '结束', description: '', x: 1150, y: 220 }
    ],
    connections: [
      { id: 1, fromNodeId: 1, toNodeId: 2 },
      { id: 2, fromNodeId: 2, toNodeId: 3 },
      { id: 3, fromNodeId: 3, toNodeId: 4 },
      { id: 4, fromNodeId: 3, toNodeId: 5 },
      { id: 5, fromNodeId: 4, toNodeId: 6 },
      { id: 6, fromNodeId: 5, toNodeId: 6 },
      { id: 7, fromNodeId: 6, toNodeId: 7 },
      { id: 8, fromNodeId: 6, toNodeId: 8 },
      { id: 9, fromNodeId: 7, toNodeId: 8 }
    ]
  },
  {
    id: 'order-process',
    name: '订单处理',
    description: '电商订单处理流程',
    thumbnail: '🛒',
    nodes: [
      { id: 1, nodeType: 'start', name: '客户下单', description: '', x: 150, y: 150 },
      { id: 2, nodeType: 'process', name: '支付验证', description: '验证支付是否成功', x: 350, y: 150 },
      { id: 3, nodeType: 'decision', name: '支付成功?', description: '检查支付状态', x: 550, y: 150 },
      { id: 4, nodeType: 'process', name: '库存检查', description: '检查商品库存', x: 750, y: 80 },
      { id: 5, nodeType: 'process', name: '订单取消', description: '取消订单并通知', x: 750, y: 220 },
      { id: 6, nodeType: 'decision', name: '有库存?', description: '判断库存是否充足', x: 950, y: 80 },
      { id: 7, nodeType: 'process', name: '发货', description: '安排物流发货', x: 1150, y: 40 },
      { id: 8, nodeType: 'process', name: '采购补货', description: '通知采购部门补货', x: 1150, y: 140 },
      { id: 9, nodeType: 'process', name: '客户签收', description: '客户确认收货', x: 1350, y: 80 },
      { id: 10, nodeType: 'end', name: '完成', description: '', x: 1350, y: 220 }
    ],
    connections: [
      { id: 1, fromNodeId: 1, toNodeId: 2 },
      { id: 2, fromNodeId: 2, toNodeId: 3 },
      { id: 3, fromNodeId: 3, toNodeId: 4 },
      { id: 4, fromNodeId: 3, toNodeId: 5 },
      { id: 5, fromNodeId: 4, toNodeId: 6 },
      { id: 6, fromNodeId: 6, toNodeId: 7 },
      { id: 7, fromNodeId: 6, toNodeId: 8 },
      { id: 8, fromNodeId: 7, toNodeId: 9 },
      { id: 9, fromNodeId: 9, toNodeId: 10 },
      { id: 10, fromNodeId: 5, toNodeId: 10 },
      { id: 11, fromNodeId: 8, toNodeId: 7 }
    ]
  },
  {
    id: 'bug-fix',
    name: 'Bug修复流程',
    description: '软件开发Bug修复流程',
    thumbnail: '🐛',
    nodes: [
      { id: 1, nodeType: 'start', name: '发现Bug', description: '', x: 150, y: 150 },
      { id: 2, nodeType: 'process', name: '提交Bug报告', description: '详细描述Bug信息', x: 350, y: 150 },
      { id: 3, nodeType: 'process', name: 'Bug分级', description: '按严重程度分级', x: 550, y: 150 },
      { id: 4, nodeType: 'decision', name: '是否紧急?', description: '判断优先级', x: 750, y: 150 },
      { id: 5, nodeType: 'process', name: '立即修复', description: '高优先级立即处理', x: 950, y: 80 },
      { id: 6, nodeType: 'process', name: '排入待办', description: '低优先级排期处理', x: 950, y: 220 },
      { id: 7, nodeType: 'process', name: '开发修复', description: '开发人员修复', x: 1150, y: 150 },
      { id: 8, nodeType: 'process', name: '测试验证', description: '测试人员验证修复', x: 1350, y: 150 },
      { id: 9, nodeType: 'decision', name: '验证通过?', description: '检查是否修复', x: 1550, y: 150 },
      { id: 10, nodeType: 'end', name: '关闭Bug', description: '', x: 1750, y: 80 },
      { id: 11, nodeType: 'process', name: '重新修复', description: '退回开发重新修复', x: 1750, y: 220 }
    ],
    connections: [
      { id: 1, fromNodeId: 1, toNodeId: 2 },
      { id: 2, fromNodeId: 2, toNodeId: 3 },
      { id: 3, fromNodeId: 3, toNodeId: 4 },
      { id: 4, fromNodeId: 4, toNodeId: 5 },
      { id: 5, fromNodeId: 4, toNodeId: 6 },
      { id: 6, fromNodeId: 5, toNodeId: 7 },
      { id: 7, fromNodeId: 6, toNodeId: 7 },
      { id: 8, fromNodeId: 7, toNodeId: 8 },
      { id: 9, fromNodeId: 8, toNodeId: 9 },
      { id: 10, fromNodeId: 9, toNodeId: 10 },
      { id: 11, fromNodeId: 9, toNodeId: 11 },
      { id: 12, fromNodeId: 11, toNodeId: 7 }
    ]
  },
  {
    id: 'onboarding',
    name: '新员工入职',
    description: '企业新员工入职流程',
    thumbnail: '👋',
    nodes: [
      { id: 1, nodeType: 'start', name: '入职登记', description: '', x: 150, y: 150 },
      { id: 2, nodeType: 'process', name: '办理入职手续', description: '签订合同、填写资料', x: 350, y: 150 },
      { id: 3, nodeType: 'process', name: 'IT配置', description: '配置电脑、账号权限', x: 550, y: 80 },
      { id: 4, nodeType: 'process', name: 'HR培训', description: '公司制度、文化培训', x: 550, y: 220 },
      { id: 5, nodeType: 'process', name: '部门分配', description: '分配到具体部门', x: 750, y: 150 },
      { id: 6, nodeType: 'process', name: '岗位培训', description: '岗位职责、技能培训', x: 950, y: 150 },
      { id: 7, nodeType: 'process', name: '导师安排', description: '安排入职导师', x: 1150, y: 150 },
      { id: 8, nodeType: 'end', name: '试用期开始', description: '', x: 1350, y: 150 }
    ],
    connections: [
      { id: 1, fromNodeId: 1, toNodeId: 2 },
      { id: 2, fromNodeId: 2, toNodeId: 3 },
      { id: 3, fromNodeId: 2, toNodeId: 4 },
      { id: 4, fromNodeId: 3, toNodeId: 5 },
      { id: 5, fromNodeId: 4, toNodeId: 5 },
      { id: 6, fromNodeId: 5, toNodeId: 6 },
      { id: 7, fromNodeId: 6, toNodeId: 7 },
      { id: 8, fromNodeId: 7, toNodeId: 8 }
    ]
  }
]

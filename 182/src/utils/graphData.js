import { v4 as uuidv4 } from 'uuid'

export const NODE_TYPES = {
  RECTANGLE: 'rectangle',
  CIRCLE: 'circle',
  DIAMOND: 'diamond',
  PARALLELOGRAM: 'parallelogram',
  DOCUMENT: 'document',
  GROUP: 'group'
}

export const NODE_CONFIGS = {
  [NODE_TYPES.RECTANGLE]: {
    name: '矩形',
    width: 120,
    height: 60,
    fill: '#fff',
    stroke: '#1890ff',
    strokeWidth: 2
  },
  [NODE_TYPES.CIRCLE]: {
    name: '圆形',
    width: 80,
    height: 80,
    fill: '#fff',
    stroke: '#52c41a',
    strokeWidth: 2
  },
  [NODE_TYPES.DIAMOND]: {
    name: '菱形',
    width: 100,
    height: 80,
    fill: '#fff',
    stroke: '#faad14',
    strokeWidth: 2
  },
  [NODE_TYPES.PARALLELOGRAM]: {
    name: '平行四边形',
    width: 120,
    height: 60,
    fill: '#fff',
    stroke: '#722ed1',
    strokeWidth: 2
  },
  [NODE_TYPES.DOCUMENT]: {
    name: '文档',
    width: 100,
    height: 120,
    fill: '#fff',
    stroke: '#eb2f96',
    strokeWidth: 2
  },
  [NODE_TYPES.GROUP]: {
    name: '分组',
    width: 200,
    height: 150,
    fill: 'rgba(24, 144, 255, 0.1)',
    stroke: '#1890ff',
    strokeWidth: 1,
    strokeDashArray: [5, 5]
  }
}

export function createNode(type, x = 100, y = 100, label = '') {
  const config = NODE_CONFIGS[type]
  return {
    id: uuidv4(),
    type,
    x,
    y,
    width: config.width,
    height: config.height,
    label: label || config.name,
    fill: config.fill,
    stroke: config.stroke,
    strokeWidth: config.strokeWidth,
    strokeDashArray: config.strokeDashArray || [],
    fontSize: 14,
    fontColor: '#333',
    groupId: null,
    collapsed: false,
    childNodes: [],
    isGroup: type === NODE_TYPES.GROUP
  }
}

export function createEdge(sourceId, targetId, label = '') {
  return {
    id: uuidv4(),
    sourceId,
    targetId,
    label,
    stroke: '#666',
    strokeWidth: 2,
    fontSize: 12,
    fontColor: '#333',
    points: [],
    orthogonal: true
  }
}

export function createGroup(nodeIds, x = 100, y = 100) {
  const group = createNode(NODE_TYPES.GROUP, x, y, '分组')
  group.childNodes = [...nodeIds]
  group.collapsed = false
  return group
}

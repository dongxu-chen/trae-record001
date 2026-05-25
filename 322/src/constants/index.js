export const ANNOTATION_TYPES = {
  RECTANGLE: 'rectangle',
  ARROW: 'arrow',
  TEXT: 'text'
}

export const ANNOTATION_CATEGORIES = [
  { id: 'data_region', name: '数据区域', color: '#409eff', description: '图表中的数据展示区域' },
  { id: 'title', name: '标题', color: '#67c23a', description: '图表标题和副标题' },
  { id: 'axis_label', name: '轴标签', color: '#e6a23c', description: 'X轴、Y轴标签和刻度' },
  { id: 'legend', name: '图例', color: '#f56c6c', description: '图表图例说明' }
]

export const TOOL_MODES = {
  SELECT: 'select',
  RECTANGLE: 'rectangle',
  ARROW: 'arrow',
  TEXT: 'text',
  PAN: 'pan'
}

export const CONNECTION_STATUS = {
  CONNECTING: 'connecting',
  ONLINE: 'online',
  OFFLINE: 'offline'
}

export const QUALITY_CHECK_RULES = {
  MIN_ANNOTATIONS: 3,
  MIN_SIZE: 20,
  OVERLAP_THRESHOLD: 0.8,
  REQUIRED_CATEGORIES: ['title', 'axis_label', 'data_region'],
  POSITION_TOLERANCE: 0.15,
  TITLE_WIDTH_RATIO: { MIN: 0.3, MAX: 0.95 },
  AXIS_LABEL_POSITION_TOLERANCE: 0.1
}

export const SNAP_CONFIG = {
  ENABLED: true,
  THRESHOLD: 15,
  SMOOTHING_FACTOR: 0.3,
  EDGE_TYPES: ['left', 'right', 'top', 'bottom', 'hcenter', 'vcenter'],
  SHOW_GUIDELINES: true,
  GUIDELINE_COLOR: '#409eff',
  GUIDELINE_OPACITY: 0.6
}

export const OT_OPERATION_TYPES = {
  CREATE: 'create',
  UPDATE: 'update',
  DELETE: 'delete',
  MOVE: 'move',
  RESIZE: 'resize'
}

export const WS_MESSAGE_TYPES = {
  JOIN: 'join',
  LEAVE: 'leave',
  USERS_UPDATE: 'users_update',
  ANNOTATION_ADD: 'annotation_add',
  ANNOTATION_UPDATE: 'annotation_update',
  ANNOTATION_DELETE: 'annotation_delete',
  IMAGE_LOAD: 'image_load',
  CURSOR_MOVE: 'cursor_move',
  UNDO: 'undo',
  REDO: 'redo',
  OT_OPERATION: 'ot_operation',
  OT_ACK: 'ot_ack',
  OT_SYNC: 'ot_sync'
}

export const AI_PREANNOTATION_CONFIG = {
  ENABLED: true,
  DEFAULT_CONFIDENCE: 0.7,
  MIN_CONFIDENCE: 0.5,
  AUTO_ACCEPT_THRESHOLD: 0.85,
  MAX_DETECTIONS: 10,
  SUPPORTED_TYPES: ['title', 'axis_label', 'legend', 'data_region']
}

export const DEFAULT_SHORTCUTS = {
  SELECT: { key: 'v', ctrl: false, alt: false, shift: false, description: '选择工具' },
  RECTANGLE: { key: 'r', ctrl: false, alt: false, shift: false, description: '矩形框工具' },
  ARROW: { key: 'a', ctrl: false, alt: false, shift: false, description: '箭头工具' },
  TEXT: { key: 't', ctrl: false, alt: false, shift: false, description: '文本工具' },
  PAN: { key: 'h', ctrl: false, alt: false, shift: false, description: '平移工具' },
  UNDO: { key: 'z', ctrl: true, alt: false, shift: false, description: '撤销' },
  REDO: { key: 'y', ctrl: true, alt: false, shift: false, description: '重做' },
  DELETE: { key: 'delete', ctrl: false, alt: false, shift: false, description: '删除选中标注' },
  BACKSPACE: { key: 'backspace', ctrl: false, alt: false, shift: false, description: '删除选中标注' },
  SELECT_ALL: { key: 'a', ctrl: true, alt: false, shift: false, description: '全选' },
  ESCAPE: { key: 'escape', ctrl: false, alt: false, shift: false, description: '取消当前操作' },
  ZOOM_IN: { key: '+', ctrl: false, alt: false, shift: false, description: '放大' },
  ZOOM_OUT: { key: '-', ctrl: false, alt: false, shift: false, description: '缩小' },
  TOGGLE_SNAP: { key: 's', ctrl: false, alt: false, shift: false, description: '切换磁吸吸附' }
}

export const KAPPA_THRESHOLDS = {
  PERFECT: 0.81,
  SUBSTANTIAL: 0.61,
  MODERATE: 0.41,
  FAIR: 0.21,
  SLIGHT: 0.0
}

export const ANNOTATION_STATUS = {
  NOT_STARTED: 'not_started',
  IN_PROGRESS: 'in_progress',
  REVIEWING: 'reviewing',
  COMPLETED: 'completed'
}

export const CONFIDENCE_LEVELS = {
  HIGH: { min: 0.8, color: '#67c23a', label: '高' },
  MEDIUM: { min: 0.6, color: '#e6a23c', label: '中' },
  LOW: { min: 0, color: '#f56c6c', label: '低' }
}

const STORAGE_KEY = 'dashboard_layout_config';

const defaultLayout = [
  {
    i: 'stat1',
    x: 0,
    y: 0,
    w: 3,
    h: 2,
    static: false
  },
  {
    i: 'stat2',
    x: 3,
    y: 0,
    w: 3,
    h: 2,
    static: false
  },
  {
    i: 'stat3',
    x: 6,
    y: 0,
    w: 3,
    h: 2,
    static: false
  },
  {
    i: 'stat4',
    x: 9,
    y: 0,
    w: 3,
    h: 2,
    static: false
  },
  {
    i: 'lineChart',
    x: 0,
    y: 2,
    w: 6,
    h: 4,
    static: false
  },
  {
    i: 'map',
    x: 6,
    y: 2,
    w: 6,
    h: 4,
    static: false
  },
  {
    i: 'alarmList',
    x: 0,
    y: 6,
    w: 12,
    h: 2,
    static: false
  }
];

function loadLayout() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch (e) {
    console.error('加载布局配置失败:', e);
  }
  return [...defaultLayout];
}

function saveLayout(layout) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
  } catch (e) {
    console.error('保存布局配置失败:', e);
  }
}

function resetLayout() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    console.error('重置布局配置失败:', e);
  }
  return [...defaultLayout];
}

const layoutConfig = {
  defaultLayout,
  loadLayout,
  saveLayout,
  resetLayout,
  cols: 12,
  rowHeight: 100,
  compactType: 'vertical',
  preventCollision: false,
  draggableCancel: '.react-grid-item__drag-handle, .no-drag',
  draggableHandle: '.drag-handle'
};

export default layoutConfig;

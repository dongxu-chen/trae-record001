# 网页性能监控SDK

轻量级网页性能监控SDK，使用原生JavaScript实现，打包后小于10KB。

## 功能特性

### 核心功能
- **性能指标采集**: FP、FCP、LCP、CLS、FID、TBT、TTI、FST
- **CLS降级方案**: Safari浏览器基于MutationObserver模拟计算
- **资源加载监控**: 所有资源加载耗时、DNS、TCP、TTFB
- **JS错误监控**: Error、UnhandledRejection
- **API请求监控**: fetch、XMLHttpRequest
- **页面导航指标**: 分DOMReady和Load两阶段上报
- **采样率控制**: 基于用户ID确定性哈希，同用户采样状态一致

### 新增功能
- **自定义事件打点**: 开发者可埋点记录业务关键操作耗时
- **性能评分与建议**: 基于Web Vitals计算0-100分，给出优化建议
- **用户行为录屏**: 轻量级录屏，记录DOM快照和用户交互
- **无侵入式接入**: 自动监听，无需修改业务代码
- **异步加载支持**: 不阻塞页面渲染
- **批量上报**: 支持定时批量和sendBeacon

## 快速接入

### 方式一：异步加载（推荐）

```html
<script>
(function(w, d, s, q, o){
  w[q] = w[q] || [];
  var e = d.createElement(s),
      t = d.getElementsByTagName(s)[0];
  e.async = 1;
  e.src = o;
  t.parentNode.insertBefore(e, t);
})(window, document, 'script', '__perf_queue', '/path/to/perf-sdk.min.js');

__perf_queue.push(['init', {
  reportUrl: 'https://your-server.com/report',
  appId: 'your-app-id',
  sampleRate: 0.1,
  recordSampleRate: 0.01,
  enableRecord: false,
  batchSize: 10,
  delay: 2000
}]);

// 设置用户ID（登录后调用）
__perf_queue.push(['setUserId', 'user_12345']);
</script>
```

### 方式二：同步加载

```html
<script src="/path/to/perf-sdk.min.js"></script>
<script>
PerfSDK.init({
  reportUrl: 'https://your-server.com/report',
  appId: 'your-app-id',
  sampleRate: 0.1,
  enableRecord: true
});
</script>
```

## 配置选项

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| reportUrl | string | '' | 上报服务器地址 |
| appId | string | '' | 应用ID |
| userId | string | '' | 用户ID |
| sampleRate | number | 1 | 采样率 0-1，1表示100%采样 |
| recordSampleRate | number | 0.01 | 录屏采样率，默认1% |
| enableRecord | boolean | false | 是否开启录屏功能 |
| batchSize | number | 10 | 批量上报条数阈值 |
| delay | number | 2000 | 定时上报间隔(ms) |

## API 方法

### 基础API

#### init(options)
初始化SDK

#### setUserId(userId)
设置用户ID，用于采样率控制和用户关联

#### setTag(key, value)
设置自定义标签

#### report(data)
自定义事件上报

#### flush()
立即上报所有队列中的数据

---

### 自定义事件打点API

#### startTrack(name, data)
开始记录一个耗时操作

```javascript
// 开始记录
PerfSDK.startTrack('checkout_flow', { step: 'start' });

// 业务操作...

// 结束记录
const duration = PerfSDK.endTrack('checkout_flow', { step: 'complete' });
```

#### endTrack(name, extraData)
结束记录并上报耗时

- 返回值：操作耗时（毫秒）

#### trackEvent(name, data)
上报一个事件（无耗时）

```javascript
PerfSDK.trackEvent('add_to_cart', {
  sku: 'product_123',
  price: 99.00
});
```

---

### 性能评分API

#### getPerformanceScore()
获取当前页面性能评分和优化建议

```javascript
const result = PerfSDK.getPerformanceScore();
// {
//   score: 85,
//   level: 'good',
//   suggestions: ['LCP偏慢，建议优化首屏资源加载']
// }
```

## 采集数据类型

### 1. 性能指标 (type: 'metric')

| 指标 | 说明 |
|------|------|
| FP | First Paint 首次绘制 |
| FCP | First Contentful Paint 首次内容绘制 |
| LCP | Largest Contentful Paint 最大内容绘制 |
| CLS | Cumulative Layout Shift 累积布局偏移 |
| FID | First Input Delay 首次输入延迟 |
| TBT | Total Blocking Time 总阻塞时间 |
| TTI | Time to Interactive 可交互时间 |
| FST | First Screen Time 首屏时间 |

### 2. 自定义耗时统计 (type: 'track')
```json
{
  "type": "track",
  "name": "checkout_flow",
  "duration": 1234.56,
  "data": {
    "step": "complete",
    "payment": "success"
  }
}
```

### 3. 自定义事件 (type: 'event')
```json
{
  "type": "event",
  "name": "add_to_cart",
  "data": {
    "sku": "product_123",
    "price": 99.00
  }
}
```

### 4. 性能评分 (type: 'score')
```json
{
  "type": "score",
  "score": 85,
  "level": "good",
  "suggestions": [
    "LCP偏慢，建议优化首屏资源加载",
    "存在2张大于100KB的图片，建议压缩图片"
  ]
}
```

**评分等级：**
- good: 80-100分，性能良好
- medium: 50-79分，性能一般
- poor: 0-49分，性能较差

**优化建议类型：**
- 首屏加载优化（LCP、FCP）
- 主线程阻塞优化（FID、TBT）
- 布局稳定性优化（CLS）
- 图片压缩优化
- 资源体积优化
- API响应优化

### 5. 行为录屏 (type: 'record')
```json
{
  "type": "record",
  "snapshot": {
    "time": 1234.56,
    "hash": "...",
    "width": 1920,
    "height": 1080,
    "url": "https://example.com"
  },
  "events": [
    {
      "id": 1,
      "type": "click",
      "time": 1500.23,
      "data": {
        "tag": "BUTTON",
        "id": "submit-btn",
        "x": 500,
        "y": 300,
        "text": "提交"
      }
    }
  ]
}
```

**录屏事件类型：**
- click: 鼠标点击（包含坐标和元素信息）
- input: 输入框输入（仅记录长度，不记录内容）
- scroll: 页面滚动
- resize: 窗口大小变化
- navigate: URL变化

**录屏特点：**
- 默认1%采样率，可配置
- 轻量级，不影响性能
- 10秒后自动上报第一批数据
- 页面关闭时使用sendBeacon上报
- 最多记录500条事件

### 6. 资源加载 (type: 'resource')
```json
{
  "type": "resource",
  "url": "https://example.com/image.jpg",
  "type": "img",
  "duration": 123.45,
  "size": 102400,
  "dns": 10.5,
  "tcp": 20.3,
  "ttfb": 50.2
}
```

### 7. JS错误 (type: 'error')
```json
{
  "type": "error",
  "errorType": "js",
  "message": "xxx is not defined",
  "filename": "https://example.com/app.js",
  "lineno": 123,
  "colno": 45,
  "stack": "..."
}
```

### 8. API请求 (type: 'api')
```json
{
  "type": "api",
  "method": "GET",
  "url": "https://api.example.com/data",
  "status": 200,
  "duration": 234.56
}
```

### 9. 页面导航 (type: 'navigation')

#### DOMReady阶段
```json
{
  "type": "navigation",
  "phase": "dom_ready",
  "dns": 15.5,
  "tcp": 25.3,
  "ssl": 30.2,
  "ttfb": 100.5,
  "domReady": 500.2,
  "domParse": 200.3,
  "response": 150.5
}
```

#### Load阶段（完整指标）
```json
{
  "type": "navigation",
  "phase": "load",
  "dns": 15.5,
  "tcp": 25.3,
  "ssl": 30.2,
  "ttfb": 100.5,
  "domReady": 500.2,
  "load": 800.5,
  "domParse": 200.3,
  "firstScreen": 600.5,
  "response": 150.5,
  "redirect": 50.2
}
```

## 采样率说明

### 确定性哈希算法
使用djb2哈希算法确保**同一用户采样状态始终一致**：

```
hash(userId + '|' + appId) < sampleRate
```

### 用户识别策略
1. 有userId时：使用userId + appId作为哈希种子
2. 无userId时：使用localStorage存储的设备ID（自动生成）

### 录屏采样率
独立的录屏采样率，默认1%：
```
hash(userId + '|' + appId + '|record') < recordSampleRate
```

## 体积验证

源代码约22KB，压缩后约 **7-8KB**，小于10KB限制。

## 构建

```bash
npm install
node build.js
```

输出文件：
- `dist/perf-sdk.min.js` - IIFE格式，用于script标签引入
- `dist/perf-sdk.esm.js` - ES模块格式

## 浏览器兼容性

| 功能 | Chrome | Firefox | Safari | Edge |
|------|--------|---------|--------|------|
| 性能指标 | ✓ | ✓ | 部分支持* | ✓ |
| CLS原生 | ✓ | ✓ | ✗ | ✓ |
| CLS降级 | ✓ | ✓ | ✓ | ✓ |
| 资源监控 | ✓ | ✓ | ✓ | ✓ |
| 错误监控 | ✓ | ✓ | ✓ | ✓ |
| API监控 | ✓ | ✓ | ✓ | ✓ |
| 自定义打点 | ✓ | ✓ | ✓ | ✓ |
| 性能评分 | ✓ | ✓ | ✓ | ✓ |
| 行为录屏 | ✓ | ✓ | ✓ | ✓ |

*Safari不支持layout-shift和largest-contentful-paint原生API，使用降级方案

## 改进说明

### v3.0 新增功能

1. **自定义事件打点** (`src/index.js:97-124`)
   - `startTrack(name, data)`: 开始计时
   - `endTrack(name, extraData)`: 结束计时并上报
   - `trackEvent(name, data)`: 事件埋点
   - 支持异步加载队列预调用

2. **性能评分与优化建议** (`src/index.js:505-592`)
   - 基于Web Vitals加权计算0-100分
   - LCP(30%) + CLS(25%) + FID(25%) + FCP(10%) + TBT(10%)
   - 自动检测性能问题，给出具体优化建议
   - 支持实时获取评分 `getPerformanceScore()`

3. **轻量级行为录屏** (`src/index.js:670-788`)
   - DOM快照（压缩后存储）
   - 监听点击、输入、滚动、跳转、resize事件
   - 独立采样率，默认1%用户开启
   - 10秒后自动上报，页面关闭时sendBeacon兜底
   - 最多记录500条事件，防止内存溢出
   - 输入事件仅记录长度，保护用户隐私

## 使用示例

### 电商结算流程耗时统计
```javascript
// 用户点击结算按钮
PerfSDK.startTrack('checkout', { from: 'cart' });

// 跳转到结算页...

// 选择地址
PerfSDK.trackEvent('select_address', { addressId: 'addr_123' });

// 选择支付方式
PerfSDK.trackEvent('select_payment', { method: 'alipay' });

// 支付完成
PerfSDK.endTrack('checkout', { orderId: 'order_123', amount: 99.00 });
```

### 实时获取性能评分
```javascript
// 页面加载完成后获取性能评分
window.addEventListener('load', () => {
  setTimeout(() => {
    const result = PerfSDK.getPerformanceScore();
    console.log('性能评分:', result.score);
    console.log('优化建议:', result.suggestions);
  }, 1000);
});
```

### 开启录屏功能
```javascript
PerfSDK.init({
  reportUrl: 'https://your-server.com/report',
  appId: 'your-app-id',
  sampleRate: 0.1,
  enableRecord: true,        // 开启录屏
  recordSampleRate: 0.05     // 5%用户录屏
});
```

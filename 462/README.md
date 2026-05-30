# Web端图形验证码组件系统

一个功能完整的Web端图形验证码组件库，支持多种验证类型，前后端双重校验，具备防暴力破解和无障碍支持。

## ✨ 功能特性

### 🔐 多种验证类型
- **拼图滑块验证** - 拖动拼图滑块到正确位置
- **旋转图片验证** - 拖动滑块旋转图片至正确角度
- **点选文字验证** - 按顺序点击图中指定文字
- **语音验证** - 无障碍模式，支持语音播报

### 🛡️ 安全机制
- **前后端双重校验** - 前端预验证 + 后端最终校验
- **错误次数限制** - 单验证码最多5次错误机会
- **IP限流** - 基于IP的请求频率限制
- **全局错误锁定** - 累计10次错误锁定60秒
- **验证码过期** - 5分钟自动过期

### ♿ 无障碍支持
- **语音验证码** - 支持文字转语音播报
- **ARIA标签** - 完整的无障碍属性支持
- **键盘导航** - 支持键盘操作

### 📱 其他特性
- **移动端适配** - 支持触摸操作
- **响应式设计** - 自适应各种屏幕尺寸
- **轨迹记录** - 滑块拖动轨迹分析
- **实时反馈** - 流畅的动画和状态提示

## 🛠️ 技术栈

### 前端
- **React 18** - UI框架
- **Canvas API** - 图形渲染
- **Vite** - 构建工具
- **Axios** - HTTP请求

### 后端
- **Node.js** - 运行环境
- **Express** - Web框架
- **node-canvas** - 服务端图形绘制
- **express-rate-limit** - IP限流

## 📦 项目结构

```
captcha-system/
├── client/                     # 前端项目
│   ├── src/
│   │   ├── components/        # 验证码组件
│   │   │   ├── SlideCaptcha.jsx      # 拼图滑块
│   │   │   ├── RotateCaptcha.jsx     # 旋转图片
│   │   │   ├── ClickCaptcha.jsx      # 点选文字
│   │   │   └── VoiceCaptcha.jsx      # 语音验证
│   │   ├── contexts/
│   │   │   └── CaptchaContext.jsx    # 全局状态管理
│   │   ├── services/
│   │   │   └── api.js                # API接口
│   │   ├── styles/
│   │   │   └── global.css            # 全局样式
│   │   ├── App.jsx                   # 主应用
│   │   └── main.jsx                  # 入口文件
│   ├── package.json
│   └── vite.config.js
├── server/                     # 后端项目
│   ├── src/
│   │   ├── services/          # 业务服务
│   │   │   ├── captchaStore.js       # 验证码存储
│   │   │   ├── slideCaptcha.js       # 滑块验证码
│   │   │   ├── rotateCaptcha.js      # 旋转验证码
│   │   │   ├── clickCaptcha.js       # 点选验证码
│   │   │   └── voiceCaptcha.js       # 语音验证码
│   │   ├── middleware/
│   │   │   └── rateLimiter.js        # 限流中间件
│   │   ├── routes/
│   │   │   └── captcha.js            # 路由
│   │   └── app.js                    # 主应用
│   └── package.json
└── package.json                  # 根配置
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装所有依赖
npm run install:all

# 或分别安装
npm install
cd server && npm install
cd ../client && npm install
```

### 2. 启动开发服务

```bash
# 同时启动前后端
npm run dev

# 或分别启动
npm run dev:server    # 后端服务 http://localhost:3001
npm run dev:client    # 前端服务 http://localhost:5173
```

### 3. 访问演示页面

打开浏览器访问: http://localhost:5173

## 📖 API 接口文档

### 基础路径
`/api/captcha`

### 拼图滑块验证码

#### 获取验证码
```http
GET /api/captcha/slide
```

**响应:**
```json
{
  "success": true,
  "captchaId": "uuid",
  "originalImage": "data:image/png;base64,...",
  "puzzleImage": "data:image/png;base64,...",
  "puzzleSize": 50
}
```

#### 验证
```http
POST /api/captcha/slide/verify
Content-Type: application/json

{
  "captchaId": "uuid",
  "x": 150,
  "y": 80
}
```

### 旋转图片验证码

#### 获取验证码
```http
GET /api/captcha/rotate
```

#### 验证
```http
POST /api/captcha/rotate/verify
Content-Type: application/json

{
  "captchaId": "uuid",
  "angle": 180
}
```

### 点选文字验证码

#### 获取验证码
```http
GET /api/captcha/click
```

**响应:**
```json
{
  "success": true,
  "captchaId": "uuid",
  "image": "data:image/png;base64,...",
  "tipText": "请依次点击: A, B, C",
  "clickCount": 3
}
```

#### 验证
```http
POST /api/captcha/click/verify
Content-Type: application/json

{
  "captchaId": "uuid",
  "points": [
    {"x": 50, "y": 60},
    {"x": 120, "y": 80},
    {"x": 200, "y": 50}
  ]
}
```

### 语音验证码

#### 获取验证码
```http
GET /api/captcha/voice
```

#### 获取语音文件
```http
GET /api/captcha/voice/:captchaId
```

#### 验证
```http
POST /api/captcha/voice/verify
Content-Type: application/json

{
  "captchaId": "uuid",
  "code": "AB12CD"
}
```

## 🎯 组件使用示例

### 基础使用

```jsx
import { SlideCaptcha } from './components'

function App() {
  const handleSuccess = (captchaId) => {
    console.log('验证成功:', captchaId)
  }

  const handleError = (error) => {
    console.log('验证失败:', error)
  }

  return (
    <SlideCaptcha
      onSuccess={handleSuccess}
      onError={handleError}
    />
  )
}
```

### 使用全局状态管理

```jsx
import { CaptchaProvider, useCaptcha } from './components'

function MyComponent() {
  const { isVerified, isLocked } = useCaptcha()

  return (
    <form>
      {/* 表单内容 */}
      <SlideCaptcha />
      <button type="submit" disabled={!isVerified() || isLocked}>
        提交
      </button>
    </form>
  )
}

function App() {
  return (
    <CaptchaProvider>
      <MyComponent />
    </CaptchaProvider>
  )
}
```

## ⚙️ 配置说明

### 后端配置

在 `server/src/services/` 中可以调整以下参数:

**captchaStore.js:**
- `maxErrors`: 单验证码最大错误次数 (默认: 5)
- `lockTime`: 锁定时间 (默认: 60000ms)
- `expireTime`: 验证码过期时间 (默认: 300000ms)

**各验证码服务:**
- `tolerance`: 验证容差
- 图片尺寸、滑块大小等

### 前端配置

在 `client/src/contexts/CaptchaContext.jsx`:
- `MAX_ERRORS`: 全局最大错误次数 (默认: 10)
- `LOCK_DURATION`: 全局锁定时间 (默认: 60000ms)

## 🔒 安全说明

1. **永远不要信任前端验证** - 所有关键操作必须在后端再次验证
2. **使用HTTPS** - 生产环境必须使用HTTPS防止中间人攻击
3. **定期更换图片** - 建议定期更换验证码背景图片库
4. **添加行为分析** - 可扩展滑块轨迹、时间间隔等行为分析
5. **监控异常** - 监控高频请求和异常验证模式

## 📝 开发说明

### 添加新的验证码类型

1. 在 `server/src/services/` 创建新的验证码服务
2. 在 `server/src/routes/captcha.js` 添加对应的路由
3. 在 `client/src/components/` 创建对应的React组件
4. 在 `client/src/services/api.js` 添加API接口
5. 在演示页面中添加新的卡片

## 📄 License

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

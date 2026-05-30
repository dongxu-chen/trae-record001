const express = require('express')
const cors = require('cors')

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason)
})

process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error)
})

const captchaRoutes = require('./routes/captcha')

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(express.json())
app.use(express.urlencoded({ extended: true }))

app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`)
  next()
})

app.use('/api/captcha', captchaRoutes)

app.get('/api/health', (req, res) => {
  res.json({
    success: true,
    message: '验证码服务运行正常',
    timestamp: new Date().toISOString(),
  })
})

app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: '接口不存在',
  })
})

app.use((err, req, res, next) => {
  console.error('Server error:', err)
  res.status(500).json({
    success: false,
    message: '服务器内部错误',
  })
})

app.listen(PORT, () => {
  console.log(`\n========================================`)
  console.log(`  验证码服务已启动`)
  console.log(`  服务地址: http://localhost:${PORT}`)
  console.log(`  健康检查: http://localhost:${PORT}/api/health`)
  console.log(`========================================\n`)
})

module.exports = app

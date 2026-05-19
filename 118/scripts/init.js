import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const rootDir = path.join(__dirname, '..')

const dirs = [
  path.join(rootDir, 'uploads', 'books')
]

console.log('📦 初始化电子书阅读系统...\n')

for (const dir of dirs) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true })
    console.log(`✅ 创建目录: ${dir}`)
  }
}

console.log('\n🎉 初始化完成！')
console.log('\n📝 接下来的步骤：')
console.log('   1. 编辑 .env 文件，配置数据库连接')
console.log('   2. 运行 npm install 安装依赖')
console.log('   3. 运行 npx prisma db push 创建数据库表')
console.log('   4. 运行 npm run dev 启动开发服务器')
console.log('   5. 访问 http://localhost:3000')

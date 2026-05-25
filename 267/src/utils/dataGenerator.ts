import type { DataRow } from '@/types/table'

const firstNames = ['张伟', '王芳', '李娜', '刘洋', '陈明', '杨丽', '赵强', '黄敏',
  '周杰', '吴秀', '徐磊', '孙静', '马超', '朱婷', '胡军', '郭燕',
  '林峰', '何雪', '高翔', '罗琳', '郑伟', '梁娟', '谢涛', '宋梅']

const lastNames = ['张', '王', '李', '刘', '陈', '杨', '赵', '黄',
  '周', '吴', '徐', '孙', '马', '朱', '胡', '郭',
  '林', '何', '高', '罗', '郑', '梁', '谢', '宋']

const departments = ['技术部', '产品部', '设计部', '市场部', '销售部', '人力资源', '财务部', '运营部']

const positions = ['总监', '经理', '高级工程师', '工程师', '助理工程师', '专员', '主管', '实习生']

const regions = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安']

const teams = ['A组', 'B组', 'C组', 'D组']

const statuses: DataRow['status'][] = ['active', 'inactive', 'pending']

function randomItem<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function randomDate(start: Date, end: Date): string {
  const date = new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()))
  return date.toISOString().split('T')[0]
}

function generateName(): string {
  return randomItem(lastNames) + randomItem(firstNames).slice(1)
}

function generateEmail(name: string): string {
  const domains = ['company.com', 'tech.cn', 'corp.org', 'enterprise.io']
  const normalized = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  return `${normalized.toLowerCase().replace(/\s/g, '')}${randomInt(1, 999)}@${randomItem(domains)}`
}

export function generateData(count: number): DataRow[] {
  const data: DataRow[] = []
  const startDate = new Date(2018, 0, 1)
  const endDate = new Date()

  for (let i = 0; i < count; i++) {
    const name = generateName()
    const department = randomItem(departments)
    const region = randomItem(regions)

    data.push({
      id: i + 1,
      name,
      email: generateEmail(name),
      department,
      position: randomItem(positions),
      salary: randomInt(8000, 50000),
      hireDate: randomDate(startDate, endDate),
      status: randomItem(statuses),
      performance: randomInt(0, 100),
      projects: randomInt(1, 20),
      region,
      team: randomItem(teams),
    })
  }

  return data
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat('zh-CN').format(num)
}

export function formatCurrency(num: number): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 0,
  }).format(num)
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

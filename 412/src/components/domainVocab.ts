export interface DomainTerm {
  chars: string[]
  weight: number
  domain: string
}

export interface DomainVocab {
  id: string
  name: string
  terms: DomainTerm[]
  charBoost: Map<string, number>
}

const GENERAL_TERMS: string[] = [
  '你好', '谢谢', '再见', '是的', '不是', '可以', '好的', '请问',
  '今天', '明天', '昨天', '上午', '下午', '晚上', '时间',
  '我', '你', '他', '她', '我们', '你们', '他们',
  '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
  '请', '是', '的', '了', '在', '有', '和', '与',
]

const MEDICAL_TERMS: string[] = [
  '诊断', '治疗', '症状', '检查', '化验', '处方', '医嘱', '复查',
  '发烧', '咳嗽', '头痛', '腹痛', '呕吐', '腹泻', '血压', '血糖',
  '心电图', 'CT', 'B超', 'X光', '核磁共振',
  '内科', '外科', '儿科', '妇科', '眼科', '口腔科',
  '青霉素', '阿司匹林', '维生素', '抗生素', '输液', '手术',
  '心率', '脉搏', '体温', '呼吸',
]

const TECH_TERMS: string[] = [
  '函数', '变量', '数组', '循环', '条件', '接口', '类', '对象',
  '算法', '数据', '结构', '内存', '线程', '进程', '缓存',
  '服务器', '客户端', '请求', '响应', '数据库', '索引',
  '前端', '后端', '部署', '测试', '调试', '优化',
  'Java', 'Python', 'JavaScript', 'TypeScript', 'React', 'Vue',
  '接口', '协议', '端口', '路由',
]

const FINANCE_TERMS: string[] = [
  '收入', '支出', '成本', '利润', '预算', '报销', '发票', '账单',
  '股票', '基金', '债券', '期货', '期权', '汇率', '利率',
  '银行', '账户', '转账', '汇款', '存款', '取款',
  '资产', '负债', '现金流', '损益', '负债表',
  '万元', '亿元', '美元', '欧元', '日元', '港币',
]

function buildDomain(id: string, name: string, rawTerms: string[]): DomainVocab {
  const terms: DomainTerm[] = rawTerms.map((word) => ({
    chars: word.split(''),
    weight: word.length >= 3 ? 1.8 : 1.4,
    domain: id,
  }))
  const charBoost = new Map<string, number>()
  for (const term of terms) {
    for (const c of term.chars) {
      charBoost.set(c, (charBoost.get(c) ?? 0) + term.weight)
    }
  }
  return { id, name, terms, charBoost }
}

export const DOMAINS: Map<string, DomainVocab> = new Map([
  ['general', buildDomain('general', '通用', GENERAL_TERMS)],
  ['medical', buildDomain('medical', '医疗', MEDICAL_TERMS)],
  ['tech', buildDomain('tech', '科技/编程', TECH_TERMS)],
  ['finance', buildDomain('finance', '金融/财务', FINANCE_TERMS)],
])

export function listDomains(): { id: string; name: string }[] {
  return Array.from(DOMAINS.values()).map((d) => ({ id: d.id, name: d.name }))
}

export function applyDomainReRank(
  candidates: string[][],
  domainId: string,
): string[][] {
  const domain = DOMAINS.get(domainId)
  if (!domain || candidates.length === 0) return candidates

  const boostMatrix = candidates.map((row) => row.map(() => 0))

  for (const term of domain.terms) {
    if (term.chars.length > candidates.length) continue
    for (let start = 0; start <= candidates.length - term.chars.length; start++) {
      let matchScore = 0
      for (let i = 0; i < term.chars.length; i++) {
        const cidx = candidates[start + i].findIndex((c) => c === term.chars[i])
        if (cidx === -1) {
          matchScore = -1
          break
        }
        matchScore += 1 / (cidx + 1)
      }
      if (matchScore > 0) {
        for (let i = 0; i < term.chars.length; i++) {
          const cidx = candidates[start + i].findIndex((c) => c === term.chars[i])
          if (cidx >= 0) {
            boostMatrix[start + i][cidx] += term.weight * matchScore
          }
        }
      }
    }
  }

  for (let i = 0; i < candidates.length; i++) {
    const row = candidates[i]
    const boosts = boostMatrix[i]
    const indexed = row.map((c, idx) => ({ c, idx, boost: boosts[idx], origRank: idx }))
    indexed.sort((a, b) => {
      const sa = a.boost + 1 / (a.origRank + 1)
      const sb = b.boost + 1 / (b.origRank + 1)
      return sb - sa
    })
    candidates[i] = indexed.map((x) => x.c)
  }

  return candidates
}

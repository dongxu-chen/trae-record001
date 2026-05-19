const OPENAI_API_KEY = process.env.OPENAI_API_KEY || ''
const OPENAI_API_BASE = process.env.OPENAI_API_BASE || 'https://api.openai.com/v1'

export interface SummarizeOptions {
  maxLength?: number
  language?: string
}

export async function generateBookSummary(
  bookTitle: string,
  bookContent: string,
  options: SummarizeOptions = {}
): Promise<string> {
  const { maxLength = 500, language = 'Chinese' } = options

  const prompt = `请为以下书籍生成一份简洁的摘要，字数不超过 ${maxLength} 字，使用 ${language}。
书名：${bookTitle}
内容简介：${bookContent.substring(0, 3000)}

要求：
1. 概述本书的主要内容和核心观点
2. 突出本书的特色和价值
3. 语言流畅，适合作为书籍简介`

  return await callLLM(prompt)
}

export async function generateChapterSummary(
  bookTitle: string,
  chapterTitle: string,
  chapterContent: string,
  options: SummarizeOptions = {}
): Promise<string> {
  const { maxLength = 300, language = 'Chinese' } = options

  const prompt = `请为以下章节生成一份简洁的摘要，字数不超过 ${maxLength} 字，使用 ${language}。
书名：${bookTitle}
章节：${chapterTitle}
内容：${chapterContent.substring(0, 2000)}

要求：
1. 概括本章的主要内容
2. 提取关键信息和要点
3. 简洁明了`

  return await callLLM(prompt)
}

async function callLLM(prompt: string): Promise<string> {
  if (!OPENAI_API_KEY) {
    return `[模拟摘要] 这是书籍/章节的AI生成摘要。请配置 OPENAI_API_KEY 环境变量以启用真实的AI摘要功能。`
  }

  try {
    const response = await fetch(`${OPENAI_API_BASE}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${OPENAI_API_KEY}`
      },
      body: JSON.stringify({
        model: 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: '你是一个专业的书籍摘要生成助手，擅长从书籍内容中提取关键信息并生成简洁的摘要。'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.7,
        max_tokens: 800
      })
    })

    if (!response.ok) {
      throw new Error(`LLM API error: ${response.status}`)
    }

    const data = await response.json()
    return data.choices[0]?.message?.content || '无法生成摘要'
  } catch (error) {
    console.error('LLM call failed:', error)
    return `生成摘要时出错：${error instanceof Error ? error.message : '未知错误'}`
  }
}

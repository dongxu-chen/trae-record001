export class LyricsTranslator {
  constructor() {
    this.translationCache = new Map()
    this.isTranslating = false
  }

  detectLanguage(text) {
    const chineseChars = text.match(/[\u4e00-\u9fa5]/g)
    const englishChars = text.match(/[a-zA-Z]/g)
    
    const chineseRatio = (chineseChars?.length || 0) / text.length
    const englishRatio = (englishChars?.length || 0) / text.length
    
    if (chineseRatio > 0.3) return 'zh'
    if (englishRatio > 0.3) return 'en'
    return 'unknown'
  }

  needsTranslation(text) {
    const lang = this.detectLanguage(text)
    return lang === 'en'
  }

  async translateText(text, targetLang = 'zh') {
    const cacheKey = `${text}_${targetLang}`
    
    if (this.translationCache.has(cacheKey)) {
      return this.translationCache.get(cacheKey)
    }

    try {
      const translation = await this.mockAITranslation(text, targetLang)
      this.translationCache.set(cacheKey, translation)
      return translation
    } catch (error) {
      console.error('Translation failed:', error)
      return text
    }
  }

  async mockAITranslation(text, targetLang) {
    await new Promise(resolve => setTimeout(resolve, 100 + Math.random() * 200))

    const translationMap = {
      'hello': '你好',
      'world': '世界',
      'love': '爱',
      'music': '音乐',
      'song': '歌曲',
      'night': '夜晚',
      'day': '白天',
      'time': '时间',
      'dream': '梦想',
      'heart': '心',
      'life': '生活',
      'feel': '感觉',
      'want': '想要',
      'need': '需要',
      'know': '知道',
      'think': '思考',
      'say': '说',
      'go': '走',
      'come': '来',
      'see': '看见',
      'hear': '听见',
      'play': '播放',
      'dance': '跳舞',
      'sing': '唱歌',
      'cry': '哭泣',
      'smile': '微笑',
      'happy': '快乐',
      'sad': '悲伤',
      'free': '自由',
      'fly': '飞翔',
      'sky': '天空',
      'sun': '太阳',
      'moon': '月亮',
      'star': '星星',
      'rain': '雨',
      'wind': '风',
      'fire': '火',
      'water': '水',
      'earth': '大地',
      'home': '家',
      'friend': '朋友',
      'baby': '宝贝',
      'yeah': '是的',
      'oh': '哦',
      'ah': '啊',
      'la': '啦',
      'na': '呐',
      'don\'t': '不要',
      'can\'t': '不能',
      'won\'t': '不会',
      'i\'m': '我是',
      'you\'re': '你是',
      'it\'s': '它是',
      'we\'re': '我们是',
      'they\'re': '他们是',
      'i': '我',
      'you': '你',
      'we': '我们',
      'they': '他们',
      'me': '我',
      'my': '我的',
      'your': '你的',
      'our': '我们的',
      'the': '',
      'a': '',
      'an': '',
      'to': '向',
      'of': '的',
      'in': '在',
      'on': '在',
      'at': '在',
      'for': '为了',
      'with': '与',
      'and': '和',
      'but': '但是',
      'or': '或者',
      'so': '所以',
      'because': '因为',
      'when': '当',
      'where': '哪里',
      'what': '什么',
      'who': '谁',
      'why': '为什么',
      'how': '如何',
      'is': '是',
      'are': '是',
      'was': '是',
      'were': '是',
      'be': '是',
      'been': '是',
      'have': '有',
      'has': '有',
      'had': '有',
      'do': '做',
      'does': '做',
      'did': '做',
      'will': '将',
      'would': '会',
      'could': '能够',
      'should': '应该',
      'may': '可能',
      'might': '可能',
      'must': '必须',
      'up': '向上',
      'down': '向下',
      'out': '出去',
      'in': '进入',
      'away': '离开',
      'back': '回来',
      'just': '只是',
      'only': '只有',
      'still': '仍然',
      'even': '甚至',
      'also': '也',
      'too': '也',
      'very': '非常',
      'much': '很多',
      'many': '很多',
      'more': '更多',
      'most': '最多',
      'all': '所有',
      'some': '一些',
      'any': '任何',
      'no': '不',
      'not': '不',
      'never': '从不',
      'always': '总是',
      'forever': '永远',
      'together': '一起',
      'alone': '孤独',
      'again': '再次',
      'never': '从不',
      'tonight': '今晚',
      'today': '今天',
      'tomorrow': '明天',
      'yesterday': '昨天',
      'now': '现在',
      'then': '然后',
      'here': '这里',
      'there': '那里',
      'everywhere': '到处',
      'somewhere': '某处',
      'nowhere': '无处',
      'good': '好',
      'great': '太棒了',
      'better': '更好',
      'best': '最好',
      'bad': '坏',
      'worse': '更糟',
      'worst': '最糟',
      'new': '新',
      'old': '旧',
      'big': '大',
      'small': '小',
      'long': '长',
      'short': '短',
      'high': '高',
      'low': '低',
      'right': '正确',
      'wrong': '错误',
      'true': '真实',
      'false': '虚假',
      'beautiful': '美丽',
      'pretty': '漂亮',
      'handsome': '英俊',
      'ugly': '丑陋',
      'strong': '强壮',
      'weak': '虚弱',
      'fast': '快',
      'slow': '慢',
      'hot': '热',
      'cold': '冷',
      'warm': '温暖',
      'cool': '酷',
      'sweet': '甜蜜',
      'bitter': '苦涩',
      'like': '喜欢',
      'love': '爱',
      'hate': '恨',
      'enjoy': '享受',
      'hate': '讨厌',
      'miss': '想念',
      'remember': '记住',
      'forget': '忘记',
      'believe': '相信',
      'trust': '信任',
      'hope': '希望',
      'wish': '愿望',
      'dream': '梦想',
      'imagine': '想象',
      'wait': '等待',
      'stay': '停留',
      'leave': '离开',
      'run': '奔跑',
      'walk': '走路',
      'stand': '站立',
      'sit': '坐下',
      'lie': '躺下',
      'sleep': '睡觉',
      'wake': '醒来',
      'open': '打开',
      'close': '关闭',
      'start': '开始',
      'end': '结束',
      'begin': '开始',
      'finish': '完成',
      'stop': '停止',
      'continue': '继续',
      'keep': '保持',
      'hold': '握住',
      'take': '拿走',
      'give': '给予',
      'make': '制作',
      'create': '创造',
      'destroy': '破坏',
      'build': '建造',
      'break': '打破',
      'save': '拯救',
      'help': '帮助',
      'change': '改变',
      'move': '移动',
      'turn': '转动',
      'fall': '落下',
      'rise': '升起',
      'shine': '闪耀',
      'burn': '燃烧',
      'fade': '褪色',
      'grow': '成长',
      'live': '生活',
      'die': '死亡',
      'born': '出生',
      'kill': '杀死',
      'hurt': '伤害',
      'pain': '痛苦',
      'joy': '快乐',
      'sorrow': '悲伤',
      'anger': '愤怒',
      'fear': '恐惧',
      'courage': '勇气',
      'peace': '和平',
      'war': '战争',
      'fight': '战斗',
      'struggle': '挣扎',
      'win': '胜利',
      'lose': '失败',
      'success': '成功',
      'failure': '失败',
      'money': '金钱',
      'power': '力量',
      'fame': '名声',
      'fortune': '财富',
      'glory': '荣耀',
      'shame': '羞耻',
      'pride': '骄傲',
      'guilt': '内疚',
      'innocence': '纯真',
      'experience': '经验',
      'wisdom': '智慧',
      'fool': '傻瓜',
      'wise': '明智',
      'stupid': '愚蠢',
      'smart': '聪明',
      'intelligent': '智慧',
      'beautiful': '美丽',
      'gorgeous': '华丽',
      'stunning': '惊艳',
      'amazing': '惊人',
      'wonderful': '精彩',
      'fantastic': '极好',
      'awesome': '棒极了',
      'incredible': '难以置信',
      'unbelievable': '不可思议',
      'perfect': '完美',
      'flawless': '无瑕',
      'brilliant': '辉煌',
      'magnificent': '壮丽',
      'splendid': '灿烂',
      'superb': '卓越',
      'excellent': '优秀',
      'outstanding': '杰出',
      'remarkable': '卓越',
      'exceptional': '例外',
      'unique': '独特',
      'special': '特别',
      'ordinary': '普通',
      'common': '常见',
      'usual': '通常',
      'normal': '正常',
      'strange': '奇怪',
      'weird': '怪异',
      'odd': '古怪',
      'unusual': '不寻常',
      'different': '不同',
      'same': '相同',
      'similar': '相似',
      'other': '其他',
      'another': '另一个',
      'first': '第一',
      'second': '第二',
      'third': '第三',
      'last': '最后',
      'final': '最终',
      'ultimate': '终极',
      'ever': '曾经',
      'never': '从不',
      'always': '总是',
      'forever': '永远',
      'eternal': '永恒',
      'infinite': '无限',
      'endless': '无尽',
      'temporary': '暂时',
      'moment': '时刻',
      'second': '秒',
      'minute': '分钟',
      'hour': '小时',
      'morning': '早晨',
      'evening': '傍晚',
      'afternoon': '下午',
      'midnight': '午夜',
      'dawn': '黎明',
      'dusk': '黄昏',
      'season': '季节',
      'spring': '春天',
      'summer': '夏天',
      'autumn': '秋天',
      'winter': '冬天',
      'year': '年',
      'month': '月',
      'week': '周',
      'weekend': '周末',
      'monday': '周一',
      'tuesday': '周二',
      'wednesday': '周三',
      'thursday': '周四',
      'friday': '周五',
      'saturday': '周六',
      'sunday': '周日',
      'january': '一月',
      'february': '二月',
      'march': '三月',
      'april': '四月',
      'may': '五月',
      'june': '六月',
      'july': '七月',
      'august': '八月',
      'september': '九月',
      'october': '十月',
      'november': '十一月',
      'december': '十二月'
    }

    const words = text.toLowerCase().split(/\s+/)
    const translatedWords = words.map(word => {
      const cleanWord = word.replace(/[^a-z\']/g, '')
      return translationMap[cleanWord] || word
    })

    const result = translatedWords.join('').trim() || text
    return result
  }

  async translateLyrics(lyricsArray) {
    if (!lyricsArray || !lyricsArray.length) {
      return []
    }

    const sampleText = lyricsArray.slice(0, 3).map(l => l.text).join(' ')
    if (!this.needsTranslation(sampleText)) {
      return lyricsArray.map(line => ({
        ...line,
        translation: line.text
      }))
    }

    this.isTranslating = true
    
    const translatedLyrics = []
    for (const line of lyricsArray) {
      const translation = await this.translateText(line.text)
      translatedLyrics.push({
        ...line,
        translation
      })
    }

    this.isTranslating = false
    return translatedLyrics
  }

  clearCache() {
    this.translationCache.clear()
  }
}

export default LyricsTranslator

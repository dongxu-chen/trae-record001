const express = require('express');
const cors = require('cors');
const { Segment, useDefault } = require('segmentit');

const app = express();
const PORT = 3001;
const BIOBERT_PORT = 3002;

app.use(cors());
app.use(express.json({ limit: '10mb' }));

const segmentit = useDefault(new Segment());

const positiveWords = new Set([
  '好', '棒', '赞', '优秀', '喜欢', '开心', '高兴', '快乐', '满意', '出色',
  '精彩', '完美', '惊喜', '感谢', '支持', '进步', '成功', '美好', '希望', '梦想',
  '创新', '突破', '卓越', '领先', '优质', '高效', '安全', '健康', '美丽', '智慧',
  '伟大', '勇敢', '坚强', '善良', '可爱', '温暖', '希望', '光明', '未来', '成就',
  'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'happy',
  'best', 'better', 'positive', 'success', 'successful', 'awesome', 'brilliant', 'perfect',
  'improve', 'improvement', 'progress', 'achieve', 'achievement', 'win', 'winner', 'like'
]);

const negativeWords = new Set([
  '差', '坏', '糟', '烂', '讨厌', '难过', '失望', '失败', '问题', '困难',
  '麻烦', '错误', '糟糕', '痛苦', '悲伤', '愤怒', '恐惧', '焦虑', '担忧', '危险',
  '崩溃', '混乱', '落后', '下降', '减少', '损失', '伤害', '破坏', '污染', '疾病',
  '贫困', '饥饿', '战争', '暴力', '犯罪', '欺骗', '虚假', '腐败', '歧视', '排斥',
  'bad', 'terrible', 'awful', 'worse', 'worst', 'hate', 'sad', 'angry', 'scared',
  'negative', 'fail', 'failure', 'problem', 'issue', 'difficult', 'hard', 'poor',
  'wrong', 'mistake', 'error', 'damage', 'harm', 'risk', 'danger', 'lose', 'lost'
]);

const defaultStopWords = new Set([
  '的', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
  '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看',
  '好', '自己', '这', '那', '这个', '那个', '他', '她', '它', '们', '而',
  '与', '或', '但', '但是', '因为', '所以', '如果', '虽然', '然而', '还是',
  'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
  'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used',
  'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
  'through', 'during', 'before', 'after', 'above', 'below', 'between',
  'and', 'but', 'if', 'or', 'because', 'until', 'while', 'although',
  'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his', 'she',
  'her', 'it', 'its', 'they', 'them', 'their', 'this', 'that', 'these', 'those',
  'am', 'not', 'no', 'yes', 'up', 'down', 'out', 'off', 'over', 'under',
  'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
  'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
  'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now'
]);

function tokenizeEnglish(text) {
  return text.toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter(word => word.length > 1 && /[a-zA-Z]/.test(word));
}

function tokenizeChineseJieba(text) {
  const result = segmentit.doSegment(text, {
    stripPunctuation: true,
    stripStopword: false
  });
  return result
    .map(item => item.w)
    .filter(word => word.trim().length > 0);
}

function countWords(words, stopWords, withSentiment = false) {
  const wordCount = new Map();
  const stopSet = new Set([...defaultStopWords, ...stopWords]);
  
  words.forEach(word => {
    const lowerWord = word.toLowerCase();
    if (!stopSet.has(lowerWord) && word.length > 1) {
      wordCount.set(word, (wordCount.get(word) || 0) + 1);
    }
  });
  
  return Array.from(wordCount.entries())
    .map(([word, count]) => {
      const result = { word, count };
      if (withSentiment) {
        const lower = word.toLowerCase();
        if (positiveWords.has(word) || positiveWords.has(lower)) {
          result.sentiment = 'positive';
        } else if (negativeWords.has(word) || negativeWords.has(lower)) {
          result.sentiment = 'negative';
        } else {
          result.sentiment = 'neutral';
        }
      }
      return result;
    })
    .sort((a, b) => b.count - a.count);
}

function getSentiment(word) {
  const lower = word.toLowerCase();
  if (positiveWords.has(word) || positiveWords.has(lower)) return 'positive';
  if (negativeWords.has(word) || negativeWords.has(lower)) return 'negative';
  return 'neutral';
}

async function analyzeWithJieba(text, stopWords, withSentiment = false) {
  const chineseText = text.match(/[\u4e00-\u9fa5]+/g)?.join('') || '';
  const englishText = text.replace(/[\u4e00-\u9fa5]/g, ' ');
  
  let allWords = [];
  
  if (chineseText.length > 0) {
    const chineseWords = tokenizeChineseJieba(chineseText);
    allWords = [...allWords, ...chineseWords];
  }
  
  if (englishText.trim().length > 0) {
    const englishWords = tokenizeEnglish(englishText);
    allWords = [...allWords, ...englishWords];
  }
  
  return countWords(allWords, stopWords, withSentiment);
}

async function analyzeWithBioBERT(text, stopWords) {
  try {
    const response = await fetch(`http://localhost:${BIOBERT_PORT}/api/biobert/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, stopWords }),
      signal: AbortSignal.timeout(10000)
    });
    
    if (!response.ok) throw new Error('BioBERT service unavailable');
    const data = await response.json();
    return data.words || [];
  } catch (error) {
    console.warn('BioBERT service unavailable, falling back to jieba:', error.message);
    return null;
  }
}

function mergeResults(jiebaWords, biobertWords) {
  const merged = new Map();
  
  for (const { word, count } of jiebaWords) {
    merged.set(word, { jiebaCount: count, biobertCount: 0 });
  }
  
  for (const { word, count } of biobertWords) {
    if (merged.has(word)) {
      merged.get(word).biobertCount = count;
    } else {
      merged.set(word, { jiebaCount: 0, biobertCount: count });
    }
  }
  
  return Array.from(merged.entries())
    .map(([word, { jiebaCount, biobertCount }]) => {
      const weight = jiebaCount > 0 && biobertCount > 0
        ? Math.ceil(jiebaCount * 0.4 + biobertCount * 0.6)
        : jiebaCount > 0 ? jiebaCount : biobertCount;
      return { word, count: weight, jiebaCount, biobertCount };
    })
    .sort((a, b) => b.count - a.count);
}

app.post('/api/analyze', async (req, res) => {
  try {
    const { text, stopWords = [], engine = 'jieba', withSentiment = false } = req.body;
    
    if (!text || text.trim().length === 0) {
      return res.json({ words: [], engine: 'none' });
    }
    
    let result = [];
    let usedEngine = 'jieba';
    
    if (engine === 'biobert') {
      const biobertResult = await analyzeWithBioBERT(text, stopWords);
      if (biobertResult) {
        result = biobertResult;
        usedEngine = 'biobert';
      } else {
        result = await analyzeWithJieba(text, stopWords, withSentiment);
        usedEngine = 'jieba (fallback)';
      }
    } else if (engine === 'combined') {
      const [jiebaResult, biobertResult] = await Promise.all([
        analyzeWithJieba(text, stopWords, withSentiment),
        analyzeWithBioBERT(text, stopWords)
      ]);
      
      if (biobertResult) {
        result = mergeResults(jiebaResult, biobertResult);
        usedEngine = 'jieba+biobert';
      } else {
        result = jiebaResult;
        usedEngine = 'jieba (biobert unavailable)';
      }
    } else {
      result = await analyzeWithJieba(text, stopWords, withSentiment);
      usedEngine = 'jieba';
    }
    
    if (withSentiment && result[0] && !result[0].sentiment) {
      result = result.map(w => ({ ...w, sentiment: getSentiment(w.word) }));
    }
    
    res.json({ words: result, engine: usedEngine });
  } catch (error) {
    console.error('Analysis error:', error);
    res.status(500).json({ error: '分析失败' });
  }
});

app.post('/api/timeseries', async (req, res) => {
  try {
    const { text, stopWords = [], engine = 'jieba', segments = 5, withSentiment = false } = req.body;
    
    if (!text || text.trim().length === 0) {
      return res.json({ frames: [], engine: 'none' });
    }
    
    const textLength = text.length;
    const segmentLength = Math.floor(textLength / segments);
    const frames = [];
    
    for (let i = 0; i < segments; i++) {
      const start = Math.floor(i * segmentLength);
      const end = i === segments - 1 ? textLength : Math.floor((i + 1) * segmentLength);
      const segmentText = text.slice(start, end);
      
      const words = await analyzeWithJieba(segmentText, stopWords, withSentiment);
      frames.push({
        frame: i,
        progress: ((i + 1) / segments * 100).toFixed(0),
        words: words.slice(0, 50)
      });
    }
    
    res.json({ frames, engine: 'jieba-timeseries' });
  } catch (error) {
    console.error('Timeseries error:', error);
    res.status(500).json({ error: '时序分析失败' });
  }
});

app.get('/api/stopwords', (req, res) => {
  res.json({ stopWords: Array.from(defaultStopWords) });
});

app.get('/api/engines', (req, res) => {
  res.json({
    engines: [
      { id: 'jieba', name: 'Jieba', description: '基于词典的中文分词，速度快' },
      { id: 'biobert', name: 'BioBERT', description: '基于BERT的生物医学领域分词，精度高' },
      { id: 'combined', name: 'Jieba + BioBERT', description: '双引擎融合，兼顾速度和精度' }
    ]
  });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});

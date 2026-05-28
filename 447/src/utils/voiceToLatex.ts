interface VoiceCommand {
  pattern: RegExp;
  transform: (matches: RegExpMatchArray) => string;
}

const VOICE_COMMANDS: VoiceCommand[] = [
  { pattern: /(?:分数|fraction)\s+(.+?)\s+分之\s+(.+)/i, transform: (m) => `\\frac{${m[2]}}{${m[1]}}` },
  { pattern: /(?:分数|fraction)\s+(.+?)\s+over\s+(.+)/i, transform: (m) => `\\frac{${m[1]}}{${m[2]}}` },
  { pattern: /根号\s*(.+)?/i, transform: (m) => m[1] ? `\\sqrt{${m[1]}}` : '\\sqrt{}' },
  { pattern: /(?:n次根号|nth root)\s+(.+?)\s+根\s+(.+)/i, transform: (m) => `\\sqrt[${m[1]}]{${m[2]}}` },
  { pattern: /(?:平方|squared)/i, transform: () => '^2' },
  { pattern: /(?:立方|cubed)/i, transform: () => '^3' },
  { pattern: /(?:上标|super)\s*(.+)/i, transform: (m) => `^{${m[1]}}` },
  { pattern: /(?:下标|sub)\s*(.+)/i, transform: (m) => `_{${m[1]}}` },
  { pattern: /x的(.+)次方/i, transform: (m) => `x^{${m[1]}}` },
  { pattern: /(?:正弦|sin)/i, transform: () => '\\sin' },
  { pattern: /(?:余弦|cos)/i, transform: () => '\\cos' },
  { pattern: /(?:正切|tan)/i, transform: () => '\\tan' },
  { pattern: /(?:对数|log)/i, transform: () => '\\log' },
  { pattern: /(?:自然对数|ln)/i, transform: () => '\\ln' },
  { pattern: /(?:指数|exp)/i, transform: () => '\\exp' },
  { pattern: /(?:求和|sum)\s+从\s+(.+?)\s+到\s+(.+)/i, transform: (m) => `\\sum_{${m[1]}}^{${m[2]}}` },
  { pattern: /(?:求和|sum)\s+from\s+(.+?)\s+to\s+(.+)/i, transform: (m) => `\\sum_{${m[1]}}^{${m[2]}}` },
  { pattern: /(?:积分|integral)\s+从\s+(.+?)\s+到\s+(.+)/i, transform: (m) => `\\int_{${m[1]}}^{${m[2]}}` },
  { pattern: /(?:积分|integral)\s+from\s+(.+?)\s+to\s+(.+)/i, transform: (m) => `\\int_{${m[1]}}^{${m[2]}}` },
  { pattern: /(?:求积|product)/i, transform: () => '\\prod' },
  { pattern: /(?:极限|limit)\s+(.+?)\s+趋近\s+(.+)/i, transform: (m) => `\\lim_{${m[1]} \\to ${m[2]}}` },
  { pattern: /(?:偏导|partial derivative)\s*(.+)?/i, transform: (m) => `\\frac{\\partial}{\\partial ${m[1] || 'x'}}` },
  { pattern: /(?:导数|derivative)\s*of\s*(.+)?/i, transform: (m) => `\\frac{d}{d${m[1] || 'x'}}` },
  { pattern: /(?:绝对值|absolute value)\s+(.+)/i, transform: (m) => `\\left| ${m[1]} \\right|` },
  { pattern: /(?:属于|in)/i, transform: () => '\\in' },
  { pattern: /(?:不属于|not in)/i, transform: () => '\\notin' },
  { pattern: /(?:不等于|not equal)/i, transform: () => '\\neq' },
  { pattern: /(?:约等于|approximately)/i, transform: () => '\\approx' },
  { pattern: /(?:小于等于|less than or equal)/i, transform: () => '\\leq' },
  { pattern: /(?:大于等于|greater than or equal)/i, transform: () => '\\geq' },
  { pattern: /(?:小于|less than)/i, transform: () => '<' },
  { pattern: /(?:大于|greater than)/i, transform: () => '>' },
  { pattern: /(?:无穷大|infinity)/i, transform: () => '\\infty' },
  { pattern: /(?:无穷小)/i, transform: () => '-\\infty' },
  { pattern: /(?:加号|plus)/i, transform: () => '+' },
  { pattern: /(?:减号|minus)/i, transform: () => '-' },
  { pattern: /(?:乘号|times|multiply)/i, transform: () => '\\times' },
  { pattern: /(?:点乘|cdot)/i, transform: () => '\\cdot' },
  { pattern: /(?:除号|divide)/i, transform: () => '\\div' },
  { pattern: /(?:正负号|plus minus)/i, transform: () => '\\pm' },
  { pattern: /(?:右箭头|right arrow)/i, transform: () => '\\rightarrow' },
  { pattern: /(?:左箭头|left arrow)/i, transform: () => '\\leftarrow' },
  { pattern: /(?:推出|implies)/i, transform: () => '\\Rightarrow' },
  { pattern: /(?:等价|if and only if|iff)/i, transform: () => '\\Leftrightarrow' },
  { pattern: /(?:映射|mapsto)/i, transform: () => '\\mapsto' },
  { pattern: /(?:阿尔法|alpha)/i, transform: () => '\\alpha' },
  { pattern: /(?:贝塔|beta)/i, transform: () => '\\beta' },
  { pattern: /(?:伽马|gamma)/i, transform: () => '\\gamma' },
  { pattern: /(?:德尔塔|delta)/i, transform: () => '\\delta' },
  { pattern: /(?:西塔|theta)/i, transform: () => '\\theta' },
  { pattern: /(?:拉姆达|lambda)/i, transform: () => '\\lambda' },
  { pattern: /(?:缪|mu)/i, transform: () => '\\mu' },
  { pattern: /(?:派|pi)/i, transform: () => '\\pi' },
  { pattern: /(?:西格玛|sigma)/i, transform: () => '\\sigma' },
  { pattern: /(?:欧米伽|omega)/i, transform: () => '\\omega' },
  { pattern: /(?:斐|phi)/i, transform: () => '\\phi' },
  { pattern: /(?:普赛|psi)/i, transform: () => '\\psi' },
  { pattern: /(?:实数集|real numbers)/i, transform: () => '\\mathbb{R}' },
  { pattern: /(?:整数集|integers)/i, transform: () => '\\mathbb{Z}' },
  { pattern: /(?:自然数集|natural numbers)/i, transform: () => '\\mathbb{N}' },
  { pattern: /(?:有理数集|rationals)/i, transform: () => '\\mathbb{Q}' },
  { pattern: /(?:复数集|complex numbers)/i, transform: () => '\\mathbb{C}' },
  { pattern: /(?:空集|empty set)/i, transform: () => '\\emptyset' },
  { pattern: /(?:交集|intersection)/i, transform: () => '\\cap' },
  { pattern: /(?:并集|union)/i, transform: () => '\\cup' },
  { pattern: /(?:子集|subset)/i, transform: () => '\\subset' },
  { pattern: /(?:真子集|proper subset)/i, transform: () => '\\subseteq' },
  { pattern: /(?:存在|exist)/i, transform: () => '\\exists' },
  { pattern: /(?:任意|for all)/i, transform: () => '\\forall' },
  { pattern: /(?:梯度|nabla)/i, transform: () => '\\nabla' },
  { pattern: /(?:偏微分|partial)/i, transform: () => '\\partial' },
  { pattern: /(?:矩阵|matrix)\s+(\d+)\s+行\s+(\d+)\s+列/i, transform: (m) => {
    const rows = parseInt(m[1]);
    const cols = parseInt(m[2]);
    let content = '';
    for (let i = 0; i < rows; i++) {
      for (let j = 0; j < cols; j++) {
        content += ' & ';
      }
      content = content.slice(0, -2) + ' \\\\ ';
    }
    return `\\begin{pmatrix} ${content.slice(0, -3)} \\end{pmatrix}`;
  }},
  { pattern: /(?:行列式|determinant)/i, transform: () => '\\begin{vmatrix}  &  \\\\  &  \\end{vmatrix}' },
  { pattern: /(?:分段函数|piecewise)/i, transform: () => '\\begin{cases}  &  \\\\  &  \\end{cases}' },
  { pattern: /(?:括号|parentheses)\s*(.+)?/i, transform: (m) => m[1] ? `\\left( ${m[1]} \\right)` : '\\left( \\right)' },
  { pattern: /(?:方括号|bracket)\s*(.+)?/i, transform: (m) => m[1] ? `\\left[ ${m[1]} \\right]` : '\\left[ \\right]' },
  { pattern: /(?:花括号|brace)\s*(.+)?/i, transform: (m) => m[1] ? `\\left\\{ ${m[1]} \\right\\}` : '\\left\\{ \\right\\}' },
  { pattern: /(?:省略号|ellipsis)/i, transform: () => '\\cdots' },
  { pattern: /(?:点|dot)/i, transform: () => '\\cdot' },
  { pattern: /(?:叉|cross)/i, transform: () => '\\times' },
  { pattern: /(?:角度|degree)/i, transform: () => '^\\circ' },
  { pattern: /(?:百分比|percent)/i, transform: () => '\\%' },
  { pattern: /(?:等于|equals)/i, transform: () => '=' },
  { pattern: /(?:恒等于|equiv)/i, transform: () => '\\equiv' },
];

const NUMBER_MAP: Record<string, string> = {
  '零': '0', '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
  '六': '6', '七': '7', '八': '8', '九': '9', '十': '10',
  '壹': '1', '贰': '2', '叁': '3', '肆': '4', '伍': '5',
  '陆': '6', '柒': '7', '捌': '8', '玖': '9',
  'π': '\\pi', 'e': 'e', 'i': 'i',
};

function preprocessText(text: string): string {
  let processed = text.trim().toLowerCase();
  processed = processed.replace(/[。，；：！？、]/g, ' ');
  for (const [word, num] of Object.entries(NUMBER_MAP)) {
    processed = processed.replace(new RegExp(word, 'gi'), num);
  }
  processed = processed.replace(/\s+/g, ' ').trim();
  return processed;
}

export function voiceTextToLatex(rawText: string): { latex: string; confidence: number; matchedRules: string[] } {
  const text = preprocessText(rawText);
  if (!text) {
    return { latex: '', confidence: 0, matchedRules: [] };
  }

  let result = text;
  const matchedRules: string[] = [];
  let matchCount = 0;

  for (const cmd of VOICE_COMMANDS) {
    if (cmd.pattern.test(result)) {
      result = result.replace(cmd.pattern, (match, ...groups) => {
        matchCount++;
        return cmd.transform([match, ...groups] as RegExpMatchArray);
      });
      if (cmd.pattern.source.length > 0) {
        matchedRules.push(cmd.pattern.source.slice(0, 20) + '...');
      }
    }
  }

  const englishNumbers: Record<string, string> = {
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
  };
  for (const [word, num] of Object.entries(englishNumbers)) {
    result = result.replace(new RegExp(`\\b${word}\\b`, 'gi'), num);
  }

  result = result.replace(/\s+/g, ' ').trim();

  const confidence = Math.min(0.95, 0.3 + matchCount * 0.1 + (result.length > 0 ? 0.2 : 0));

  return {
    latex: result,
    confidence,
    matchedRules: matchedRules.slice(0, 3),
  };
}

export interface WebSpeechVoice {
  voice: SpeechSynthesisVoice;
  lang: string;
  name: string;
}

export function getVoices(): WebSpeechVoice[] {
  if (!('speechSynthesis' in window)) return [];
  return window.speechSynthesis.getVoices()
    .filter((v) => v.lang.startsWith('zh') || v.lang.startsWith('en'))
    .map((v) => ({ voice: v, lang: v.lang, name: v.name }));
}

export function speakText(text: string, voice?: SpeechSynthesisVoice): void {
  if (!('speechSynthesis' in window)) return;
  const utterance = new SpeechSynthesisUtterance(text);
  if (voice) utterance.voice = voice;
  utterance.rate = 0.9;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

export interface RecognitionResult {
  transcript: string;
  confidence: number;
  isFinal: boolean;
}

export class VoiceRecognitionManager {
  private recognition: any = null;
  private onResult: ((result: RecognitionResult) => void) | null = null;
  private onError: ((error: string) => void) | null = null;
  private onEnd: (() => void) | null = null;
  private isListening = false;

  static isSupported(): boolean {
    return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
  }

  constructor(
    onResult: (result: RecognitionResult) => void,
    onError: (error: string) => void,
    onEnd: () => void,
  ) {
    this.onResult = onResult;
    this.onError = onError;
    this.onEnd = onEnd;

    const SR = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    if (SR) {
      this.recognition = new SR();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = 'zh-CN';

      this.recognition.onresult = (event: any) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          const transcript = result[0].transcript;
          const confidence = result[0].confidence || 0.8;
          const isFinal = result.isFinal;
          this.onResult?.({ transcript, confidence, isFinal });
        }
      };

      this.recognition.onerror = (event: any) => {
        const messages: Record<string, string> = {
          'no-speech': '未检测到语音',
          'audio-capture': '无法访问麦克风',
          'not-allowed': '麦克风权限被拒绝',
          'service-not-allowed': '语音服务不可用',
        };
        this.onError?.(messages[event.error] || `识别错误: ${event.error}`);
      };

      this.recognition.onend = () => {
        this.isListening = false;
        this.onEnd?.();
      };
    }
  }

  start(): void {
    if (!this.recognition) {
      this.onError?.('当前浏览器不支持语音识别，请使用Chrome或Edge浏览器');
      return;
    }
    try {
      this.recognition.start();
      this.isListening = true;
    } catch (e) {
      // Already started
    }
  }

  stop(): void {
    if (this.recognition) {
      this.recognition.stop();
      this.isListening = false;
    }
  }

  abort(): void {
    if (this.recognition) {
      this.recognition.abort();
      this.isListening = false;
    }
  }

  getIsListening(): boolean {
    return this.isListening;
  }
}

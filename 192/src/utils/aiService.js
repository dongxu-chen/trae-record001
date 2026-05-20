import { Editor, Transforms } from 'slate';

const AI_CONFIG = {
  enableMock: true,
  apiEndpoint: '/api/ai',
  debounceMs: 800,
};

const MOCK_COMPLETIONS = [
  '这是一个非常重要的观点，值得深入探讨。',
  '综上所述，我们可以得出以下结论。',
  '接下来，让我们分析一下具体的实施步骤。',
  '这个方案的优势在于它的灵活性和可扩展性。',
  '通过以上分析，我们可以清楚地看到问题的核心所在。',
  '为了更好地理解这个问题，我们需要从多个角度进行思考。',
  '这项技术的应用前景非常广阔，值得我们持续关注。',
  '在实际操作中，我们需要注意以下几个关键点。',
];

const MOCK_GRAMMAR_RULES = [
  { pattern: /的地得/g, suggestion: '请检查"的/地/得"的正确使用："的"修饰名词，"地"修饰动词，"得"补充说明', severity: 'warning' },
  { pattern: /因为[。，]/g, suggestion: '"因为"后面应该接"所以"，不应直接结束句子', severity: 'error' },
  { pattern: /不但[。，]/g, suggestion: '"不但"后面应该接"而且"，构成递进关系', severity: 'error' },
  { pattern: /虽然[。，]/g, suggestion: '"虽然"后面应该接"但是"，构成转折关系', severity: 'error' },
  { pattern: /[，。；：]{2,}/g, suggestion: '连续的标点符号，请删除多余的', severity: 'error' },
  { pattern: /[a-zA-Z]+/g, suggestion: '中英文混排时建议在英文前后加空格', severity: 'info' },
];

const MOCK_SUGGESTIONS = {
  improve: [
    { original: '非常', suggestion: '极为、尤为、甚是' },
    { original: '很多', suggestion: '众多、诸多、大量' },
    { original: '好', suggestion: '优秀、出色、卓越' },
    { original: '坏', suggestion: '糟糕、恶劣、不佳' },
    { original: '想', suggestion: '希望、期望、渴望' },
    { original: '说', suggestion: '表示、指出、阐述' },
    { original: '做', suggestion: '实施、执行、落实' },
  ],
};

let debounceTimer = null;

export function debounceAI(callback, delay = AI_CONFIG.debounceMs) {
  return (...args) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => callback(...args), delay);
  };
}

export async function getAICompletion(context, cursorPosition) {
  if (AI_CONFIG.enableMock) {
    return mockCompletion(context, cursorPosition);
  }
  
  try {
    const response = await fetch(AI_CONFIG.apiEndpoint + '/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ context, cursorPosition }),
    });
    return await response.json();
  } catch (error) {
    console.error('AI completion error:', error);
    return null;
  }
}

function mockCompletion(context, cursorPosition) {
  const randomCompletion = MOCK_COMPLETIONS[Math.floor(Math.random() * MOCK_COMPLETIONS.length)];
  
  return new Promise(resolve => {
    setTimeout(() => {
      resolve({
        text: randomCompletion,
        confidence: 0.85 + Math.random() * 0.15,
        alternatives: [
          MOCK_COMPLETIONS[(Math.floor(Math.random() * MOCK_COMPLETIONS.length))],
          MOCK_COMPLETIONS[(Math.floor(Math.random() * MOCK_COMPLETIONS.length))],
        ],
      });
    }, 500 + Math.random() * 500);
  });
}

export async function checkGrammar(text) {
  if (AI_CONFIG.enableMock) {
    return mockGrammarCheck(text);
  }
  
  try {
    const response = await fetch(AI_CONFIG.apiEndpoint + '/grammar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    return await response.json();
  } catch (error) {
    console.error('Grammar check error:', error);
    return [];
  }
}

function mockGrammarCheck(text) {
  const issues = [];
  
  for (const rule of MOCK_GRAMMAR_RULES) {
    let match;
    while ((match = rule.pattern.exec(text)) !== null) {
      issues.push({
        type: 'grammar',
        severity: rule.severity,
        start: match.index,
        end: match.index + match[0].length,
        text: match[0],
        suggestion: rule.suggestion,
        rule: rule.pattern.toString(),
      });
    }
  }
  
  return new Promise(resolve => {
    setTimeout(() => resolve(issues), 300);
  });
}

export async function getWritingSuggestions(text) {
  if (AI_CONFIG.enableMock) {
    return mockWritingSuggestions(text);
  }
  
  try {
    const response = await fetch(AI_CONFIG.apiEndpoint + '/suggest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    return await response.json();
  } catch (error) {
    console.error('Writing suggestions error:', error);
    return [];
  }
}

function mockWritingSuggestions(text) {
  const suggestions = [];
  
  for (const item of MOCK_SUGGESTIONS.improve) {
    const index = text.indexOf(item.original);
    if (index !== -1) {
      suggestions.push({
        type: 'improve',
        start: index,
        end: index + item.original.length,
        original: item.original,
        suggestions: item.suggestion.split('、'),
        reason: '建议使用更精准的表达',
      });
    }
  }
  
  return new Promise(resolve => {
    setTimeout(() => resolve(suggestions), 400);
  });
}

export async function rewriteSentence(sentence, style = 'professional') {
  if (AI_CONFIG.enableMock) {
    return mockRewrite(sentence, style);
  }
  
  try {
    const response = await fetch(AI_CONFIG.apiEndpoint + '/rewrite', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sentence, style }),
    });
    return await response.json();
  } catch (error) {
    console.error('Rewrite error:', error);
    return null;
  }
}

function mockRewrite(sentence, style) {
  const styleTemplates = {
    professional: `从专业角度来看，${sentence}这一观点具有重要的实践意义。`,
    casual: `话说回来，${sentence}，你懂的～`,
    formal: `兹就上述内容而言，${sentence}，理合陈明。`,
    simple: `${sentence}`,
    academic: `根据现有研究表明，${sentence}（Smith, 2023）。`,
  };
  
  return new Promise(resolve => {
    setTimeout(() => {
      resolve({
        original: sentence,
        rewritten: styleTemplates[style] || styleTemplates.professional,
        style,
      });
    }, 600);
  });
}

export function insertCompletion(editor, completion) {
  if (!editor.selection) return;
  
  const { anchor } = editor.selection;
  Transforms.insertText(editor, completion, { at: anchor });
}

export function applySuggestion(editor, suggestion) {
  const start = findPointAtOffset(editor, suggestion.start);
  const end = findPointAtOffset(editor, suggestion.end);
  
  if (start && end) {
    Transforms.delete(editor, { at: { anchor: start, focus: end } });
    Transforms.insertText(editor, suggestion.suggestions[0], { at: start });
  }
}

function findPointAtOffset(editor, targetOffset) {
  let currentOffset = 0;
  const nodes = Editor.nodes(editor, { at: [] });

  for (const [node, path] of nodes) {
    if (node.text) {
      if (currentOffset + node.text.length >= targetOffset) {
        return { path, offset: targetOffset - currentOffset };
      }
      currentOffset += node.text.length;
    }
    
    if (Editor.isBlock(editor, node)) {
      if (currentOffset === targetOffset) {
        const firstChildPath = [...path, 0];
        return { path: firstChildPath, offset: 0 };
      }
      currentOffset += 1;
    }
  }

  return null;
}

export function getEditorText(editor) {
  return Editor.string(editor, []);
}

export const AI_STYLES = [
  { id: 'professional', name: '专业', icon: '💼' },
  { id: 'casual', name: ' casual', icon: '😊' },
  { id: 'formal', name: '正式', icon: '🎩' },
  { id: 'simple', name: '简洁', icon: '✨' },
  { id: 'academic', name: '学术', icon: '📚' },
];

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';

const keywords = {
  javascript: [
    'const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while',
    'do', 'switch', 'case', 'break', 'continue', 'class', 'extends', 'new',
    'this', 'super', 'import', 'export', 'from', 'default', 'as', 'async',
    'await', 'try', 'catch', 'finally', 'throw', 'typeof', 'instanceof',
    'in', 'of', 'delete', 'void', 'null', 'true', 'false', 'undefined',
    'static', 'public', 'private', 'protected', 'get', 'set', 'yield', 'with'
  ],
  js: ['const', 'let', 'var', 'function', 'return', 'if', 'else'],
  python: [
    'def', 'class', 'return', 'if', 'elif', 'else', 'for', 'while', 'break',
    'continue', 'try', 'except', 'finally', 'raise', 'import', 'from', 'as',
    'with', 'lambda', 'pass', 'yield', 'global', 'nonlocal', 'assert', 'del',
    'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is', 'async', 'await'
  ],
  py: ['def', 'class', 'return', 'if', 'elif', 'else'],
  html: [],
  css: [],
  json: []
};

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function createTokenizer(language) {
  const langKeywords = keywords[language] || keywords.javascript;
  const keywordPattern = langKeywords.length > 0
    ? `\\b(${langKeywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`
    : '(?!)';

  const patterns = [
    { type: 'comment', regex: /\/\/[^\n]*/ },
    { type: 'comment', regex: /\/\*[\s\S]*?\*\// },
    { type: 'comment', regex: /#[^\n]*/ },
    { type: 'string', regex: /"(?:\\.|[^"\\])*"/ },
    { type: 'string', regex: /'(?:\\.|[^'\\])*'/ },
    { type: 'string', regex: /`(?:\\.|[^`\\])*`/ },
    { type: 'regex', regex: /\/(?:\\.|[^\/\\\n])+\/[gimsuy]*/ },
    { type: 'number', regex: /\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b/ },
    { type: 'number', regex: /\b0x[0-9a-fA-F]+\b/ },
    { type: 'keyword', regex: new RegExp(keywordPattern) },
    { type: 'function', regex: /\b([a-zA-Z_$][a-zA-Z0-9_$]*)(?=\s*\()/ },
    { type: 'tag', regex: /<\/?[a-zA-Z][a-zA-Z0-9-]*/ },
    { type: 'attr-name', regex: /\s+([a-zA-Z-]+)(?==)/ },
    { type: 'attr-value', regex: /=(?:"[^"]*"|'[^']*')/ },
    { type: 'operator', regex: /[+\-*\/%=<>!&|^~?:]+/ },
    { type: 'punctuation', regex: /[{}()\[\];,.]/ }
  ];

  return patterns;
}

function tokenize(text, language) {
  if (!text) return [];
  
  const patterns = createTokenizer(language);
  const tokens = [];
  let position = 0;

  while (position < text.length) {
    let matched = false;

    for (const { type, regex } of patterns) {
      regex.lastIndex = 0;
      const slice = text.slice(position);
      const match = slice.match(regex);

      if (match && match.index === 0) {
        const value = match[0];
        tokens.push({ type, value, start: position, end: position + value.length });
        position += value.length;
        matched = true;
        break;
      }
    }

    if (!matched) {
      const endOfWord = text.search(/[\s{}()\[\];,.+\-*\/%=<>!&|^~?:]/, position);
      const wordEnd = endOfWord === -1 ? text.length : endOfWord;
      
      if (wordEnd > position) {
        tokens.push({ type: 'text', value: text.slice(position, wordEnd), start: position, end: wordEnd });
        position = wordEnd;
      } else {
        tokens.push({ type: 'text', value: text[position], start: position, end: position + 1 });
        position++;
      }
    }
  }

  return tokens;
}

function highlightCode(text, language) {
  const tokens = tokenize(text, language);
  const result = [];
  let currentPos = 0;

  for (const token of tokens) {
    if (token.start > currentPos) {
      result.push(escapeHtml(text.slice(currentPos, token.start)));
    }

    const escaped = escapeHtml(token.value);
    result.push(`<span class="token-${token.type}">${escaped}</span>`);
    currentPos = token.end;
  }

  if (currentPos < text.length) {
    result.push(escapeHtml(text.slice(currentPos)));
  }

  return result.join('') || '&nbsp;';
}

function CodeEditor({ value, onChange, language }) {
  const textareaRef = useRef(null);
  const preRef = useRef(null);
  const [highlighted, setHighlighted] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const debounceRef = useRef(null);

  const syncScroll = useCallback(() => {
    if (textareaRef.current && preRef.current) {
      preRef.current.scrollTop = textareaRef.current.scrollTop;
      preRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  }, []);

  useEffect(() => {
    if (isComposing) return;

    if (debounceRef.current) {
      cancelAnimationFrame(debounceRef.current);
    }

    debounceRef.current = requestAnimationFrame(() => {
      setHighlighted(highlightCode(value || '', language || 'javascript'));
      debounceRef.current = null;
    });

    return () => {
      if (debounceRef.current) {
        cancelAnimationFrame(debounceRef.current);
      }
    };
  }, [value, language, isComposing]);

  const handleChange = (e) => {
    if (!isComposing) {
      onChange(e.target.value);
    }
  };

  const handleCompositionStart = () => {
    setIsComposing(true);
  };

  const handleCompositionEnd = (e) => {
    setIsComposing(false);
    onChange(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = textareaRef.current.selectionStart;
      const end = textareaRef.current.selectionEnd;
      const newValue = value.slice(0, start) + '  ' + value.slice(end);
      onChange(newValue);
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.selectionStart = start + 2;
          textareaRef.current.selectionEnd = start + 2;
        }
      }, 0);
    }
  };

  return (
    <div className="code-editor-wrapper">
      <div className="code-editor">
        <pre ref={preRef} aria-hidden="true">
          <code dangerouslySetInnerHTML={{ __html: highlighted }} />
        </pre>
        <textarea
          ref={textareaRef}
          value={value || ''}
          onChange={handleChange}
          onScroll={syncScroll}
          onKeyDown={handleKeyDown}
          onCompositionStart={handleCompositionStart}
          onCompositionEnd={handleCompositionEnd}
          spellCheck={false}
          placeholder="在这里输入你的代码..."
        />
      </div>
    </div>
  );
}

export default CodeEditor;

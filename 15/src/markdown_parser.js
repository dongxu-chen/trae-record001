import { marked } from 'marked';
import hljs from 'highlight.js';

const renderer = new marked.Renderer();

renderer.code = (code, language) => {
  const validLang = language && hljs.getLanguage(language);
  const highlighted = validLang
    ? hljs.highlight(code, { language }).value
    : hljs.highlightAuto(code).value;
  return `<pre><code class="hljs language-${language || 'text'}">${highlighted}</code></pre>`;
};

renderer.blockquote = (quote) => {
  return `<blockquote class="markdown-quote">${quote}</blockquote>`;
};

marked.setOptions({
  breaks: true,
  gfm: true,
  renderer
});

export function renderMarkdown(markdown) {
  if (!markdown || markdown.trim() === '') {
    return '<p class="empty-preview">开始编写，这里会显示预览...</p>';
  }
  
  try {
    return marked.parse(markdown);
  } catch (e) {
    console.error('Markdown parsing error:', e);
    return `<p class="parse-error">解析错误: ${e.message}</p>`;
  }
}

export function extractTitle(markdown) {
  if (!markdown) return '';
  const lines = markdown.split('\n');
  for (const line of lines) {
    const match = line.match(/^#+\s*(.+)$/);
    if (match) {
      return match[1].trim();
    }
    const trimmed = line.trim();
    if (trimmed) {
      return trimmed.slice(0, 50);
    }
  }
  return '';
}

export { marked, hljs };

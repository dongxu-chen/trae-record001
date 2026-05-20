import { saveAs } from 'file-saver';
import { marked } from 'marked';
import TurndownService from 'turndown';
import { jsPDF } from 'jspdf';
import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, LevelFormat } from 'docx';

const turndownService = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
});

export function exportToMarkdown(editorValue) {
  const html = slateToHtml(editorValue);
  const markdown = turndownService.turndown(html);
  
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
  saveAs(blob, 'document.md');
  
  return markdown;
}

export function exportToHtml(editorValue) {
  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Document</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; line-height: 1.8; }
    h1 { font-size: 28px; margin-bottom: 16px; }
    h2 { font-size: 22px; margin-bottom: 12px; }
    h3 { font-size: 18px; margin-bottom: 10px; }
    p { margin-bottom: 12px; }
    blockquote { border-left: 4px solid #667eea; padding-left: 16px; color: #666; margin: 16px 0; }
    pre { background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 8px; overflow-x: auto; }
    code { font-family: Consolas, Monaco, monospace; }
    ul, ol { padding-left: 24px; }
    li { margin: 4px 0; }
    hr { border: none; border-top: 2px solid #e8e8e8; margin: 24px 0; }
  </style>
</head>
<body>
${slateToHtml(editorValue)}
</body>
</html>`;

  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  saveAs(blob, 'document.html');
  
  return html;
}

export async function exportToPDF(editorValue, options = {}) {
  const html = slateToHtml(editorValue);
  
  const printWindow = window.open('', '_blank');
  printWindow.document.write(`<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>Document</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px; line-height: 1.8; }
    h1 { font-size: 28px; margin-bottom: 16px; }
    h2 { font-size: 22px; margin-bottom: 12px; }
    h3 { font-size: 18px; margin-bottom: 10px; }
    p { margin-bottom: 12px; }
    blockquote { border-left: 4px solid #667eea; padding-left: 16px; color: #666; margin: 16px 0; }
    pre { background: #f5f5f5; padding: 16px; border-radius: 8px; }
    code { font-family: Consolas, Monaco, monospace; }
    ul, ol { padding-left: 24px; }
    li { margin: 4px 0; }
    hr { border: none; border-top: 2px solid #e8e8e8; margin: 24px 0; }
    @media print {
      body { padding: 20px; }
    }
  </style>
</head>
<body>
${html}
<script>
  window.onload = function() {
    window.print();
    window.onafterprint = function() {
      window.close();
    };
  };
</script>
</body>
</html>`);
  printWindow.document.close();
  
  return true;
}

export async function exportToWord(editorValue) {
  const children = [];
  
  for (const node of editorValue) {
    const paragraph = convertSlateNodeToDocx(node);
    if (paragraph) {
      if (Array.isArray(paragraph)) {
        children.push(...paragraph);
      } else {
        children.push(paragraph);
      }
    }
  }
  
  const doc = new Document({
    sections: [{
      properties: {},
      children,
    }],
  });
  
  const blob = await Packer.toBlob(doc);
  saveAs(blob, 'document.docx');
  
  return doc;
}

function convertSlateNodeToDocx(node) {
  if (!node) return null;
  
  switch (node.type) {
    case 'heading-one':
      return new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: node.children?.map(child => convertTextNode(child)).filter(Boolean) || [],
      });
      
    case 'heading-two':
      return new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: node.children?.map(child => convertTextNode(child)).filter(Boolean) || [],
      });
      
    case 'heading-three':
      return new Paragraph({
        heading: HeadingLevel.HEADING_3,
        children: node.children?.map(child => convertTextNode(child)).filter(Boolean) || [],
      });
      
    case 'block-quote':
      return new Paragraph({
        style: 'Quote',
        children: node.children?.map(child => convertTextNode(child)).filter(Boolean) || [],
      });
      
    case 'code-block':
      return new Paragraph({
        style: 'Code',
        children: node.children?.map(child => convertTextNode(child)).filter(Boolean) || [],
      });
      
    case 'bulleted-list':
      return node.children?.map((item, idx) => 
        new Paragraph({
          bullet: { level: 0 },
          children: item.children?.map(child => 
            child.children?.map(c => convertTextNode(c)).flat() || []
          ).flat() || [],
        })
      ) || [];
      
    case 'numbered-list':
      return node.children?.map((item, idx) => 
        new Paragraph({
          numbering: { reference: 'default', level: 0 },
          children: item.children?.map(child => 
            child.children?.map(c => convertTextNode(c)).flat() || []
          ).flat() || [],
        })
      ) || [];
      
    case 'paragraph':
    default:
      return new Paragraph({
        children: node.children?.map(child => convertTextNode(child)).filter(Boolean) || [],
        alignment: node.align ? convertAlignment(node.align) : AlignmentType.LEFT,
      });
  }
}

function convertTextNode(node) {
  if (!node || !node.text) return new TextRun('');
  
  const options = { text: node.text };
  
  if (node.bold) options.bold = true;
  if (node.italic) options.italics = true;
  if (node.underline) options.underline = {};
  if (node.strikethrough) options.strike = true;
  
  return new TextRun(options);
}

function convertAlignment(align) {
  switch (align) {
    case 'center': return AlignmentType.CENTER;
    case 'right': return AlignmentType.RIGHT;
    case 'justify': return AlignmentType.JUSTIFIED;
    default: return AlignmentType.LEFT;
  }
}

function slateToHtml(editorValue) {
  if (!Array.isArray(editorValue)) return '';
  
  return editorValue.map(node => slateNodeToHtml(node)).join('\n');
}

function slateNodeToHtml(node, depth = 0) {
  if (!node) return '';
  
  if (node.text !== undefined) {
    let html = escapeHtml(node.text);
    if (node.bold) html = `<strong>${html}</strong>`;
    if (node.italic) html = `<em>${html}</em>`;
    if (node.underline) html = `<u>${html}</u>`;
    if (node.strikethrough) html = `<s>${html}</s>`;
    if (node.code) html = `<code>${html}</code>`;
    return html;
  }
  
  const childrenHtml = node.children?.map(child => slateNodeToHtml(child, depth + 1)).join('') || '';
  
  switch (node.type) {
    case 'heading-one':
      return `<h1>${childrenHtml}</h1>`;
    case 'heading-two':
      return `<h2>${childrenHtml}</h2>`;
    case 'heading-three':
      return `<h3>${childrenHtml}</h3>`;
    case 'block-quote':
      return `<blockquote>${childrenHtml}</blockquote>`;
    case 'code-block':
      return `<pre><code>${childrenHtml}</code></pre>`;
    case 'bulleted-list':
      return `<ul>${childrenHtml}</ul>`;
    case 'numbered-list':
      return `<ol>${childrenHtml}</ol>`;
    case 'list-item':
      return `<li>${childrenHtml}</li>`;
    case 'thematic-break':
      return `<hr />`;
    case 'paragraph':
    default:
      const style = node.align ? ` style="text-align: ${node.align};"` : '';
      return `<p${style}>${childrenHtml || '<br>'}</p>`;
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

export const EXPORT_FORMATS = [
  { id: 'markdown', name: 'Markdown', icon: '📝', extension: '.md', description: '轻量级标记语言' },
  { id: 'html', name: 'HTML', icon: '🌐', extension: '.html', description: '网页格式' },
  { id: 'pdf', name: 'PDF', icon: '📕', extension: '.pdf', description: '便携式文档格式' },
  { id: 'word', name: 'Word', icon: '📘', extension: '.docx', description: 'Microsoft Word 文档' },
];

export async function exportDocument(editorValue, format) {
  switch (format) {
    case 'markdown':
      return exportToMarkdown(editorValue);
    case 'html':
      return exportToHtml(editorValue);
    case 'pdf':
      return exportToPDF(editorValue);
    case 'word':
      return exportToWord(editorValue);
    default:
      throw new Error(`Unsupported format: ${format}`);
  }
}

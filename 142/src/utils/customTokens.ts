export interface HighlightToken {
  pattern: string | RegExp;
  color: string;
  backgroundColor?: string;
  fontWeight?: 'normal' | 'bold';
  fontStyle?: 'normal' | 'italic';
  className?: string;
}

export interface TokenMatch {
  start: number;
  end: number;
  text: string;
  token: HighlightToken;
}

function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function findCustomTokens(line: string, tokens: HighlightToken[]): TokenMatch[] {
  const matches: TokenMatch[] = [];

  for (const token of tokens) {
    let regex: RegExp;

    if (typeof token.pattern === 'string') {
      regex = new RegExp(`\\b${escapeRegExp(token.pattern)}\\b`, 'g');
    } else {
      regex = new RegExp(token.pattern.source, token.pattern.flags.includes('g') ? token.pattern.flags : token.pattern.flags + 'g');
    }

    let match: RegExpExecArray | null;
    while ((match = regex.exec(line)) !== null) {
      matches.push({
        start: match.index,
        end: match.index + match[0].length,
        text: match[0],
        token,
      });
    }
  }

  matches.sort((a, b) => a.start - b.start);

  const result: TokenMatch[] = [];
  let lastEnd = -1;

  for (const match of matches) {
    if (match.start >= lastEnd) {
      result.push(match);
      lastEnd = match.end;
    } else if (match.end > lastEnd) {
      const adjustedMatch = {
        ...match,
        start: lastEnd,
        text: match.text.slice(lastEnd - match.start),
      };
      result.push(adjustedMatch);
      lastEnd = match.end;
    }
  }

  return result;
}

export function applyCustomTokens(html: string, tokens: HighlightToken[]): string {
  if (tokens.length === 0) return html;

  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = html;
  const text = tempDiv.textContent || '';

  const matches = findCustomTokens(text, tokens);
  if (matches.length === 0) return html;

  let result = '';
  let lastIndex = 0;

  for (const match of matches) {
    if (match.start > lastIndex) {
      result += text.slice(lastIndex, match.start);
    }

    const styleParts: string[] = [];
    if (match.token.color) styleParts.push(`color: ${match.token.color}`);
    if (match.token.backgroundColor) styleParts.push(`background-color: ${match.token.backgroundColor}`);
    if (match.token.fontWeight) styleParts.push(`font-weight: ${match.token.fontWeight}`);
    if (match.token.fontStyle) styleParts.push(`font-style: ${match.token.fontStyle}`);

    const className = match.token.className || 'custom-token';
    const style = styleParts.length > 0 ? ` style="${styleParts.join('; ')}"` : '';

    result += `<span class="${className}"${style}>${match.text}</span>`;
    lastIndex = match.end;
  }

  if (lastIndex < text.length) {
    result += text.slice(lastIndex);
  }

  return result;
}

export const predefinedTokens: Record<string, HighlightToken[]> = {
  importantVariables: [
    {
      pattern: 'user',
      color: '#ff6b6b',
      fontWeight: 'bold',
      className: 'token-var-user',
    },
    {
      pattern: 'data',
      color: '#4ecdc4',
      fontWeight: 'bold',
      className: 'token-var-data',
    },
    {
      pattern: 'config',
      color: '#ffe66d',
      fontWeight: 'bold',
      className: 'token-var-config',
    },
  ],
  todos: [
    {
      pattern: /TODO|FIXME|XXX|HACK/,
      color: '#ff4757',
      backgroundColor: 'rgba(255, 71, 87, 0.1)',
      fontWeight: 'bold',
      className: 'token-todo',
    },
  ],
  warnings: [
    {
      pattern: /console\.(warn|error|log)/,
      color: '#ffa502',
      fontWeight: 'bold',
      className: 'token-console',
    },
  ],
};

export function combineTokens(...tokenGroups: HighlightToken[][]): HighlightToken[] {
  return tokenGroups.flat();
}

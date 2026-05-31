import React, { useMemo } from 'react';

const RegexVisualizer = ({ pattern }) => {
  const parsed = useMemo(() => {
    if (!pattern) return null;
    return parseRegex(pattern);
  }, [pattern]);

  if (!pattern) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📊</div>
        <p>输入正则表达式以查看可视化</p>
      </div>
    );
  }

  if (!parsed) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠️</div>
        <p>无法解析该正则表达式</p>
      </div>
    );
  }

  return (
    <div className="visualization-area">
      <svg width="600" height={`${parsed.height + 80}`} viewBox={`0 0 600 ${parsed.height + 80}`}>
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#667eea" />
          </marker>
        </defs>
        
        {renderNode(parsed, 40, 40)}
      </svg>
    </div>
  );
};

const parseRegex = (pattern) => {
  try {
    const tokens = tokenize(pattern);
    return buildTree(tokens);
  } catch (e) {
    return null;
  }
};

const tokenize = (pattern) => {
  const tokens = [];
  let i = 0;
  
  while (i < pattern.length) {
    const char = pattern[i];
    
    if (char === '\\' && i + 1 < pattern.length) {
      const next = pattern[i + 1];
      const special = { 'd': '\\d', 'w': '\\w', 's': '\\s', 'b': '\\b', '.': '\\.', '\\': '\\\\' };
      if (special[next]) {
        tokens.push({ type: 'special', value: special[next], label: getLabel(special[next]) });
      } else {
        tokens.push({ type: 'literal', value: next, label: `'${next}'` });
      }
      i += 2;
      continue;
    }
    
    if (char === '[') {
      let end = pattern.indexOf(']', i);
      if (end === -1) end = pattern.length;
      const charset = pattern.slice(i, end + 1);
      tokens.push({ type: 'charset', value: charset, label: `字符集 ${charset}` });
      i = end + 1;
      continue;
    }
    
    if (char === '(') {
      if (pattern.slice(i, i + 3) === '(?:') {
        let depth = 1;
        let end = i + 3;
        while (end < pattern.length && depth > 0) {
          if (pattern[end] === '(' && pattern[end - 1] !== '\\') depth++;
          if (pattern[end] === ')' && pattern[end - 1] !== '\\') depth--;
          end++;
        }
        const group = pattern.slice(i, end);
        tokens.push({ type: 'nonCaptureGroup', value: group, label: '非捕获组' });
        i = end;
      } else {
        let depth = 1;
        let end = i + 1;
        while (end < pattern.length && depth > 0) {
          if (pattern[end] === '(' && pattern[end - 1] !== '\\') depth++;
          if (pattern[end] === ')' && pattern[end - 1] !== '\\') depth--;
          end++;
        }
        const group = pattern.slice(i, end);
        tokens.push({ type: 'group', value: group, label: '捕获组' });
        i = end;
      }
      continue;
    }
    
    if (char === '{') {
      let end = pattern.indexOf('}', i);
      if (end === -1) end = pattern.length;
      const quantifier = pattern.slice(i, end + 1);
      tokens.push({ type: 'quantifier', value: quantifier, label: quantifier });
      i = end + 1;
      continue;
    }
    
    const quantifiers = { '+': '一个或多个', '*': '零个或多个', '?': '零个或一个' };
    if (quantifiers[char]) {
      tokens.push({ type: 'quantifier', value: char, label: `${char} (${quantifiers[char]})` });
      i++;
      continue;
    }
    
    const anchors = { '^': '行首', '$': '行尾' };
    if (anchors[char]) {
      tokens.push({ type: 'anchor', value: char, label: `${char} (${anchors[char]})` });
      i++;
      continue;
    }
    
    if (char === '|') {
      tokens.push({ type: 'alternation', value: '|', label: 'OR' });
      i++;
      continue;
    }
    
    if (char === '.') {
      tokens.push({ type: 'special', value: '.', label: '. (任意字符)' });
      i++;
      continue;
    }
    
    tokens.push({ type: 'literal', value: char, label: `'${char}'` });
    i++;
  }
  
  return tokens;
};

const buildTree = (tokens) => {
  if (!tokens || tokens.length === 0) return null;
  
  let x = 0;
  let y = 0;
  const width = 120;
  const height = 50;
  const gapX = 20;
  const gapY = 60;
  
  const nodes = [];
  const links = [];
  
  let prevNode = null;
  
  tokens.forEach((token, index) => {
    const node = {
      id: index,
      ...token,
      x,
      y,
      width,
      height
    };
    
    nodes.push(node);
    
    if (prevNode) {
      links.push({
        from: prevNode.id,
        to: node.id
      });
    }
    
    prevNode = node;
    x += width + gapX;
    
    if (x + width > 560) {
      x = 0;
      y += height + gapY;
      prevNode = null;
    }
  });
  
  return {
    nodes,
    links,
    height: y + height
  };
};

const renderNode = (parsed, offsetX, offsetY) => {
  if (!parsed || !parsed.nodes) return null;
  
  const elements = [];
  
  parsed.links.forEach((link, index) => {
    const fromNode = parsed.nodes.find(n => n.id === link.from);
    const toNode = parsed.nodes.find(n => n.id === link.to);
    
    if (fromNode && toNode) {
      const sameRow = fromNode.y === toNode.y;
      let x1, y1, x2, y2;
      
      if (sameRow) {
        x1 = fromNode.x + offsetX + fromNode.width;
        y1 = fromNode.y + offsetY + fromNode.height / 2;
        x2 = toNode.x + offsetX;
        y2 = toNode.y + offsetY + toNode.height / 2;
      } else {
        x1 = fromNode.x + offsetX + fromNode.width / 2;
        y1 = fromNode.y + offsetY + fromNode.height;
        x2 = toNode.x + offsetX + toNode.width / 2;
        y2 = toNode.y + offsetY;
      }
      
      if (sameRow) {
        elements.push(
          <line
            key={`link-${index}`}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke="#667eea"
            strokeWidth="2"
            markerEnd="url(#arrowhead)"
          />
        );
      } else {
        const midY = y1 + (y2 - y1) / 2;
        const path = `M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}`;
        elements.push(
          <path
            key={`link-${index}`}
            d={path}
            fill="none"
            stroke="#667eea"
            strokeWidth="2"
            markerEnd="url(#arrowhead)"
          />
        );
      }
    }
  });
  
  parsed.nodes.forEach((node) => {
    const colors = {
      special: '#3b82f6',
      literal: '#10b981',
      charset: '#8b5cf6',
      group: '#ec4899',
      nonCaptureGroup: '#f59e0b',
      quantifier: '#f97316',
      anchor: '#6366f1',
      alternation: '#ef4444'
    };
    
    const color = colors[node.type] || '#6b7280';
    
    elements.push(
      <g key={`node-${node.id}`}>
        <rect
          x={node.x + offsetX}
          y={node.y + offsetY}
          width={node.width}
          height={node.height}
          rx="8"
          ry="8"
          fill={color + '15'}
          stroke={color}
          strokeWidth="2"
        />
        <text
          x={node.x + offsetX + node.width / 2}
          y={node.y + offsetY + node.height / 2 - 8}
          textAnchor="middle"
          fill={color}
          fontSize="14"
          fontWeight="600"
          fontFamily="monospace"
        >
          {node.value}
        </text>
        <text
          x={node.x + offsetX + node.width / 2}
          y={node.y + offsetY + node.height / 2 + 12}
          textAnchor="middle"
          fill="#666"
          fontSize="11"
        >
          {node.label}
        </text>
      </g>
    );
  });
  
  return elements;
};

const getLabel = (value) => {
  const labels = {
    '\\d': '数字 [0-9]',
    '\\w': '单词字符',
    '\\s': '空白字符',
    '\\b': '单词边界',
    '\\.': '点号',
    '.': '任意字符'
  };
  return labels[value] || value;
};

export default RegexVisualizer;

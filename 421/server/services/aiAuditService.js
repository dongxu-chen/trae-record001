const commonTypos = {
  '的是': '是的',
  '了的': '的了',
  '一一': '一一',
  '因为所以': '因为...所以',
  '虽然但是': '虽然...但是',
  '我我': '我',
  '你你': '你',
  '他他': '他',
  '的的': '的',
  '了了': '了',
  '和和': '和',
  '是是': '是',
  '在在': '在',
  '有有': '有',
  '不不会': '不会',
  '很很好': '很好',
  '非非常': '非常',
  '的的话': '的话',
  '一个一个': '一个',
  '的问题': '问题',
  '的情况': '情况',
  'the the': 'the',
  'a a': 'a',
  'is is': 'is',
  'are are': 'are',
  'teh': 'the',
  'recieve': 'receive',
  'acheive': 'achieve',
  'occured': 'occurred',
  'seperate': 'separate',
  'definately': 'definitely',
  'accomodate': 'accommodate',
  'occurence': 'occurrence',
  'untill': 'until',
  'begining': 'beginning',
  'apparantly': 'apparently',
  'goverment': 'government',
  'enviroment': 'environment'
};

const grammarRules = [
  {
    id: 'double_subject',
    pattern: /(我们|你们|他们|她们|它们|我|你|他|她|它)\s*(都|也|还|就|才|只|又|都还|也还|还都|还也)\s*(是|在|有|要|会|能|可以|应该|必须)/g,
    category: 'grammar',
    type: 'grammar',
    severity: 'medium',
    explanation: '检测到可能的语法问题：主语重复或副词位置不当',
    confidence: 0.7
  },
  {
    id: 'missing_predicate',
    pattern: /^[^。！？；]*?(的|了|着|过)$/gm,
    category: 'grammar',
    type: 'grammar',
    severity: 'low',
    explanation: '句子可能缺少谓语动词，建议检查',
    confidence: 0.5
  },
  {
    id: 'run_on_sentence',
    pattern: /[^。！？；]{100,}[，,]/gm,
    category: 'sentence_structure',
    type: 'clarity',
    severity: 'medium',
    explanation: '句子过长，建议拆分为多个短句以提高可读性',
    confidence: 0.6
  },
  {
    id: 'passive_voice',
    pattern: /被|由|让|给|为|被...所/g,
    category: 'style',
    type: 'style',
    severity: 'low',
    explanation: '使用了被动语态，考虑改为主动语态以增强表达力度',
    confidence: 0.5
  },
  {
    id: 'weasel_words',
    pattern: /可能|也许|或许|大概|差不多|几乎|基本上|大概|一些|某些|部分/g,
    category: 'clarity',
    type: 'clarity',
    severity: 'low',
    explanation: '使用了模糊词语，建议使用更精确的表达',
    confidence: 0.4
  },
  {
    id: 'cliche_phrases',
    pattern: /众所周知|不言而喻|显而易见|不言而喻|总而言之|综上所述|最后但并非最不重要/g,
    category: 'style',
    type: 'style',
    severity: 'low',
    explanation: '使用了陈词滥调，建议使用更有创意的表达',
    confidence: 0.5
  },
  {
    id: 'informal_language',
    pattern: /其实|说实话|老实说|我觉得|我认为|我想|应该是|可能是/g,
    category: 'style',
    type: 'style',
    severity: 'low',
    explanation: '使用了口语化表达，正式文档建议使用更专业的语言',
    confidence: 0.4
  },
  {
    id: 'subject_verb_agreement',
    pattern: /(他们|她们|它们|这些|那些|很多|许多|一些|多个)\s*(是|在|有|要|会|能|可以|应该|必须)\s*(了|过|着)/g,
    category: 'grammar',
    type: 'grammar',
    severity: 'medium',
    explanation: '主谓搭配可能不一致，建议检查',
    confidence: 0.5
  }
];

const punctuationRules = [
  {
    id: 'chinese_comma',
    pattern: /[，,]{2,}/g,
    category: 'punctuation',
    type: 'format',
    severity: 'low',
    explanation: '检测到重复的逗号',
    fix: '，',
    confidence: 0.9
  },
  {
    id: 'chinese_period',
    pattern: /[。.]{2,}/g,
    category: 'punctuation',
    type: 'format',
    severity: 'low',
    explanation: '检测到重复的句号',
    fix: '。',
    confidence: 0.9
  },
  {
    id: 'space_needed',
    pattern: /([a-zA-Z])([\u4e00-\u9fa5])/g,
    category: 'formatting',
    type: 'format',
    severity: 'low',
    explanation: '中英文之间建议添加空格',
    confidence: 0.7
  },
  {
    id: 'fullwidth_halfwidth',
    pattern: /[\u4e00-\u9fa5][,.;:!?][\u4e00-\u9fa5]/g,
    category: 'punctuation',
    type: 'format',
    severity: 'medium',
    explanation: '中文文本中应使用全角标点',
    confidence: 0.8
  },
  {
    id: 'space_before_punctuation',
    pattern: /\s+[，。！？；：、）》】]/g,
    category: 'punctuation',
    type: 'format',
    severity: 'low',
    explanation: '中文标点前不应有空格',
    confidence: 0.8
  }
];

const styleRules = [
  {
    id: 'long_paragraph',
    minLength: 500,
    category: 'style',
    type: 'clarity',
    severity: 'medium',
    explanation: '段落过长，建议分段以提高可读性',
    confidence: 0.7
  },
  {
    id: 'first_person',
    pattern: /我|我们|咱们/g,
    category: 'style',
    type: 'style',
    severity: 'low',
    explanation: '正式文档建议避免使用第一人称',
    confidence: 0.5
  },
  {
    id: 'contractions',
    pattern: /\b(it's|don't|can't|won't|isn't|aren't|wasn't|weren't|haven't|hasn't|hadn't|wouldn't|couldn't|shouldn't|doesn't|didn't|I'm|you're|he's|she's|we're|they're|I've|you've|we've|they've|I'll|you'll|he'll|she'll|we'll|they'll|I'd|you'd|he'd|she'd|we'd|they'd)\b/g,
    category: 'style',
    type: 'style',
    severity: 'low',
    explanation: '正式文档建议避免使用缩写形式',
    confidence: 0.6
  }
];

class AIAuditService {
  constructor() {
    this.suggestions = [];
  }

  async analyzeText(text, options = {}) {
    const suggestions = [];
    
    const paragraphs = text.split(/\n\n+/);
    const sentences = text.split(/[。！？!?；;]/g);

    const typos = this.detectTypos(text);
    suggestions.push(...typos);

    const grammarIssues = this.detectGrammarIssues(text);
    suggestions.push(...grammarIssues);

    const punctuationIssues = this.detectPunctuationIssues(text);
    suggestions.push(...punctuationIssues);

    const styleIssues = this.detectStyleIssues(text, paragraphs);
    suggestions.push(...styleIssues);

    const consistencyIssues = this.detectConsistencyIssues(text);
    suggestions.push(...consistencyIssues);

    if (options.detectFormat) {
      const formatIssues = this.detectFormatIssues(text);
      suggestions.push(...formatIssues);
    }

    const sortedSuggestions = suggestions
      .sort((a, b) => {
        const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
        return severityOrder[a.severity] - severityOrder[b.severity];
      })
      .slice(0, options.limit || 50);

    return sortedSuggestions;
  }

  detectTypos(text) {
    const suggestions = [];
    
    for (const [typo, correction] of Object.entries(commonTypos)) {
      const regex = new RegExp(typo, 'gi');
      let match;
      
      while ((match = regex.exec(text)) !== null) {
        if (this.isValidTypoContext(text, match.index, typo)) {
          suggestions.push({
            type: 'typo',
            category: 'spelling',
            severity: 'high',
            originalText: match[0],
            suggestedText: correction,
            explanation: `可能的拼写错误："${match[0]}"，建议改为"${correction}"`,
            startPos: match.index,
            endPos: match.index + match[0].length,
            ruleId: 'typo_dictionary',
            confidence: 0.95
          });
        }
      }
    }

    const repeatedChars = text.match(/(.)\1{2,}/g);
    if (repeatedChars) {
      for (const match of repeatedChars) {
        const index = text.indexOf(match);
        suggestions.push({
          type: 'typo',
          category: 'spelling',
          severity: 'medium',
          originalText: match,
          suggestedText: match[0],
          explanation: `检测到重复字符"${match}"，可能是输入错误`,
          startPos: index,
          endPos: index + match.length,
          ruleId: 'repeated_chars',
          confidence: 0.8
        });
      }
    }

    return suggestions;
  }

  isValidTypoContext(text, index, typo) {
    const before = text[index - 1] || '';
    const after = text[index + typo.length] || '';
    
    if (/[\u4e00-\u9fa5]/.test(before) && /[\u4e00-\u9fa5]/.test(after)) {
      return true;
    }
    
    if ((before === ' ' || before === '') && (after === ' ' || after === '')) {
      return true;
    }
    
    return false;
  }

  detectGrammarIssues(text) {
    const suggestions = [];

    for (const rule of grammarRules) {
      let match;
      const pattern = new RegExp(rule.pattern.source, rule.pattern.flags);
      
      while ((match = pattern.exec(text)) !== null) {
        suggestions.push({
          type: rule.type,
          category: rule.category,
          severity: rule.severity,
          originalText: match[0],
          explanation: rule.explanation,
          startPos: match.index,
          endPos: match.index + match[0].length,
          ruleId: rule.id,
          confidence: rule.confidence
        });
      }
    }

    return suggestions;
  }

  detectPunctuationIssues(text) {
    const suggestions = [];

    for (const rule of punctuationRules) {
      let match;
      const pattern = new RegExp(rule.pattern.source, rule.pattern.flags);
      
      while ((match = pattern.exec(text)) !== null) {
        const suggestion = {
          type: rule.type,
          category: rule.category,
          severity: rule.severity,
          originalText: match[0],
          explanation: rule.explanation,
          startPos: match.index,
          endPos: match.index + match[0].length,
          ruleId: rule.id,
          confidence: rule.confidence
        };

        if (rule.fix) {
          suggestion.suggestedText = rule.fix;
        }

        suggestions.push(suggestion);
      }
    }

    return suggestions;
  }

  detectStyleIssues(text, paragraphs) {
    const suggestions = [];

    for (const rule of styleRules) {
      if (rule.minLength) {
        for (let i = 0; i < paragraphs.length; i++) {
          if (paragraphs[i].length > rule.minLength) {
            const startPos = text.indexOf(paragraphs[i]);
            suggestions.push({
              type: rule.type,
              category: rule.category,
              severity: rule.severity,
              originalText: paragraphs[i].substring(0, 100) + '...',
              explanation: rule.explanation + ` (${paragraphs[i].length}字)`,
              startPos,
              endPos: startPos + paragraphs[i].length,
              ruleId: rule.id,
              confidence: rule.confidence
            });
          }
        }
      } else if (rule.pattern) {
        let match;
        const pattern = new RegExp(rule.pattern.source, rule.pattern.flags);
        
        while ((match = pattern.exec(text)) !== null) {
          suggestions.push({
            type: rule.type,
            category: rule.category,
            severity: rule.severity,
            originalText: match[0],
            explanation: rule.explanation,
            startPos: match.index,
            endPos: match.index + match[0].length,
            ruleId: rule.id,
            confidence: rule.confidence
          });
        }
      }
    }

    return suggestions;
  }

  detectConsistencyIssues(text) {
    const suggestions = [];
    
    const terms = {};
    const englishWords = text.match(/\b[a-zA-Z]{3,}\b/g) || [];
    
    for (const word of englishWords) {
      const lower = word.toLowerCase();
      if (!terms[lower]) {
        terms[lower] = new Set();
      }
      terms[lower].add(word);
    }

    for (const [lower, variations] of Object.entries(terms)) {
      if (variations.size > 1) {
        const variationList = Array.from(variations);
        suggestions.push({
          type: 'consistency',
          category: 'terminology',
          severity: 'medium',
          originalText: variationList.join(', '),
          suggestedText: variationList[0],
          explanation: `术语不一致：检测到"${variationList.join('"和"')}"多种写法，建议统一为"${variationList[0]}"`,
          ruleId: 'term_consistency',
          confidence: 0.85
        });
      }
    }

    return suggestions;
  }

  detectFormatIssues(text) {
    const suggestions = [];
    
    const lines = text.split('\n');
    let inTable = false;
    let tableStart = -1;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      if (line.startsWith('|') && line.endsWith('|')) {
        if (!inTable) {
          inTable = true;
          tableStart = i;
        }
        
        if (i > 0 && inTable) {
          const prevLine = lines[i - 1].trim();
          if (prevLine.startsWith('|') && prevLine.endsWith('|')) {
            const prevCells = prevLine.split('|').filter(c => c.trim());
            const currentCells = line.split('|').filter(c => c.trim());
            
            if (prevCells.length !== currentCells.length) {
              suggestions.push({
                type: 'format',
                category: 'formatting',
                severity: 'high',
                originalText: line,
                explanation: `表格列数不一致：上一行${prevCells.length}列，当前行${currentCells.length}列`,
                ruleId: 'table_columns',
                confidence: 0.9
              });
            }
          }
        }
      } else {
        inTable = false;
      }
    }

    return suggestions;
  }

  async applySuggestion(suggestion, documentContent) {
    if (suggestion.suggestedText && suggestion.startPos !== undefined && suggestion.endPos !== undefined) {
      const before = documentContent.substring(0, suggestion.startPos);
      const after = documentContent.substring(suggestion.endPos);
      return before + suggestion.suggestedText + after;
    }
    return documentContent;
  }

  generateSummary(suggestions) {
    const summary = {
      total: suggestions.length,
      byType: {},
      bySeverity: {},
      byCategory: {},
      accepted: 0,
      pending: suggestions.length,
      averageConfidence: 0
    };

    let totalConfidence = 0;

    for (const suggestion of suggestions) {
      summary.byType[suggestion.type] = (summary.byType[suggestion.type] || 0) + 1;
      summary.bySeverity[suggestion.severity] = (summary.bySeverity[suggestion.severity] || 0) + 1;
      summary.byCategory[suggestion.category] = (summary.byCategory[suggestion.category] || 0) + 1;
      totalConfidence += suggestion.confidence || 0;
    }

    if (suggestions.length > 0) {
      summary.averageConfidence = totalConfidence / suggestions.length;
    }

    return summary;
  }
}

module.exports = new AIAuditService();

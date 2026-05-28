const Diff = require('diff');

class RichTextDiffEngine {
  constructor() {
    this.formatProps = ['bold', 'italic', 'underline', 'strikethrough', 'color', 'backgroundColor'];
  }

  computeRichDiff(oldContent, newContent, oldRichContent, newRichContent) {
    const textDiff = Diff.diffChars(oldContent, newContent);
    
    const richDiff = textDiff.map(part => {
      const formats = this.detectFormatChanges(part, oldRichContent, newRichContent);
      return {
        ...part,
        formats
      };
    });

    return richDiff;
  }

  detectFormatChanges(part, oldRichContent, newRichContent) {
    const formats = {
      added: [],
      removed: [],
      modified: []
    };

    if (!oldRichContent || !newRichContent) return formats;

    const oldFormats = this.extractFormatsAtRange(oldRichContent, part);
    const newFormats = this.extractFormatsAtRange(newRichContent, part);

    for (const prop of this.formatProps) {
      const oldVal = oldFormats[prop];
      const newVal = newFormats[prop];
      
      if (!oldVal && newVal) {
        formats.added.push({ type: prop, value: newVal });
      } else if (oldVal && !newVal) {
        formats.removed.push({ type: prop, value: oldVal });
      } else if (oldVal && newVal && oldVal !== newVal) {
        formats.modified.push({ 
          type: prop, 
          oldValue: oldVal, 
          newValue: newVal 
        });
      }
    }

    return formats;
  }

  extractFormatsAtRange(richContent, part) {
    const formats = {};
    
    if (!richContent || !richContent.content) return formats;
    
    let charCount = 0;
    for (const block of richContent.content) {
      for (const textNode of block.content) {
        const nodeStart = charCount;
        const nodeEnd = charCount + textNode.text.length;
        
        if (part.added || part.removed) {
          if (textNode.marks) {
            for (const mark of textNode.marks) {
              if (mark.type === 'bold') formats.bold = true;
              if (mark.type === 'italic') formats.italic = true;
              if (mark.type === 'underline') formats.underline = true;
              if (mark.type === 'strikethrough') formats.strikethrough = true;
              if (mark.type === 'color') formats.color = mark.color;
              if (mark.type === 'backgroundColor') formats.backgroundColor = mark.color;
            }
          }
        }
        
        charCount = nodeEnd;
      }
      charCount += 1;
    }
    
    return formats;
  }

  generateSideBySideDiff(oldContent, newContent, oldRichContent, newRichContent) {
    const oldLines = oldContent.split('\n');
    const newLines = newContent.split('\n');
    
    const maxLines = Math.max(oldLines.length, newLines.length);
    const diffLines = [];

    for (let i = 0; i < maxLines; i++) {
      const oldLine = oldLines[i] || '';
      const newLine = newLines[i] || '';
      
      const lineDiff = Diff.diffChars(oldLine, newLine);
      
      diffLines.push({
        lineNumber: i + 1,
        oldLine: this.renderLineWithFormatting(oldLine, oldRichContent, i),
        newLine: this.renderLineWithFormatting(newLine, newRichContent, i),
        changes: lineDiff,
        hasChanges: lineDiff.some(p => p.added || p.removed)
      });
    }

    return diffLines;
  }

  renderLineWithFormatting(text, richContent, lineIndex) {
    if (!richContent || !richContent.content[lineIndex]) {
      return [{ text, formats: {} }];
    }

    const block = richContent.content[lineIndex];
    const segments = [];

    for (const textNode of block.content) {
      const formats = {};
      if (textNode.marks) {
        for (const mark of textNode.marks) {
          if (mark.type === 'bold') formats.bold = true;
          if (mark.type === 'italic') formats.italic = true;
          if (mark.type === 'underline') formats.underline = true;
          if (mark.type === 'strikethrough') formats.strikethrough = true;
          if (mark.type === 'color') formats.color = mark.color;
          if (mark.type === 'backgroundColor') formats.backgroundColor = mark.color;
        }
      }
      segments.push({
        text: textNode.text,
        formats
      });
    }

    return segments;
  }

  generateHTMLDiff(richDiff) {
    return richDiff.map(part => {
      let className = '';
      let style = '';
      
      if (part.added) {
        className = 'diff-added';
        style = 'background-color: #e6ffed; color: #22863a;';
      } else if (part.removed) {
        className = 'diff-removed';
        style = 'background-color: #ffeef0; color: #b31d28; text-decoration: line-through;';
      }

      if (part.formats) {
        if (part.formats.added.length > 0) {
          for (const f of part.formats.added) {
            if (f.type === 'bold') style += 'font-weight: bold;';
            if (f.type === 'italic') style += 'font-style: italic;';
            if (f.type === 'underline') style += 'text-decoration: underline;';
            if (f.type === 'color') style += `color: ${f.value};`;
            if (f.type === 'backgroundColor') style += `background-color: ${f.value};`;
          }
        }
      }

      return `<span class="${className}" style="${style}">${part.value}</span>`;
    }).join('');
  }

  generateInlineDiffHTML(oldContent, newContent) {
    const changes = Diff.diffChars(oldContent, newContent);
    return changes.map(part => {
      if (part.added) {
        return `<ins style="background-color: #e6ffed; color: #22863a; text-decoration: none;">${part.value}</ins>`;
      } else if (part.removed) {
        return `<del style="background-color: #ffeef0; color: #b31d28;">${part.value}</del>`;
      }
      return `<span>${part.value}</span>`;
    }).join('');
  }

  compareFormats(oldFormats, newFormats) {
    const differences = {
      added: [],
      removed: [],
      modified: []
    };

    for (const prop of this.formatProps) {
      const oldVal = oldFormats[prop];
      const newVal = newFormats[prop];
      
      if (!oldVal && newVal) {
        differences.added.push({ type: prop, value: newVal });
      } else if (oldVal && !newVal) {
        differences.removed.push({ type: prop, value: oldVal });
      } else if (oldVal && newVal && JSON.stringify(oldVal) !== JSON.stringify(newVal)) {
        differences.modified.push({ 
          type: prop, 
          oldValue: oldVal, 
          newValue: newVal 
        });
      }
    }

    return differences;
  }

  getFormatSummary(richDiff) {
    const summary = {
      textAdded: 0,
      textRemoved: 0,
      formatsAdded: 0,
      formatsRemoved: 0,
      formatsModified: 0
    };

    for (const part of richDiff) {
      if (part.added) {
        summary.textAdded += part.value.length;
      } else if (part.removed) {
        summary.textRemoved += part.value.length;
      }
      
      if (part.formats) {
        summary.formatsAdded += part.formats.added.length;
        summary.formatsRemoved += part.formats.removed.length;
        summary.formatsModified += part.formats.modified.length;
      }
    }

    return summary;
  }
}

module.exports = new RichTextDiffEngine();

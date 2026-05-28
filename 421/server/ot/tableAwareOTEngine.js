const json0 = require('ot-json0').type;

class TableAwareOTEngine {
  constructor() {
    this.documents = new Map();
  }

  createDocument(docId, initialContent = '') {
    if (this.documents.has(docId)) {
      return this.documents.get(docId);
    }
    
    const doc = {
      id: docId,
      content: initialContent,
      richContent: this.parseToRichContent(initialContent),
      version: 0,
      operations: [],
      tables: [],
      pendingOps: []
    };
    
    this.documents.set(docId, doc);
    return doc;
  }

  parseToRichContent(text) {
    return {
      type: 'doc',
      content: text.split('\n').map(line => ({
        type: 'paragraph',
        content: [{
          type: 'text',
          text: line,
          marks: []
        }]
      }))
    };
  }

  richContentToText(richContent) {
    return richContent.content
      .map(block => block.content.map(t => t.text).join(''))
      .join('\n');
  }

  getDocument(docId) {
    return this.documents.get(docId);
  }

  parseTableStructure(content) {
    const tableRegex = /\|(.+)\|/g;
    const tables = [];
    let match;
    
    while ((match = tableRegex.exec(content)) !== null) {
      const rowText = match[1];
      const cells = rowText.split('|').map(c => c.trim());
      
      tables.push({
        startPos: match.index,
        endPos: match.index + match[0].length,
        cells: cells,
        rowIndex: tables.length
      });
    }
    
    return tables;
  }

  isPositionInTable(position, tables) {
    return tables.find(t => position >= t.startPos && position <= t.endPos);
  }

  applyOperation(docId, op, userId) {
    const doc = this.getDocument(docId);
    if (!doc) {
      throw new Error('Document not found');
    }

    if (op.v !== doc.version) {
      return this.transformOperation(doc, op, userId);
    }

    const tables = this.parseTableStructure(doc.content);
    
    if (op.op && op.op[0]) {
      const operation = op.op[0];
      const position = operation.p ? operation.p[1] : 0;
      const tableAtPos = this.isPositionInTable(position, tables);
      
      if (tableAtPos && op.type !== 'table-operation') {
        op = this.adjustOperationForTable(op, tableAtPos, tables);
      }
    }

    const appliedOp = {
      ...op,
      v: doc.version,
      userId,
      timestamp: Date.now()
    };

    if (op.type === 'table-operation') {
      doc.content = this.applyTableOperation(doc.content, op);
    } else if (op.type === 'format-operation') {
      doc.richContent = this.applyFormatOperation(doc.richContent, op);
      doc.content = this.richContentToText(doc.richContent);
    } else {
      doc.content = this.applyOpToContent(doc.content, op);
    }
    
    doc.version++;
    doc.operations.push(appliedOp);

    return {
      op: appliedOp,
      content: doc.content,
      richContent: doc.richContent,
      version: doc.version
    };
  }

  adjustOperationForTable(op, table, allTables) {
    const operation = op.op[0];
    const position = operation.p[1];
    const relativePos = position - table.startPos;
    
    if (operation.si !== undefined) {
      const cellIndex = this.getCellIndexAtPosition(relativePos, table);
      if (cellIndex !== -1) {
        op.tableContext = {
          tableStart: table.startPos,
          rowIndex: table.rowIndex,
          cellIndex: cellIndex
        };
      }
    }
    
    return op;
  }

  getCellIndexAtPosition(relativePos, table) {
    let currentPos = 1;
    for (let i = 0; i < table.cells.length; i++) {
      const cellLength = table.cells[i].length + 1;
      if (relativePos >= currentPos && relativePos < currentPos + cellLength) {
        return i;
      }
      currentPos += cellLength;
    }
    return -1;
  }

  applyTableOperation(content, op) {
    const tables = this.parseTableStructure(content);
    const targetTable = tables[op.tableIndex];
    
    if (!targetTable) return content;

    if (op.action === 'insert-row') {
      const newRow = '|' + Array(targetTable.cells.length).fill(' ').join('|') + '|';
      const insertPos = op.position === 'after' ? targetTable.endPos + 1 : targetTable.startPos;
      return content.slice(0, insertPos) + '\n' + newRow + content.slice(insertPos);
    }
    
    if (op.action === 'delete-row') {
      return content.slice(0, targetTable.startPos) + content.slice(targetTable.endPos + 1);
    }
    
    if (op.action === 'insert-column') {
      const lines = content.split('\n');
      const tableLines = lines.filter(line => line.startsWith('|') && line.endsWith('|'));
      
      const modifiedLines = lines.map(line => {
        if (line.startsWith('|') && line.endsWith('|')) {
          const cells = line.split('|');
          cells.splice(op.columnIndex + 1, 0, ' ');
          return cells.join('|');
        }
        return line;
      });
      
      return modifiedLines.join('\n');
    }
    
    if (op.action === 'delete-column') {
      const lines = content.split('\n');
      
      const modifiedLines = lines.map(line => {
        if (line.startsWith('|') && line.endsWith('|')) {
          const cells = line.split('|');
          if (cells.length > op.columnIndex + 2) {
            cells.splice(op.columnIndex + 1, 1);
            return cells.join('|');
          }
        }
        return line;
      });
      
      return modifiedLines.join('\n');
    }
    
    return content;
  }

  applyFormatOperation(richContent, op) {
    const { blockIndex, textIndex, start, end, mark, value } = op;
    
    if (!richContent.content[blockIndex]) return richContent;
    
    const block = richContent.content[blockIndex];
    if (!block.content[textIndex]) return richContent;
    
    const textNode = block.content[textIndex];
    
    if (value) {
      if (!textNode.marks) textNode.marks = [];
      if (!textNode.marks.find(m => m.type === mark)) {
        textNode.marks.push({ type: mark, ...op.markData });
      }
    } else {
      if (textNode.marks) {
        textNode.marks = textNode.marks.filter(m => m.type !== mark);
      }
    }
    
    return JSON.parse(JSON.stringify(richContent));
  }

  transformOperation(doc, clientOp, userId) {
    let transformedOp = { ...clientOp };
    const pendingOps = doc.operations.slice(clientOp.v);

    for (const serverOp of pendingOps) {
      transformedOp = this.transformPair(transformedOp, serverOp);
    }

    transformedOp.v = doc.version;
    return this.applyOperation(doc.id, transformedOp, userId);
  }

  transformPair(clientOp, serverOp) {
    if (clientOp.type === 'table-operation' || serverOp.type === 'table-operation') {
      return this.transformTableOperations(clientOp, serverOp);
    }
    
    if (clientOp.type === 'format-operation' || serverOp.type === 'format-operation') {
      return this.transformFormatOperations(clientOp, serverOp);
    }
    
    try {
      const [transformed] = json0.transform(clientOp.op, serverOp.op, 'left');
      return { ...clientOp, op: transformed };
    } catch (e) {
      return clientOp;
    }
  }

  transformTableOperations(clientOp, serverOp) {
    if (clientOp.type !== 'table-operation') {
      return clientOp;
    }
    
    if (serverOp.type === 'table-operation') {
      if (serverOp.action === 'insert-row' && serverOp.tableIndex <= clientOp.tableIndex) {
        clientOp.tableIndex += 1;
      }
      if (serverOp.action === 'delete-row' && serverOp.tableIndex < clientOp.tableIndex) {
        clientOp.tableIndex -= 1;
      }
      if (serverOp.action === 'insert-column' && serverOp.tableIndex === clientOp.tableIndex 
          && serverOp.columnIndex <= clientOp.columnIndex) {
        clientOp.columnIndex += 1;
      }
      if (serverOp.action === 'delete-column' && serverOp.tableIndex === clientOp.tableIndex 
          && serverOp.columnIndex < clientOp.columnIndex) {
        clientOp.columnIndex -= 1;
      }
    }
    
    return clientOp;
  }

  transformFormatOperations(clientOp, serverOp) {
    if (clientOp.type !== 'format-operation') {
      return clientOp;
    }
    
    if (serverOp.op && serverOp.op[0]) {
      const serverPos = serverOp.op[0].p ? serverOp.op[0].p[1] : 0;
      
      if (serverOp.op[0].si !== undefined) {
        const insertLength = serverOp.op[0].si.length;
        if (serverPos <= clientOp.start) {
          clientOp.start += insertLength;
          clientOp.end += insertLength;
        }
      }
      
      if (serverOp.op[0].sd !== undefined) {
        const deleteLength = serverOp.op[0].sd.length;
        if (serverPos + deleteLength <= clientOp.start) {
          clientOp.start -= deleteLength;
          clientOp.end -= deleteLength;
        } else if (serverPos < clientOp.end) {
          clientOp.end = Math.max(clientOp.start, clientOp.end - deleteLength);
        }
      }
    }
    
    return clientOp;
  }

  applyOpToContent(content, op) {
    try {
      if (op.op && op.op[0]) {
        const operation = op.op[0];
        const position = operation.p ? operation.p[1] : 0;
        
        if (operation.si !== undefined) {
          return content.slice(0, position) + operation.si + content.slice(position);
        } else if (operation.sd !== undefined) {
          const length = operation.sd.length;
          return content.slice(0, position) + content.slice(position + length);
        }
      }
      return content;
    } catch (e) {
      return content;
    }
  }

  createTableOperation(docId, action, tableIndex, options = {}) {
    const doc = this.getDocument(docId);
    return {
      v: doc.version,
      type: 'table-operation',
      action,
      tableIndex,
      ...options
    };
  }

  createFormatOperation(docId, blockIndex, textIndex, start, end, mark, value, markData = {}) {
    const doc = this.getDocument(docId);
    return {
      v: doc.version,
      type: 'format-operation',
      blockIndex,
      textIndex,
      start,
      end,
      mark,
      value,
      markData
    };
  }

  getHistory(docId) {
    const doc = this.getDocument(docId);
    return doc ? doc.operations : [];
  }

  getVersion(docId) {
    const doc = this.getDocument(docId);
    return doc ? doc.version : 0;
  }
}

module.exports = new TableAwareOTEngine();

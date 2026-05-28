const json0 = require('ot-json0').type;

class OTEngine {
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
      version: 0,
      operations: [],
      pendingOps: []
    };
    
    this.documents.set(docId, doc);
    return doc;
  }

  getDocument(docId) {
    return this.documents.get(docId);
  }

  applyOperation(docId, op, userId) {
    const doc = this.getDocument(docId);
    if (!doc) {
      throw new Error('Document not found');
    }

    if (op.v !== doc.version) {
      return this.transformOperation(doc, op, userId);
    }

    const appliedOp = {
      ...op,
      v: doc.version,
      userId,
      timestamp: Date.now()
    };

    doc.content = this.applyOpToContent(doc.content, op);
    doc.version++;
    doc.operations.push(appliedOp);

    return {
      op: appliedOp,
      content: doc.content,
      version: doc.version
    };
  }

  transformOperation(doc, clientOp, userId) {
    let transformedOp = { ...clientOp };
    const pendingOps = doc.operations.slice(clientOp.v);

    for (const serverOp of pendingOps) {
      const [transformed] = json0.transform(transformedOp.op, serverOp.op, 'left');
      transformedOp.op = transformed;
    }

    transformedOp.v = doc.version;
    return this.applyOperation(doc.id, transformedOp, userId);
  }

  applyOpToContent(content, op) {
    try {
      const doc = [{ p: '', t: 'text', d: content }];
      const result = json0.apply(doc, op.op);
      return result[0].d;
    } catch (e) {
      return content;
    }
  }

  createInsertOp(position, text, version) {
    return {
      v: version,
      op: [{
        p: ['', position],
        si: text
      }]
    };
  }

  createDeleteOp(position, length, version) {
    return {
      v: version,
      op: [{
        p: ['', position],
        sd: ' '.repeat(length)
      }]
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

module.exports = new OTEngine();

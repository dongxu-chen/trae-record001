const Document = require('../models/Document');

exports.getDocumentsByTask = async (req, res) => {
  try {
    const { taskId } = req.params;
    const { status, limit = 100, offset = 0 } = req.query;
    
    const query = { taskId };
    if (status) {
      query.status = status;
    }
    
    const documents = await Document.find(query)
      .sort({ createdAt: 1 })
      .skip(parseInt(offset))
      .limit(parseInt(limit));
    
    const total = await Document.countDocuments(query);
    
    res.json({ documents, total });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getDocumentById = async (req, res) => {
  try {
    const document = await Document.findById(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }
    res.json(document);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getNextDocument = async (req, res) => {
  try {
    const { taskId, currentId } = req.params;
    
    const currentDoc = await Document.findById(currentId);
    if (!currentDoc) {
      const firstDoc = await Document.findOne({ taskId, status: 'pending' })
        .sort({ createdAt: 1 });
      return res.json(firstDoc);
    }
    
    const nextDoc = await Document.findOne({
      taskId,
      status: 'pending',
      createdAt: { $gt: currentDoc.createdAt }
    }).sort({ createdAt: 1 });
    
    if (!nextDoc) {
      return res.json(null);
    }
    
    res.json(nextDoc);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.createDocument = async (req, res) => {
  try {
    const document = new Document(req.body);
    await document.save();
    res.status(201).json(document);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
};

exports.bulkCreateDocuments = async (req, res) => {
  try {
    const { taskId, documents } = req.body;
    const docs = documents.map(doc => ({
      ...doc,
      taskId
    }));
    
    const created = await Document.insertMany(docs);
    res.status(201).json({ count: created.length, documents: created });
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
};

exports.updateDocument = async (req, res) => {
  try {
    const document = await Document.findByIdAndUpdate(
      req.params.id,
      { ...req.body, updatedAt: Date.now() },
      { new: true }
    );
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }
    res.json(document);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
};

exports.deleteDocument = async (req, res) => {
  try {
    const document = await Document.findByIdAndDelete(req.params.id);
    if (!document) {
      return res.status(404).json({ error: 'Document not found' });
    }
    res.json({ message: 'Document deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

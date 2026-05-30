const Annotation = require('../models/Annotation');
const Document = require('../models/Document');

exports.getAnnotationByDocument = async (req, res) => {
  try {
    const { documentId } = req.params;
    const annotation = await Annotation.findOne({ documentId });
    
    if (!annotation) {
      return res.json({
        documentId,
        taskId: req.query.taskId,
        entities: [],
        relations: [],
        events: []
      });
    }
    
    res.json(annotation);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.saveAnnotation = async (req, res) => {
  try {
    const { documentId } = req.params;
    const { entities, relations, events, taskId, annotator, comments } = req.body;
    
    let annotation = await Annotation.findOne({ documentId });
    
    if (annotation) {
      annotation.entities = entities;
      annotation.relations = relations;
      annotation.events = events;
      annotation.annotator = annotator;
      annotation.comments = comments;
      annotation.updatedAt = Date.now();
    } else {
      annotation = new Annotation({
        documentId,
        taskId,
        entities,
        relations,
        events,
        annotator,
        comments
      });
    }
    
    await annotation.save();
    
    await Document.findByIdAndUpdate(documentId, {
      status: 'annotated',
      updatedAt: Date.now()
    });
    
    res.json(annotation);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
};

exports.deleteAnnotation = async (req, res) => {
  try {
    const annotation = await Annotation.findOneAndDelete({ documentId: req.params.documentId });
    if (!annotation) {
      return res.status(404).json({ error: 'Annotation not found' });
    }
    
    await Document.findByIdAndUpdate(req.params.documentId, {
      status: 'pending',
      updatedAt: Date.now()
    });
    
    res.json({ message: 'Annotation deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getAnnotationsByTask = async (req, res) => {
  try {
    const { taskId } = req.params;
    const annotations = await Annotation.find({ taskId })
      .populate('documentId', 'text status')
      .sort({ updatedAt: -1 });
    
    res.json(annotations);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};
